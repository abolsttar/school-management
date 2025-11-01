"""
Tests for attendance endpoints.
"""
import pytest
from httpx import AsyncClient
from datetime import datetime, date


@pytest.mark.asyncio
async def test_mark_attendance(client: AsyncClient, clean_db, sample_student_data):
    """Test marking attendance for a student."""
    # Create student first
    await client.post("/students", json=sample_student_data)
    
    attendance_data = {
        "student_code": "ST001",
        "date": str(date.today()),
        "status": "present"
    }
    response = await client.post("/attendance/mark", json=attendance_data)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "present"
    assert data["student_code"] == "ST001"


@pytest.mark.asyncio
async def test_mark_attendance_absent(client: AsyncClient, clean_db, sample_student_data):
    """Test marking student as absent."""
    await client.post("/students", json=sample_student_data)
    
    attendance_data = {
        "student_code": "ST001",
        "date": str(date.today()),
        "status": "absent"
    }
    response = await client.post("/attendance/mark", json=attendance_data)
    assert response.status_code == 201
    assert response.json()["status"] == "absent"


@pytest.mark.asyncio
async def test_mark_attendance_duplicate(client: AsyncClient, clean_db, sample_student_data):
    """Test marking duplicate attendance fails."""
    await client.post("/students", json=sample_student_data)
    
    attendance_data = {
        "student_code": "ST001",
        "date": str(date.today()),
        "status": "present"
    }
    await client.post("/attendance/mark", json=attendance_data)
    
    # Try to mark again
    response = await client.post("/attendance/mark", json=attendance_data)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_attendance_by_date(client: AsyncClient, clean_db, sample_student_data):
    """Test getting attendance records by date."""
    await client.post("/students", json=sample_student_data)
    
    today = str(date.today())
    attendance_data = {
        "student_code": "ST001",
        "date": today,
        "status": "present"
    }
    await client.post("/attendance/mark", json=attendance_data)
    
    response = await client.get(f"/attendance?date={today}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(a["student_code"] == "ST001" for a in data)


@pytest.mark.asyncio
async def test_get_attendance_by_student(client: AsyncClient, clean_db, sample_student_data):
    """Test getting attendance records for a student."""
    await client.post("/students", json=sample_student_data)
    
    attendance_data = {
        "student_code": "ST001",
        "date": str(date.today()),
        "status": "present"
    }
    await client.post("/attendance/mark", json=attendance_data)
    
    response = await client.get("/attendance?student_code=ST001")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

