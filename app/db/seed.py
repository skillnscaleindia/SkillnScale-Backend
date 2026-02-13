"""Seed the database with initial data."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.db_models import ServiceCategory, User, UserRole, Availability
from app.core.security import get_password_hash
import random
from datetime import datetime, timedelta

CATEGORIES = [
    {"id": "cleaning", "name": "Cleaning", "icon": "sparkles", "color": "0xFF6C63FF", "description": "Home & office cleaning services"},
    {"id": "plumbing", "name": "Plumbing", "icon": "wrench", "color": "0xFFFFA726", "description": "Pipe repairs, fittings, and water systems"},
    {"id": "electrician", "name": "Electrician", "icon": "zap", "color": "0xFFFF7043", "description": "Electrical repairs, wiring, and installations"},
    {"id": "painting", "name": "Painting", "icon": "paint-roller", "color": "0xFF29B6F6", "description": "Interior and exterior painting"},
    {"id": "ac_repair", "name": "AC Repair", "icon": "wind", "color": "0xFF26A69A", "description": "AC servicing, repair, and installation"},
    {"id": "salon", "name": "Salon", "icon": "scissors", "color": "0xFFEC407A", "description": "Haircut, styling, and grooming at home"},
    {"id": "pest_control", "name": "Pest Control", "icon": "bug", "color": "0xFF8D6E63", "description": "Pest removal and prevention"},
    {"id": "carpentry", "name": "Carpentry", "icon": "hammer", "color": "0xFF5C6BC0", "description": "Furniture repair, assembly, and custom work"},
]

PROFESSIONALS = [
    {
        "email": "rajesh.electrician@example.com",
        "full_name": "Rajesh Kumar",
        "phone": "9876543210",
        "service_category": "electrician",
        "bio": "Expert electrician with 10 years of experience in residential and commercial wiring.",
        "latitude": 12.9716,
        "longitude": 77.5946,  # Bangalore Central
        "address": "MG Road, Bangalore"
    },
    {
        "email": "anita.cleaning@example.com",
        "full_name": "Anita Singh",
        "phone": "9876543211",
        "service_category": "cleaning",
        "bio": "Professional home cleaner. I use eco-friendly products and ensure 100% satisfaction.",
        "latitude": 12.9352,
        "longitude": 77.6245,  # Koramangala
        "address": "Koramangala, Bangalore"
    },
    {
        "email": "suresh.plumber@example.com",
        "full_name": "Suresh Reddy",
        "phone": "9876543212",
        "service_category": "plumbing",
        "bio": "Certified plumber specializing in leak repairs and pipe fitting.",
        "latitude": 12.9784,
        "longitude": 77.6408,  # Indiranagar
        "address": "Indiranagar, Bangalore"
    },
    {
        "email": "priya.salon@example.com",
        "full_name": "Priya Sharma",
        "phone": "9876543213",
        "service_category": "salon",
        "bio": "Professional beautician providing salon services at your doorstep.",
        "latitude": 12.9279,
        "longitude": 77.6271,  # HSR Layout
        "address": "HSR Layout, Bangalore"
    },
    {
        "email": "vikram.ac@example.com",
        "full_name": "Vikram Malhotra",
        "phone": "9876543214",
        "service_category": "ac_repair",
        "bio": "AC installation and repair expert. Fast and reliable service.",
        "latitude": 13.0358,
        "longitude": 77.5970,  # Hebbal
        "address": "Hebbal, Bangalore"
    }
]

CUSTOMERS = [
    {
        "email": "customer@example.com",
        "full_name": "Rahul Verma",
        "phone": "9988776655",
        "address": "Whitefield, Bangalore",
        "latitude": 12.9698,
        "longitude": 77.7500
    }
]

async def seed_data(db: AsyncSession):
    """Seed the database with initial data."""
    print("Starting database seed...")
    
    # 1. Seed Categories
    result = await db.execute(select(ServiceCategory))
    if not result.scalars().first():
        for cat_data in CATEGORIES:
            category = ServiceCategory(**cat_data)
            db.add(category)
        print(f"Seeded {len(CATEGORIES)} service categories.")
    
    # 2. Seed Professionals
    password_hash = get_password_hash("password123")
    
    for pro_data in PROFESSIONALS:
        result = await db.execute(select(User).where(User.email == pro_data["email"]))
        if not result.scalars().first():
            user = User(
                email=pro_data["email"],
                password_hash=password_hash,
                full_name=pro_data["full_name"],
                phone=pro_data["phone"],
                role=UserRole.PRO.value,
                service_category=pro_data["service_category"],
                bio=pro_data["bio"],
                latitude=pro_data["latitude"],
                longitude=pro_data["longitude"],
                address=pro_data["address"],
                is_active=True
            )
            db.add(user)
            
            # Add availability for next 7 days (9 AM - 6 PM)
            today = datetime.now()
            for i in range(7):
                day = today + timedelta(days=i)
                avail = Availability(
                    professional=user,  # Using relationship directly since user.id is generated on flush
                    date=day.strftime("%Y-%m-%d"),
                    start_time="09:00",
                    end_time="18:00",
                    is_recurring=False
                )
                db.add(avail)
            
            print(f"Seeded professional: {pro_data['full_name']}")

    # 3. Seed Customers
    for cust_data in CUSTOMERS:
        result = await db.execute(select(User).where(User.email == cust_data["email"]))
        if not result.scalars().first():
            user = User(
                email=cust_data["email"],
                password_hash=password_hash,
                full_name=cust_data["full_name"],
                phone=cust_data["phone"],
                role=UserRole.CUSTOMER.value,
                address=cust_data["address"],
                latitude=cust_data["latitude"],
                longitude=cust_data["longitude"],
                is_active=True
            )
            db.add(user)
            print(f"Seeded customer: {cust_data['full_name']}")

    await db.commit()
    print("Database seeding completed.")
