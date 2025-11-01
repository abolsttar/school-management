# 🚀 راهنمای Setup پروژه - برای Code Reviewer

## ✅ چیزهایی که باید انجام بدی:

### 1. Git Setup (اولویت اول!)
```powershell
# Initialize Git
git init

# Add all files
git add .

# First commit
git commit -m "Initial commit: Complete school management system"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/school-management.git
git branch -M main
git push -u origin main
```

**قانون:** بعد از هر تغییر مهم، commit کن:
```powershell
git add .
git commit -m "Description of changes"
git push
```

### 2. Logging ✅ (انجام شده)
- لاگ‌ها در `logs/app.log` و `logs/error.log` ذخیره می‌شن
- همه actions لاگ می‌شن
- Errors با full traceback لاگ می‌شن

### 3. Code Organization ✅ (انجام شده)
- کد با block comments سازماندهی شده
- هر function docstring داره
- Sections جداگانه برای هر بخش

### 4. Error Handling ✅ (بهبود داده شده)
- Custom exceptions اضافه شده
- Try-catch در تمام endpoints
- Proper error logging

### 5. Research & Updates
- هر هفته FastAPI, Pydantic, MongoDB docs رو چک کن
- Dependencies رو update کن: `pip list --outdated`
- Best practices رو مطالعه کن

### 6. Keyboard Manager Tools
- استفاده از **Cursor** (که داری استفاده می‌کنی) ✅
- **Raycast** یا **Alfred** برای quick actions
- **BetterTouchTool** برای shortcuts

### 7. VPN مناسب
- برای دسترسی به GitHub و docs

### 8. XMind / Mind Mapping
- Architecture پروژه رو visualize کن
- Flow charts برای features

---

## 📁 ساختار پروژه:

```
University/
├── main.py              # Main application (960 lines)
├── requirements.txt      # Dependencies
├── docker-compose.yml    # MongoDB & Redis setup
├── .gitignore           # Git ignore rules
├── templates/           # HTML templates
│   ├── dashboard.html
│   ├── attendance.html
│   ├── students.html
│   ├── login.html
│   └── reports.html
└── logs/                # Auto-generated
    ├── app.log
    └── error.log
```

---

## 🎯 Next Steps (برای Code Reviewer):

1. **Git Setup**: فوری! (گفتی commit لحظه به لحظه)
2. **Test کردن**: تمام endpoints رو test کن
3. **Documentation**: API docs در `/api/docs` موجوده
4. **Monitoring**: Logs رو چک کن در `logs/` folder

---

## 💡 نکات مهم:

- ⚠️ **عجله نکن**: هر تغییر رو تست کن قبل از commit
- 📝 **Logs رو بخون**: برای debugging
- 🔄 **Regular commits**: بعد از هر feature
- 📚 **Docs بخون**: برای استفاده از latest methods

