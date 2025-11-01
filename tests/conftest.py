"""
Pytest configuration and fixtures for testing.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis

# Import app after setting test environment
import os
os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB"] = "test_school_db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["ADMIN_API_KEY"] = "test-api-key"
os.environ["SMS_PROVIDER"] = "log"

from main import app, mongo_client, mongo_db, redis_client


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
async def clean_db():
    """Clean database before each test."""
    if mongo_db is not None:
        await mongo_db["students"].delete_many({})
        await mongo_db["attendance"].delete_many({})
    yield
    # Cleanup after test
    if mongo_db is not None:
        await mongo_db["students"].delete_many({})
        await mongo_db["attendance"].delete_many({})


@pytest.fixture(scope="function")
async def clean_cache():
    """Clean Redis cache before each test."""
    if redis_client is not None:
        rc = redis_client
        keys = await rc.keys("*")
        if keys:
            await rc.delete(*keys)
    yield
    # Cleanup after test
    if redis_client is not None:
        rc = redis_client
        keys = await rc.keys("*")
        if keys:
            await rc.delete(*keys)


@pytest.fixture
def sample_student_data():
    """Sample student data for testing."""
    return {
        "student_code": "ST001",
        "name": "Test Student",
        "email": "test@example.com",
        "phone": "09123456789",
        "grade": "10",
        "class_name": "A"
    }

