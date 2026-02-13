from typing import List, Dict
from datetime import datetime

# Mock Data Store
class MockDB:
    users: List[Dict] = []
    bookings: List[Dict] = []
    services: List[Dict] = [
        {"id": "cleaning", "name": "Cleaning", "icon": "sparkles", "color": "0xFF6C63FF"},
        {"id": "plumbing", "name": "Plumbing", "icon": "wrench", "color": "0xFFFFA726"},
        {"id": "electrician", "name": "Electrician", "icon": "zap", "color": "0xFFFF7043"},
        {"id": "painting", "name": "Painting", "icon": "paint-roller", "color": "0xFF29B6F6"},
    ]
    
    def __init__(self):
        # Add a default test user
        self.users.append({
            "id": 1,
            "email": "test@example.com",
            "password_hash": "hashed_password", # Mock hash
            "full_name": "Test User",
            "role": "customer",
            "is_active": True
        })

db = MockDB()
