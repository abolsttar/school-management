# 🏫 School Management System

Complete school management system with student attendance tracking, SMS notifications, and analytics dashboard.

## ✨ Features

- **Student Management**: Full CRUD operations for student records
- **Attendance Tracking**: Mark and track student attendance
- **SMS Notifications**: Automatic SMS to parents when student is absent
- **Admin Dashboard**: Beautiful web interface for managing students and attendance
- **Analytics**: Real-time usage statistics and reports
- **Caching**: Redis-based caching for improved performance
- **Rate Limiting**: Protection against API abuse
- **Security**: Security headers and input validation
- **Comprehensive Logging**: Detailed logs for debugging and monitoring

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for MongoDB and Redis)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/abolsttar/school-management.git
   cd school-management
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup environment variables**
   ```bash
   # Copy the example file
   copy env.example.txt .env  # Windows
   # or
   cp env.example.txt .env  # Linux/Mac
   
   # Edit .env with your settings
   ```

5. **Start MongoDB and Redis**
   ```bash
   docker-compose up -d
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

   Or with uvicorn directly:
   ```bash
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

7. **Access the application**
   - API Documentation: http://127.0.0.1:8000/api/docs
   - Admin Panel: http://127.0.0.1:8000/admin/login
   - Default credentials: `admin` / `admin123`

## 📁 Project Structure

```
school-management/
├── main.py                 # Main FastAPI application
├── requirements.txt        # Python dependencies
├── docker-compose.yml     # MongoDB & Redis services
├── Dockerfile             # Production container
├── .env                   # Environment variables (create from env.example.txt)
├── tests/                 # Test files
│   ├── test_health.py
│   ├── test_students.py
│   └── test_attendance.py
├── templates/             # HTML templates
│   ├── dashboard.html
│   ├── login.html
│   ├── attendance.html
│   ├── students.html
│   └── reports.html
└── logs/                  # Application logs (auto-generated)
    ├── app.log
    └── error.log
```

## 🔧 Configuration

### Environment Variables

See `env.example.txt` for all available configuration options:

- `MONGO_URI`: MongoDB connection string
- `MONGO_DB`: Database name
- `REDIS_URL`: Redis connection URL
- `ADMIN_API_KEY`: API key for admin endpoints
- `SMS_PROVIDER`: SMS provider (`log` or `twilio`)
- `RATE_LIMIT_PER_MINUTE`: Requests per minute (default: 60)
- `RATE_LIMIT_PER_HOUR`: Requests per hour (default: 1000)

## 📚 API Endpoints

### Health & Status
- `GET /health` - Health check
- `GET /readiness` - Readiness check (database connections)

### Students
- `POST /students` - Create a new student
- `GET /students` - List all students
- `GET /students/{student_code}` - Get student by code
- `PUT /students/{student_code}` - Update student
- `DELETE /students/{student_code}` - Delete student

### Attendance
- `POST /attendance/mark` - Mark attendance
- `GET /attendance` - Get attendance records (with filters)

### Statistics
- `GET /stats/today` - Today's usage statistics
- `GET /stats/slowest` - Slowest endpoints
- `GET /stats/recent` - Recent API requests
- `GET /stats/endpoints` - Endpoint statistics

Full API documentation available at `/api/docs`

## 🧪 Testing

Run tests:
```bash
pytest tests/ -v
```

Run with coverage:
```bash
pytest tests/ --cov=main --cov-report=html
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose up -d  # MongoDB & Redis only
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🔒 Security Features

- **Rate Limiting**: Per-IP rate limiting (60/min, 1000/hour)
- **Security Headers**: XSS protection, frame options, content security policy
- **Input Validation**: Pydantic models for all inputs
- **API Key Authentication**: For admin endpoints

## 📊 Monitoring

- Logs are stored in `logs/app.log` and `logs/error.log`
- Usage statistics tracked in Redis
- Real-time dashboard at `/admin/stats`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**Abolsttar**
- GitHub: [@abolsttar](https://github.com/abolsttar)

## 🙏 Acknowledgments

- FastAPI for the excellent web framework
- MongoDB for flexible data storage
- Redis for high-performance caching

---

⭐ If you like this project, please give it a star!
