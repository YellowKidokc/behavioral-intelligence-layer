# PIL Install Script — Phase 1
# Run in PowerShell as Administrator from D:\BIL

Write-Host "=== PIL — Personal Intelligence Layer ===" -ForegroundColor Cyan
Write-Host "=== Phase 1 Install                   ===" -ForegroundColor Cyan

# Create all directories
$dirs = @(
    "D:\BIL\data\captures",
    "D:\BIL\data\understood",
    "D:\BIL\data\embeddings",
    "D:\BIL\data\ratings",
    "D:\BIL\data\clips",
    "D:\BIL\data\github",
    "D:\BIL\data\memory",
    "D:\BIL\data\digests",
    "D:\BIL\engines\perception",
    "D:\BIL\engines\embeddings",
    "D:\BIL\engines\github",
    "D:\BIL\engines\memory",
    "D:\BIL\engines\synthesis",
    "D:\BIL\engines\truth",
    "D:\BIL\ui"
)

Write-Host "`nCreating directories..." -ForegroundColor Yellow
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  + $dir" -ForegroundColor Green
    }
}

# Python packages
Write-Host "`nInstalling Python packages..." -ForegroundColor Yellow
$packages = @("mss", "keyboard", "pillow", "requests", "pystray", "pywin32")
foreach ($pkg in $packages) {
    Write-Host "  pip install $pkg" -ForegroundColor Gray
    pip install $pkg --quiet
}

# Ollama models
Write-Host "`nPulling Ollama models..." -ForegroundColor Yellow
Write-Host "  moondream (vision — understands screenshots)"
ollama pull moondream
Write-Host "  llama3 (synthesis — daily organizer)"
ollama pull llama3

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run:" -ForegroundColor Cyan
Write-Host "  START_BILL.bat                           (BIL preference engine)"
Write-Host "  python desktop-capture\hotkey_capture.py (Ctrl+Shift+S to capture)"
Write-Host "  python desktop-capture\watcher.py        (passive every 5 min)"
