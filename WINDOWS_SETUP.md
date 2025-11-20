# 🪟 Windows Setup Guide - Retail AI MVP

## ❌ Fixing the "ModuleNotFoundError: No module named 'jose'" Error

You're seeing this error because the required Python packages haven't been installed yet. Here's how to fix it:

## 🚀 Quick Fix (Recommended)

### Option 1: Install All Dependencies at Once

Open your terminal (PowerShell or CMD) in the project directory and run:

```bash
pip install -r requirements-mvp.txt
```

**Note**: This might take 5-10 minutes as it installs all packages.

### Option 2: Install Dependencies Step by Step

If you encounter errors with the full installation, install packages in groups:

```bash
# 1. Core Framework
pip install fastapi==0.104.1 uvicorn[standard]==0.24.0 pydantic==2.5.0 pydantic-settings==2.1.0

# 2. Database (IMPORTANT!)
pip install sqlalchemy[asyncio]==2.0.23 alembic==1.12.1

# For Windows, use pre-built wheels:
pip install asyncpg==0.29.0
pip install psycopg2-binary==2.9.9

# 3. Authentication & Security (THIS FIXES YOUR ERROR!)
pip install python-jose[cryptography]==3.3.0
pip install passlib[bcrypt]==1.7.4
pip install python-multipart==0.0.6
pip install bcrypt==4.1.1

# 4. Utilities
pip install python-dotenv==1.0.0
pip install email-validator==2.1.0
pip install httpx==0.25.2

# 5. Redis (Optional for now)
pip install redis==5.0.1

# 6. Development Tools
pip install pytest==7.4.3
pip install pytest-asyncio==0.21.1
```

## 🔧 Complete Windows Setup Guide

### Prerequisites

1. **Python 3.11 or higher**
   - Download from: https://www.python.org/downloads/
   - ✅ Check "Add Python to PATH" during installation
   - Verify: `python --version`

2. **PostgreSQL 15+**
   - Download from: https://www.postgresql.org/download/windows/
   - Default port: 5432
   - Remember your password!

3. **Git** (if using version control)
   - Download from: https://git-scm.com/download/win

### Step-by-Step Installation

#### Step 1: Create Virtual Environment

```bash
# Open PowerShell or CMD in project directory
cd C:\Users\benyu\Desktop\retail-ai-claude-mvp-saas...

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# You should see (venv) in your prompt
```

#### Step 2: Upgrade pip

```bash
python -m pip install --upgrade pip setuptools wheel
```

#### Step 3: Install Dependencies

```bash
# Option A: All at once (may take time)
pip install -r requirements-mvp.txt

# Option B: Core only (if you get errors)
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] alembic asyncpg pydantic pydantic-settings python-jose[cryptography] passlib[bcrypt] python-multipart python-dotenv email-validator
```

#### Step 4: Set Up Environment File

```bash
# Copy the template
copy .env.mvp .env

# Edit .env file with your settings (use Notepad or VS Code)
```

**Important .env settings for Windows:**

```ini
# Database (Update with your PostgreSQL details)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/retail_mvp

# For local development
DEBUG=true
LOG_LEVEL=DEBUG

# Security (change in production!)
JWT_SECRET_KEY=your-super-secret-key-change-this-32-chars-minimum

# CORS for local development
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://localhost:8080"]
```

#### Step 5: Create Database

```bash
# Open PostgreSQL (psql) or pgAdmin
# Create database:
CREATE DATABASE retail_mvp;
CREATE USER retail_user WITH PASSWORD 'retail_password';
GRANT ALL PRIVILEGES ON DATABASE retail_mvp TO retail_user;
```

Or use the default postgres user and update your DATABASE_URL accordingly.

#### Step 6: Run Database Migrations

```bash
# Make sure virtual environment is activated
alembic upgrade head
```

#### Step 7: Start the Application

```bash
# Method 1: Using the new MVP app
uvicorn app.main_mvp:app --reload --host 0.0.0.0 --port 8000

# Method 2: If you want to use the old app temporarily
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Step 8: Verify It's Working

Open your browser and go to:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## 🐳 Alternative: Using Docker (Easier!)

If you have Docker Desktop for Windows installed:

### Step 1: Install Docker Desktop
Download from: https://www.docker.com/products/docker-desktop/

### Step 2: Run Setup Script

```bash
# Open PowerShell as Administrator
cd C:\Users\benyu\Desktop\retail-ai-claude-mvp-saas...

