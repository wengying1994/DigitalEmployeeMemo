"""
Seed data script for initial database population.
Run this script to create initial users and departments for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from app.db.session import async_session_factory, init_db
from app.models import User, Department


async def seed_data():
    """Create initial seed data."""
    print("Initializing database tables...")
    await init_db()
    print("Tables created.")

    async with async_session_factory() as session:
        # Check if data already exists
        result = await session.execute(select(Department))
        if result.scalars().first():
            print("Seed data already exists, skipping...")
            return

        # Create departments
        departments = [
            Department(id=1, name="领导办公室", description="公司领导部门"),
            Department(id=2, name="企信中心", description="企业信息化中心"),
            Department(id=3, name="ICNOC", description="网络运维中心"),
            Department(id=4, name="ISOC", description="安全运维中心"),
        ]

        for dept in departments:
            session.add(dept)
        await session.flush()
        print(f"Created {len(departments)} departments")

        # Create users
        users = [
            User(id=1, name="李XX", email="lizhong@company.com", role="leader", dept_id=1,
                 is_deleted=False),
            User(id=2, name="吴XX", email="wuxx@company.com", role="dept_head", dept_id=2,
                 is_deleted=False),
            User(id=3, name="张ICNOC", email="zhang@company.com", role="member", dept_id=3,
                 is_deleted=False),
            User(id=4, name="刘ISOC", email="liu@company.com", role="member", dept_id=4,
                 is_deleted=False),
        ]

        for user in users:
            session.add(user)
        await session.flush()
        print(f"Created {len(users)} users")

        await session.commit()
        print("Seed data committed successfully!")


if __name__ == "__main__":
    asyncio.run(seed_data())
