"""
Seed script to create default roles and test users
Run: python seed_users.py
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime, timezone
import uuid
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
db_name = os.environ['DB_NAME']

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


async def seed_users():
    """Create test users for each role"""
    client = AsyncIOMotorClient(mongo_url)
    db = client[db_name]
    
    # Test users
    users = [
        {
            "id": str(uuid.uuid4()),
            "email": "auditor@radiance.com",
            "password_hash": hash_password("auditor123"),
            "full_name": "John Doe (Auditor)",
            "role": "auditor",
            "team_id": "TEAM-A",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "manager@radiance.com",
            "password_hash": hash_password("manager123"),
            "full_name": "Sarah Smith (Manager)",
            "role": "manager",
            "team_id": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "admin@radiance.com",
            "password_hash": hash_password("admin123"),
            "full_name": "Admin User",
            "role": "admin",
            "team_id": None,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "email": "auditor2@radiance.com",
            "password_hash": hash_password("auditor123"),
            "full_name": "Mike Johnson (Auditor)",
            "role": "auditor",
            "team_id": "TEAM-B",
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Check and insert users
    for user in users:
        existing = await db.users.find_one({"email": user["email"]})
        if existing:
            print(f"✓ User already exists: {user['email']}")
        else:
            await db.users.insert_one(user)
            print(f"✓ Created user: {user['email']} (Role: {user['role']})")
    
    print("\n" + "="*60)
    print("SEED COMPLETED - Test User Credentials:")
    print("="*60)
    print("\n📋 AUDITOR ACCOUNT:")
    print("   Email: auditor@radiance.com")
    print("   Password: auditor123")
    print("   Role: auditor")
    print("   Team: TEAM-A")
    print("   Access: Assigned audits and personal metrics only")
    
    print("\n📋 AUDITOR 2 ACCOUNT:")
    print("   Email: auditor2@radiance.com")
    print("   Password: auditor123")
    print("   Role: auditor")
    print("   Team: TEAM-B")
    
    print("\n👔 MANAGER ACCOUNT:")
    print("   Email: manager@radiance.com")
    print("   Password: manager123")
    print("   Role: manager")
    print("   Access: Full analytics, reports, configurations")
    
    print("\n🔧 ADMIN ACCOUNT:")
    print("   Email: admin@radiance.com")
    print("   Password: admin123")
    print("   Role: admin")
    print("   Access: All permissions\n")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(seed_users())
