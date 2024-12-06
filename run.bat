@echo off
:: 检查是否存在 abaqus python 命令
where abaqus >nul 2>nul
if %errorlevel% neq 0 (
    echo Abaqus Python not found.
    exit /b 2
)

:: 尝试执行 abaqus python get_data.py 命令
abaqus python displacement.py
if %errorlevel% neq 0 (
    echo Command failed.
    exit /b 1
)

echo Command executed successfully.
exit /b 0
