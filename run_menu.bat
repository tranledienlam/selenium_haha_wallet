@echo off
cd /d %~dp0

REM Khởi tạo VENV_PATH trống
set VENV_PATH=

REM Đọc đường dẫn Python từ config.txt nếu có
if exist "config.txt" (
    for /f "tokens=1,2 delims==" %%a in ('findstr /C:"PYTHON_PATH=" config.txt') do (
        set VENV_PATH=%%b
    )
)

REM Kiểm tra và thiết lập Python path
if not "%VENV_PATH%"=="" (
    REM Có đường dẫn từ config, kiểm tra tồn tại
    if exist "%VENV_PATH%" (
        set PYTHON_PATH=%VENV_PATH%
    ) else (
        echo Canh bao: Moi truong ao khong ton tai: %VENV_PATH%
        echo Chuyen sang su dung Python he thong...
        goto :check_system_python
    )
) else (
    REM Không có config, kiểm tra Python hệ thống
    goto :check_system_python
)

goto :run_script

:check_system_python
REM Kiểm tra Python hệ thống
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_PATH=python
) else (
    echo ========================================
    echo    LOI: Python khong duoc tim thay!
    echo ========================================
    exit /b 1
)

:run_script
REM Chạy script Python với tham số nếu có
"%PYTHON_PATH%" index.py %*
echo ========================================
echo    Dong sau 5 giay...
echo ========================================
timeout /t 5 >nul
exit /b