@echo off
chcp 65001 >nul
echo ========================================
echo   RetailAI - Demo Başlatıcı 🏪✨
echo ========================================
echo.

REM Virtual environment'ı aktifleştir
if exist venv\Scripts\activate.bat (
    echo [1/3] Virtual environment aktifleştiriliyor...
    call venv\Scripts\activate.bat
) else (
    echo ❌ HATA: venv bulunamadı!
    echo Önce şunu çalıştır: python -m venv venv
    pause
    exit /b 1
)

echo.
echo [2/3] FastAPI servisi başlatılıyor...
echo       📍 URL: http://localhost:8000/ui/
echo       🔐 Login: admin / retailai2025
echo.
echo ⚠️  ÖNEMLI: Demo verisini yüklemek için yeni terminal aç ve şunu çalıştır:
echo     curl -X POST http://localhost:8000/seed/demo_data -u admin:retailai2025
echo     curl -X POST http://localhost:8000/migrate/add_status_columns -u admin:retailai2025
echo.
echo [3/3] Sunucu çalışıyor... (Durdurmak için Ctrl+C)
echo ========================================
echo.

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
