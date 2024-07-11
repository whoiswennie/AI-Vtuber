@echo on
chcp 65001

echo Running Python script...
call runtime\miniconda3\envs\ai-vtuber\python.exe -m streamlit run UI\streamlit_ui.py > output.log 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error occurred. Check output.log for details.
    exit /b %ERRORLEVEL%
)

echo Script finished successfully.
