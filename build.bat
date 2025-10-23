@echo off
echo ========================================
echo    Script de build Waksense
echo ========================================
echo.

echo [1/4] Verification des fichiers...
if not exist "src\main.py" (
    echo ERREUR: src\main.py introuvable
    pause
    exit /b 1
)
if not exist "src\classes\iop\tracker.py" (
    echo ERREUR: src\classes\iop\tracker.py introuvable
    pause
    exit /b 1
)
if not exist "src\classes\cra\tracker.py" (
    echo ERREUR: src\classes\cra\tracker.py introuvable
    pause
    exit /b 1
)
if not exist "assets\Waksense.ico" (
    echo ERREUR: assets\Waksense.ico introuvable
    pause
    exit /b 1
)
echo ✓ Tous les fichiers sources sont presents

echo.
echo [2/4] Nettoyage des builds precedents...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
echo ✓ Nettoyage termine

echo.
echo [3/4] Compilation avec PyInstaller...
pyinstaller --clean Waksense.spec
if %errorlevel% neq 0 (
    echo ERREUR: Echec de la compilation
    pause
    exit /b 1
)
echo ✓ Compilation reussie

echo.
echo [4/4] Copie vers releases...
if not exist "releases" mkdir "releases"
copy "dist\Waksense.exe" "releases\Waksense.exe"
if %errorlevel% neq 0 (
    echo ERREUR: Echec de la copie
    pause
    exit /b 1
)
echo ✓ Copie vers releases terminee

echo.
echo ========================================
echo    Build termine avec succes !
echo ========================================
echo.
echo L'executable est disponible dans :
echo   releases\Waksense.exe
echo.
echo Taille du fichier :
dir "releases\Waksense.exe" | findstr "Waksense.exe"
echo.
pause
