@echo off
REM Script to apply Django migrations for HandwerkML

echo.
echo Applying Django Migrations...
echo.

cd /d "%~dp0"

REM Create migrations
echo Creating migrations for calculator app...
python manage.py makemigrations calculator

if %errorlevel% neq 0 (
    echo Error: Failed to create migrations
    pause
    exit /b 1
)

REM Apply migrations
echo.
echo Applying migrations to database...
python manage.py migrate

if %errorlevel% neq 0 (
    echo Error: Failed to apply migrations
    pause
    exit /b 1
)

echo.
echo Success! Migrations applied.
echo.
pause
