where abaqus >nul 2>nul
if %errorlevel% neq 0 (
	echo abaqus python not found
	exit /b 2
)
:: abaqus python python_script odb_file zdf_file
:: %1 is the path to odb2zdf.py, %2 the path to odb file, %3 the path to zdf file to be output
abaqus python %1 %2 %3
if %errorlevel% neq 0 (
	echo command execution failed
	exit /b 1
)
echo Command executed successfully
exit /b 0