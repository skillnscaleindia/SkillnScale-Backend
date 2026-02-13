import httpx
import uuid
import time

BASE_URL = "http://localhost:8000/api/v1"

def run_test():
    print(f"Testing against {BASE_URL}")
    generated_suffix = str(uuid.uuid4())[:8]
    customer_email = f"cust_{generated_suffix}@example.com"
    pro_email = f"pro_{generated_suffix}@example.com"
    password = "password123"

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health Check
        try:
            resp = client.get("/")  # Or /docs, checking root usually 404s but let's check /services/categories as health
            print("Server is up.")
        except Exception as e:
            print(f"CRITICAL: Server down? {e}")
            return

        # 1.5. Negative Test: Invalid Login
        print("Testing Invalid Login...")
        resp = client.post("/auth/login", data={
            "username": "wrong@example.com",
            "password": "wrongpassword"
        })
        if resp.status_code == 400 or resp.status_code == 401:
            print("SUCCESS: Invalid login rejected.")
        else:
            print(f"FAILED: Invalid login accepted? Status: {resp.status_code}")
            return

        # 2. Register Customer
        print(f"Registering Customer: {customer_email}")
        resp = client.post("/auth/signup", json={
            "email": customer_email,
            "password": password,
            "full_name": "Test Customer",
            "role": "customer"
        })
        if resp.status_code != 200:
            print(f"FAILED to register customer: {resp.text}")
            return
        print("Customer registered.")

        # 3. Login Customer
        print("Logging in Customer...")
        resp = client.post("/auth/login", data={
            "username": customer_email,
            "password": password
        })  # OAuth2RequestForm expects form data
        if resp.status_code != 200:
             # Try json if form fails (depends on implementation)
             print(f"Login failed (form data): {resp.text}")
             return
        
        customer_token = resp.json()["access_token"]
        customer_headers = {"Authorization": f"Bearer {customer_token}"}
        print("Customer logged in.")

        # 4. Get Categories
        print("Fetching Categories...")
        resp = client.get("/services/categories", headers=customer_headers)
        if resp.status_code != 200:
            print(f"FAILED to get categories: {resp.text}")
            return
        categories = resp.json()
        if not categories:
            print("FAILED: No categories found (did you seed the db?)")
            # If empty, we can't create a booking with valid category, but maybe "general" works if we allow it?
            # Let's see if we can use a dummy one if empty.
        else:
            print(f"Found {len(categories)} categories.")
        
        category_id = categories[0]['id'] if categories else "general"

        # 5. Create Booking
        print("Creating Booking...")
        scheduled_at = "2026-12-31T10:00:00"
        booking_payload = {
            "service_id": category_id,
            "scheduled_at": scheduled_at,
            "address": "123 Test St",
            "notes": "Fix my leak"
        }
        resp = client.post("/bookings/", json=booking_payload, headers=customer_headers)
        if resp.status_code != 200:
            print(f"FAILED to create booking: {resp.text}")
            return
        
        booking_data = resp.json()
        booking_id = booking_data['id']
        print(f"Booking created: ID {booking_id}")

        # 6. Register Professional
        print(f"Registering Professional: {pro_email}")
        resp = client.post("/auth/signup", json={
            "email": pro_email,
            "password": password,
            "full_name": "Test Pro",
            "role": "pro"
        })
        if resp.status_code != 200:
            print(f"FAILED to register pro: {resp.text}")
            return
        
        # 7. Login Professional
        print("Logging in Professional...")
        resp = client.post("/auth/login", data={
            "username": pro_email,
            "password": password
        })
        if resp.status_code != 200:
            print(f"FAILED login pro: {resp.text}")
            return
        
        pro_token = resp.json()["access_token"]
        pro_headers = {"Authorization": f"Bearer {pro_token}"}
        
        # 8. View Pending Bookings
        print("Fetching Pending Bookings...")
        resp = client.get("/bookings/pending", headers=pro_headers)
        if resp.status_code != 200:
            print(f"FAILED to fetch pending: {resp.text}")
            return
        
        pending = resp.json()
        target_booking = next((b for b in pending if b['id'] == booking_id), None)
        
        if not target_booking:
            print("FAILED: Newly created booking not found in pending list!")
            print(f"Pending list IDs: {[b['id'] for b in pending]}")
            return
        print("Booking found in pending list.")

        # 9. Accept Booking
        print(f"Accepting Booking {booking_id}...")
        resp = client.post(f"/bookings/{booking_id}/accept", headers=pro_headers)
        if resp.status_code != 200:
            print(f"FAILED to accept booking: {resp.text}")
            return
        print("Booking accepted.")

        # 10. Verify Status (Customer Side)
        print("Verifying Customer Status...")
        resp = client.get("/bookings/", headers=customer_headers)
        my_bookings = resp.json()
        updated_booking = next((b for b in my_bookings if b['id'] == booking_id), None)
        
        if updated_booking and updated_booking['status'] in ['accepted', 'confirmed']:
            print(f"SUCCESS! Booking status is {updated_booking['status']}")
        else:
            print(f"FAILED: Status mismatch. Expected accepted, got {updated_booking['status'] if updated_booking else 'None'}")

if __name__ == "__main__":
    run_test()
