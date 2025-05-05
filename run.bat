@echo off
REM Batch script to activate the virtual environment and run the Streamlit application

echo Activating virtual environment...
REM Assuming the virtual environment is named .venv and located in the project root
call .\.venv\Scripts\activate

if %errorlevel% neq 0 (
    echo ERROR: Failed to activate virtual environment. Make sure it exists at ".\.venv".
    pause
    exit /b %errorlevel%
)

echo Starting Streamlit application...
echo You can access it at the URLs provided by Streamlit below.

streamlit run app/app.py

echo.
echo Streamlit server stopped or failed to start.
pause 