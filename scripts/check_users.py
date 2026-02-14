import asyncio
from app.db.database import AsyncSessionLocal
from app.db.db_models import User
from sqlalchemy import select

async def check_users():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"Phone: {u.phone}, Email: {u.email}, Active: {u.is_active}")

if __name__ == '__main__':
    asyncio.run(check_users())
