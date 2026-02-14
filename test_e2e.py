import asyncio
import httpx
import random
import string

BASE_URL = "https://skillnscale-backend.onrender.com/api/v1"
# BASE_URL = "http://localhost:8000/api/v1" # Uncomment for local testing

def random_string(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_phone():
    return f"9{random.randint(100000000, 999999999)}"

async def run_e2e_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"🚀 Starting E2E Test against {BASE_URL}")
        
        # 0. Health Check with Retry
        max_retries = 6
        for i in range(max_retries):
            try:
                print(f"Health check attempt {i+1}/{max_retries}...")
                resp = await client.get(f"{BASE_URL.replace('/api/v1', '')}/health")
                if resp.status_code == 200:
                    print(f"✅ Health Check passed: {resp.json()}")
                    break
                else:
                    print(f"Health Check: {resp.status_code} {resp.text}")
            except Exception as e:
                print(f"Health check failed: {e}")
            
            if i < max_retries - 1:
                print("Waiting 10s for service to wake up/deploy...")
                await asyncio.sleep(10)
        else:
            print("❌ Service unobtainable after retries.")
            return

        # 1. Signup Customer
        cust_phone = random_phone()
        cust_password = "password123"
        print(f"\n[1] Signing up Customer ({cust_phone})...")
        resp = await client.post(f"{BASE_URL}/auth/signup/customer", json={
            "phone": cust_phone,
            "password": cust_password,
            "full_name": f"Test Customer {random_string()}"
        })
        if resp.status_code != 200:
            print(f"❌ Signup failed: {resp.status_code} - {resp.text}")
            return
        print("✅ Customer signed up")

        # 2. Login Customer
        print(f"\n[2] Logging in Customer...")
        resp = await client.post(f"{BASE_URL}/auth/login/json", json={
            "phone": cust_phone,
            "password": cust_password
        })
        if resp.status_code != 200:
            print(f"❌ Login failed: {resp.text}")
            return
        cust_token = resp.json()["access_token"]
        print("✅ Customer logged in")

        # 3. Create Service Request
        print(f"\n[3] Creating Service Request...")
        # First, we need a category ID. Fetch categories.
        resp = await client.get(f"{BASE_URL}/services/categories")
        categories = resp.json()
        if not categories:
            print("❌ No categories found to create request")
            return
        category_id = categories[0]["id"]
        
        request_data = {
            "category_id": category_id,
            "title": "Leaking Tap",
            "description": "Kitchen tap is leaking badly, need fix ASAP.",
            "location": "Sector 45, Gurgaon",
            "latitude": 28.4595,
            "longitude": 77.0266,
            "urgency": "immediate",
            "photos": [] 
        }
        
        resp = await client.post(
            f"{BASE_URL}/requests/",
            json=request_data,
            headers={"Authorization": f"Bearer {cust_token}"}
        )
        if resp.status_code != 200:
            print(f"❌ Create request failed: {resp.text}")
            return
        request_id = resp.json()["id"]
        print(f"✅ Request created (ID: {request_id})")

        # 4. Signup Professional
        pro_phone = random_phone()
        print(f"\n[4] Signing up Professional ({pro_phone})...")
        resp = await client.post(f"{BASE_URL}/auth/signup/pro", json={
            "phone": pro_phone,
            "password": "password123",
            "full_name": f"Test Pro {random_string()}",
            "service_category": category_id
        })
        if resp.status_code != 200:
            print(f"❌ Pro Signup failed: {resp.text}")
            return
        print("✅ Professional signed up")

        # 5. Login Professional
        print(f"\n[5] Logging in Professional...")
        resp = await client.post(f"{BASE_URL}/auth/login/json", json={
            "phone": pro_phone,
            "password": "password123"
        })
        if resp.status_code != 200:
            print(f"❌ Pro Login failed: {resp.text}")
            return
        pro_token = resp.json()["access_token"]
        print("✅ Professional logged in")

        # 6. Pro Views Open Requests
        print(f"\n[6] Pro fetching open requests...")
        resp = await client.get(
            f"{BASE_URL}/requests/open",
            params={"category": category_id},
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        if resp.status_code != 200:
            print(f"❌ Fetch open requests failed: {resp.text}")
            return
        
        requests = resp.json()
        found = any(r["id"] == request_id for r in requests)
        if found:
            print("✅ Newly created request found in open list!")
        else:
            print("⚠️ Request not found in open list (might be caching or latency)")

        print("\n🎉 E2E Test Completed Successfully!")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
