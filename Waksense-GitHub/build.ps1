# Script de build Waksense (PowerShell)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Script de build Waksense" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Vérification des fichiers
Write-Host "[1/4] Vérification des fichiers..." -ForegroundColor Yellow
$requiredFiles = @(
    "src\main.py",
    "src\classes\iop\tracker.py", 
    "src\classes\cra\tracker.py",
    "assets\Waksense.ico"
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "ERREUR: $file introuvable" -ForegroundColor Red
        Read-Host "Appuyez sur Entrée pour quitter"
        exit 1
    }
}
Write-Host "✓ Tous les fichiers sources sont présents" -ForegroundColor Green

# Nettoyage
Write-Host ""
Write-Host "[2/4] Nettoyage des builds précédents..." -ForegroundColor Yellow
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
Write-Host "✓ Nettoyage terminé" -ForegroundColor Green

# Compilation
Write-Host ""
Write-Host "[3/4] Compilation avec PyInstaller..." -ForegroundColor Yellow
$result = & pyinstaller --clean Waksense.spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Échec de la compilation" -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}
Write-Host "✓ Compilation réussie" -ForegroundColor Green

# Copie vers releases
Write-Host ""
Write-Host "[4/4] Copie vers releases..." -ForegroundColor Yellow
if (-not (Test-Path "releases")) { New-Item -ItemType Directory -Name "releases" }
Copy-Item "dist\Waksense.exe" "releases\Waksense.exe"
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERREUR: Échec de la copie" -ForegroundColor Red
    Read-Host "Appuyez sur Entrée pour quitter"
    exit 1
}
Write-Host "✓ Copie vers releases terminée" -ForegroundColor Green

# Résumé
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "    Build terminé avec succès !" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "L'exécutable est disponible dans :" -ForegroundColor White
Write-Host "  releases\Waksense.exe" -ForegroundColor Green
Write-Host ""
Write-Host "Taille du fichier :" -ForegroundColor White
Get-ChildItem "releases\Waksense.exe" | Select-Object Name, Length, LastWriteTime
Write-Host ""
Read-Host "Appuyez sur Entrée pour quitter"