# Run the Windows startup script
.\scripts\start-mvp.bat
```

This will:
- Create .env file
- Start PostgreSQL
- Start Redis
- Start the application
- Run migrations
- Set up everything automatically

### Step 3: Access the Application

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **pgAdmin**: http://localhost:5050 (admin@retailai.com / admin)

## 🔥 Troubleshooting Common Windows Issues

### Issue 1: "asyncpg" installation fails

**Solution**: Use pre-built wheel
```bash
pip install asyncpg --only-binary :all:
```

### Issue 2: "psycopg2" installation fails

**Solution**: Use binary version
```bash
pip install psycopg2-binary
```

### Issue 3: "python-jose[cryptography]" fails

**Solution**: Install cryptography first
```bash
pip install cryptography
pip install python-jose[cryptography]
```

### Issue 4: Can't connect to PostgreSQL

**Solutions**:
1. Check if PostgreSQL is running (Services → postgresql-x64-15)
2. Verify password in .env file
3. Try using `127.0.0.1` instead of `localhost`
4. Check firewall settings

### Issue 5: Port 8000 already in use

**Solution**: Use different port
```bash
uvicorn app.main_mvp:app --reload --port 8001
```

### Issue 6: Virtual environment activation issues (PowerShell)

**Solution**: Enable script execution
```bash
# Run as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate
venv\Scripts\activate
```

## 📝 Quick Commands Reference

### Activate Virtual Environment
```bash
# CMD
venv\Scripts\activate.bat

# PowerShell
venv\Scripts\Activate.ps1

# Git Bash
source venv/Scripts/activate
```

### Deactivate Virtual Environment
```bash
deactivate
```

### Reinstall Everything (Clean Install)
```bash
# Deactivate venv
deactivate

# Delete venv folder
rmdir /s venv

# Create new venv
python -m venv venv
venv\Scripts\activate

# Install fresh
pip install -r requirements-mvp.txt
```

### Check Installed Packages
```bash
pip list
pip show python-jose
```

### Run Migrations
```bash
# Upgrade to latest
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Rollback
alembic downgrade -1
```

### Start Development Server
```bash
# With auto-reload
uvicorn app.main_mvp:app --reload

# Different host/port
uvicorn app.main_mvp:app --host 0.0.0.0 --port 8001 --reload

# With log level
uvicorn app.main_mvp:app --reload --log-level debug
```

## 🎯 Next Steps After Setup

1. **Test the API**:
   - Go to http://localhost:8000/docs
   - Try the `/health` endpoint
   - Register a user via `/api/v1/auth/register`

2. **Create First Product**:
   - Login to get JWT token
   - Use token to create a product
   - Check dashboard metrics

3. **Upload Receipt**:
   - Upload a receipt image
   - Check processing status
   - View extracted items

## 💡 Pro Tips

1. **Always use virtual environment** to avoid package conflicts
2. **Use VS Code** with Python extension for better development experience
3. **Install pgAdmin** for easier database management
4. **Use Postman** or **Thunder Client** for API testing
5. **Enable WSL2** for better Docker performance on Windows

## 🆘 Still Having Issues?

1. Check Python version: `python --version` (should be 3.11+)
2. Check pip version: `pip --version`
3. Verify virtual environment is activated (see `(venv)` in prompt)
4. Try installing packages one by one to identify the problematic one
5. Check Windows Event Viewer for system-level errors
6. Make sure antivirus isn't blocking Python

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy**: https://docs.sqlalchemy.org/
- **Alembic**: https://alembic.sqlalchemy.org/
- **PostgreSQL Windows**: https://www.postgresql.org/docs/
- **Python Virtual Environments**: https://docs.python.org/3/tutorial/venv.html

---

**Happy Coding! 🚀**

If you encounter any other issues, please create an issue on GitHub with:
- Full error message
- Python version
- Windows version
- Steps to reproduce
