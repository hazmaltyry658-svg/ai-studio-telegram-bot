@echo off
cd /d %~dp0
if not exist .env (
  copy .env.example .env
  echo.
  echo تم إنشاء .env. افتحه وضع المفاتيح ثم شغل الملف مرة أخرى.
  pause
  exit /b
)
python -m pip install -r requirements.txt
python -m app.bot
pause
