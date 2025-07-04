@echo off
echo GP Audio Downloader - Demarrage...
echo.

REM Verifier si Python est installe
python --version >nul 2>&1
if errorlevel 1 (
    echo Erreur: Python n'est pas installe ou n'est pas dans le PATH
    echo Veuillez installer Python 3.8+ depuis https://python.org
    pause
    exit /b 1
)

REM Verifier si les dependances sont installees
echo Verification des dependances...
pip show PySide6 >nul 2>&1
if errorlevel 1 (
    echo Installation des dependances...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Erreur lors de l'installation des dependances
        pause
        exit /b 1
    )
)

REM Lancer l'application
echo Lancement de GP Audio Downloader...
echo.
python main.py

REM Pause si erreur
if errorlevel 1 (
    echo.
    echo Une erreur s'est produite lors du lancement
    pause
)