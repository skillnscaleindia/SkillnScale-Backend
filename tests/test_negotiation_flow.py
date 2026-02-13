"""
Comprehensive Integration Test for SkillnScale Backend.
Tests the full negotiation flow:
  Customer signup → Create request → Professional signup → Set availability →
  Get matches → Create chat → Negotiate price → Accept price → Booking created →
  Complete booking → Review
"""
import httpx
import uuid
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"
suffix = str(uuid.uuid4())[:8]


def test_full_flow():
    print(f"\n{'='*60}")
    print(f"  SkillnScale Full Negotiation Flow Test")
    print(f"{'='*60}\n")

    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:

        # ─── 1. Health Check ─────────────────────────────────
        print("1. Health check...")
        resp = client.get("/health")
        assert resp.status_code == 200, f"Health check failed: {resp.text}"
        print("   ✅ Server is healthy\n")

        # ─── 2. Get Categories ───────────────────────────────
        print("2. Fetching service categories...")
        resp = client.get("/services/categories")
        assert resp.status_code == 200
        categories = resp.json()
        assert len(categories) == 8, f"Expected 8 categories, got {len(categories)}"
        cat_names = [c['name'] for c in categories]
        print(f"   ✅ Found {len(categories)} categories: {cat_names}\n")

        # ─── 3. Customer Signup ──────────────────────────────
        customer_email = f"customer_{suffix}@test.com"
        print(f"3. Customer signup: {customer_email}")
        resp = client.post("/auth/signup", json={
            "email": customer_email,
            "password": "password123",
            "full_name": "Rajat Customer",
            "role": "customer",
            "phone": "9876543210",
        })
        assert resp.status_code == 200, f"Signup failed: {resp.text}"
        customer = resp.json()
        print(f"   ✅ Customer created: ID {customer['id'][:8]}...\n")

        # ─── 4. Customer Login ───────────────────────────────
        print("4. Customer login...")
        resp = client.post("/auth/login/json", json={
            "email": customer_email,
            "password": "password123",
        })
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        cust_token = resp.json()["access_token"]
        cust_headers = {"Authorization": f"Bearer {cust_token}"}
        print("   ✅ Customer logged in\n")

        # ─── 5. Get /users/me ────────────────────────────────
        print("5. Get customer profile...")
        resp = client.get("/users/me", headers=cust_headers)
        assert resp.status_code == 200
        me = resp.json()
        assert me["email"] == customer_email
        print(f"   ✅ Profile: {me['full_name']} ({me['role']})\n")

        # ─── 6. Create Service Request ───────────────────────
        print("6. Customer creates service request...")
        resp = client.post("/requests/", json={
            "category_id": "plumbing",
            "title": "Kitchen Sink Leak",
            "description": "Kitchen sink is leaking badly. Water dripping from the pipe under the sink. Need urgent repair.",
            "location": "Jaipur, Rajasthan",
            "urgency": "immediate",
        }, headers=cust_headers)
        assert resp.status_code == 200, f"Create request failed: {resp.text}"
        service_req = resp.json()
        request_id = service_req["id"]
        print(f"   ✅ Request created: {service_req['title']} (ID: {request_id[:8]}...)\n")

        # ─── 7. Professional Signup ──────────────────────────
        pro_email = f"plumber_{suffix}@test.com"
        print(f"7. Professional signup: {pro_email}")
        resp = client.post("/auth/signup", json={
            "email": pro_email,
            "password": "password123",
            "full_name": "Ramesh Plumber",
            "role": "pro",
            "phone": "9876543211",
            "service_category": "plumbing",
        })
        assert resp.status_code == 200, f"Pro signup failed: {resp.text}"
        pro = resp.json()
        pro_id = pro["id"]
        print(f"   ✅ Professional created: {pro['full_name']} (ID: {pro_id[:8]}...)\n")

        # ─── 8. Professional Login ───────────────────────────
        print("8. Professional login...")
        resp = client.post("/auth/login/json", json={
            "email": pro_email,
            "password": "password123",
        })
        assert resp.status_code == 200
        pro_token = resp.json()["access_token"]
        pro_headers = {"Authorization": f"Bearer {pro_token}"}
        print("   ✅ Professional logged in\n")

        # ─── 9. Set Availability ─────────────────────────────
        print("9. Professional sets availability...")
        resp = client.post("/availability/", json={
            "date": "2026-02-14",
            "start_time": "14:00",
            "end_time": "17:00",
            "is_recurring": False,
        }, headers=pro_headers)
        assert resp.status_code == 200, f"Set availability failed: {resp.text}"
        slot = resp.json()
        print(f"   ✅ Slot created: {slot['date']} {slot['start_time']}-{slot['end_time']}\n")

        # ─── 10. Get Matched Professionals ───────────────────
        print("10. Customer gets matched professionals...")
        resp = client.get(f"/requests/{request_id}/matches", headers=cust_headers)
        assert resp.status_code == 200, f"Matches failed: {resp.text}"
        matches = resp.json()
        assert len(matches) >= 1, "No matches found!"
        print(f"   ✅ Found {len(matches)} match(es): {[m['full_name'] for m in matches]}\n")

        matched_pro_id = matches[0]["id"]

        # ─── 11. Create Chat Room ────────────────────────────
        print("11. Customer starts chat with professional...")
        resp = client.post("/chat/rooms/", json={
            "request_id": request_id,
            "professional_id": matched_pro_id,
        }, headers=cust_headers)
        assert resp.status_code == 200, f"Create chat failed: {resp.text}"
        room = resp.json()
        room_id = room["id"]
        print(f"   ✅ Chat room created: {room_id[:8]}...\n")

        # ─── 12. Exchange Messages ───────────────────────────
        print("12. Chat conversation...")

        # Customer message
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "Hi, my sink is leaking. Can you come today?",
            "message_type": "text",
        }, headers=cust_headers)
        assert resp.status_code == 200
        print("   📨 Customer: Hi, my sink is leaking. Can you come today?")

        # Pro message
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "Yes, I can come between 2-5 PM. What kind of pipe is it?",
            "message_type": "text",
        }, headers=pro_headers)
        assert resp.status_code == 200
        print("   📨 Pro: Yes, I can come between 2-5 PM. What kind of pipe is it?")

        # Customer message
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "It's a PVC pipe under the kitchen sink. How much would it cost?",
            "message_type": "text",
        }, headers=cust_headers)
        assert resp.status_code == 200
        print("   📨 Customer: It's a PVC pipe. How much would it cost?")

        # Pro proposes price
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "For PVC pipe repair, I can do it for ₹400",
            "message_type": "price_proposal",
            "proposed_price": 400.0,
        }, headers=pro_headers)
        assert resp.status_code == 200
        print("   💰 Pro proposes: ₹400")

        # Customer counter-proposes
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "Can you do it for ₹300?",
            "message_type": "price_proposal",
            "proposed_price": 300.0,
        }, headers=cust_headers)
        assert resp.status_code == 200
        print("   💰 Customer counter: ₹300")

        # Pro counters
        resp = client.post(f"/chat/rooms/{room_id}/messages", json={
            "content": "Final offer: ₹350 including pipe replacement",
            "message_type": "price_proposal",
            "proposed_price": 350.0,
        }, headers=pro_headers)
        assert resp.status_code == 200
        print("   💰 Pro final: ₹350")

        # Verify messages stored
        resp = client.get(f"/chat/rooms/{room_id}/messages", headers=cust_headers)
        assert resp.status_code == 200
        messages = resp.json()
        print(f"   ✅ {len(messages)} messages in chat\n")

        # ─── 13. Accept Price → Booking Created ─────────────
        print("13. Customer accepts ₹350...")
        resp = client.post(f"/chat/rooms/{room_id}/accept-price", headers=cust_headers)
        assert resp.status_code == 200, f"Accept price failed: {resp.text}"
        booking = resp.json()
        booking_id = booking["id"]
        assert booking["agreed_price"] == 350.0
        assert booking["status"] == "confirmed"
        print(f"   ✅ Booking created! ID: {booking_id[:8]}... Price: ₹{booking['agreed_price']}\n")

        # ─── 14. Update Booking Status ───────────────────────
        print("14. Professional starts job...")
        resp = client.patch(f"/bookings/{booking_id}/status", json={
            "status": "in_progress",
        }, headers=pro_headers)
        assert resp.status_code == 200
        print("   ✅ Status: in_progress")

        print("    Professional completes job...")
        resp = client.patch(f"/bookings/{booking_id}/status", json={
            "status": "completed",
        }, headers=pro_headers)
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["status"] == "completed"
        print("   ✅ Status: completed\n")

        # ─── 15. Submit Review ───────────────────────────────
        print("15. Customer submits review...")
        resp = client.post("/reviews/", json={
            "booking_id": booking_id,
            "rating": 5,
            "comment": "Excellent work! Fixed the leak quickly and cleanly. Very professional.",
        }, headers=cust_headers)
        assert resp.status_code == 200, f"Review failed: {resp.text}"
        review = resp.json()
        print(f"   ✅ Review submitted: {review['rating']}/5 stars\n")

        # ─── 16. Verify Pro Rating ───────────────────────────
        print("16. Verify professional profile with rating...")
        resp = client.get(f"/users/{pro_id}", headers=cust_headers)
        assert resp.status_code == 200
        pro_profile = resp.json()
        assert pro_profile["rating"] == 5.0
        assert pro_profile["jobs_completed"] == 1
        print(f"   ✅ {pro_profile['full_name']}: ⭐ {pro_profile['rating']}/5, {pro_profile['jobs_completed']} job(s) completed\n")

        # ─── 17. List Chat Rooms ─────────────────────────────
        print("17. List customer's chat rooms...")
        resp = client.get("/chat/rooms/", headers=cust_headers)
        assert resp.status_code == 200
        rooms = resp.json()
        assert len(rooms) >= 1
        print(f"   ✅ Found {len(rooms)} chat room(s)\n")

        # ─── 18. Invalid Login Test ──────────────────────────
        print("18. Negative test: invalid login...")
        resp = client.post("/auth/login/json", json={
            "email": "wrong@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 400
        print("   ✅ Invalid login correctly rejected\n")

        # ─── 19. Duplicate Signup Test ───────────────────────
        print("19. Negative test: duplicate signup...")
        resp = client.post("/auth/signup", json={
            "email": customer_email,
            "password": "password123",
            "full_name": "Duplicate User",
            "role": "customer",
        })
        assert resp.status_code == 400
        print("   ✅ Duplicate signup correctly rejected\n")

        # ─── Summary ────────────────────────────────────────
        print(f"{'='*60}")
        print(f"  🎉 ALL 19 TESTS PASSED!")
        print(f"{'='*60}")
        print(f"\n  Full negotiation flow verified:")
        print(f"  ✅ Auth (signup, login, /me)")
        print(f"  ✅ Service categories (8 seeded)")
        print(f"  ✅ Service request with problem description")
        print(f"  ✅ Professional availability time slots")
        print(f"  ✅ Matching (category-based)")
        print(f"  ✅ Chat rooms + messages")
        print(f"  ✅ Price negotiation (propose/counter/accept)")
        print(f"  ✅ Auto-booking on price acceptance")
        print(f"  ✅ Booking lifecycle (confirmed → in_progress → completed)")
        print(f"  ✅ Reviews with computed ratings")
        print(f"  ✅ Error handling (invalid login, duplicate signup)")
        print()


if __name__ == "__main__":
    try:
        test_full_flow()
    except AssertionError as e:
        print(f"\n   ❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n   ❌ ERROR: {e}")
        sys.exit(1)
