"""
Tests for student CRUD endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_student(client: AsyncClient, clean_db, sample_student_data):
    """Test creating a new student."""
    response = await client.post("/students", json=sample_student_data)
    assert response.status_code == 201
    data = response.json()
    assert data["student_code"] == "ST001"
    assert data["name"] == "Test Student"


@pytest.mark.asyncio
async def test_create_student_duplicate_code(client: AsyncClient, clean_db, sample_student_data):
    """Test creating student with duplicate code fails."""
    await client.post("/students", json=sample_student_data)
    response = await client.post("/students", json=sample_student_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_all_students(client: AsyncClient, clean_db, sample_student_data):
    """Test getting all students."""
    # Create a student first
    await client.post("/students", json=sample_student_data)
    
    response = await client.get("/students")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(s["student_code"] == "ST001" for s in data)


@pytest.mark.asyncio
async def test_get_student_by_code(client: AsyncClient, clean_db, sample_student_data):
    """Test getting a student by code."""
    await client.post("/students", json=sample_student_data)
    
    response = await client.get("/students/ST001")
    assert response.status_code == 200
    data = response.json()
    assert data["student_code"] == "ST001"
    assert data["name"] == "Test Student"


@pytest.mark.asyncio
async def test_get_student_not_found(client: AsyncClient, clean_db):
    """Test getting non-existent student returns 404."""
    response = await client.get("/students/NOTEXIST")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_student(client: AsyncClient, clean_db, sample_student_data):
    """Test updating a student."""
    await client.post("/students", json=sample_student_data)
    
    update_data = {"name": "Updated Name", "grade": "11"}
    response = await client.put("/students/ST001", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["grade"] == "11"


@pytest.mark.asyncio
async def test_delete_student(client: AsyncClient, clean_db, sample_student_data):
    """Test deleting a student."""
    await client.post("/students", json=sample_student_data)
    
    response = await client.delete("/students/ST001")
    assert response.status_code == 200
    
    # Verify deletion
    response = await client.get("/students/ST001")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_validation(client: AsyncClient, clean_db):
    """Test student data validation."""
    invalid_data = {
        "student_code": "ST002",
        "name": "",  # Empty name
        "email": "invalid-email"  # Invalid email
    }
    response = await client.post("/students", json=invalid_data)
    assert response.status_code == 422

