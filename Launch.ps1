param([ValidateSet('install','update','uninstall','recover','status')][string]$Action = 'install')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
try {
    Add-Type -AssemblyName System.Windows.Forms
    $picker = New-Object System.Windows.Forms.FolderBrowserDialog
    $picker.Description = 'Forge Neo: select the folder containing webui.py (or its EasyForgeNeo parent).'
    $picker.ShowNewFolderButton = $false
    if ($picker.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { exit 0 }
    $targetRoot = $picker.SelectedPath
    if (Test-Path -LiteralPath (Join-Path $targetRoot 'sd-webui-forge-neo\webui.py')) {
        $targetRoot = Join-Path $targetRoot 'sd-webui-forge-neo'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $targetRoot 'webui.py'))) { throw 'webui.py not found. Select the Forge Neo folder.' }
    $pythonExe = Join-Path $targetRoot 'venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        $candidate = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $candidate) { throw 'Python 3.10+ is required. Install Forge Neo dependencies first.' }
        $pythonExe = $candidate.Source
    }
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) {
        $portableGit = Join-Path (Split-Path $targetRoot -Parent) 'EasyTools\Git\env\PortableGit\bin'
        if (Test-Path -LiteralPath (Join-Path $portableGit 'git.exe')) { $env:PATH = "$portableGit;$env:PATH" }
        else { throw 'Git is required. Install Git for Windows first.' }
    }
    & $pythonExe -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 or later is required.' }
    $managerArgs = @((Join-Path $PSScriptRoot 'manager.py'), $Action, '--root', $targetRoot)
    if ($Action -ne 'status') { $managerArgs += '--interactive' }
    if ($Action -eq 'update') { $managerArgs += '--online' }
    & $pythonExe @managerArgs
    exit $LASTEXITCODE
} catch {
    Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
    exit 1
}
