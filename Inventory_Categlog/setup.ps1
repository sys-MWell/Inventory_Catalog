$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $python) {
	& $python.Source -3.9 -m venv .venv
} else {
	$python = Get-Command python -ErrorAction SilentlyContinue
	if ($null -eq $python) {
		throw 'Python was not found. Install Python 3.9 or newer, then run this script again.'
	}
	& $python.Source -m venv .venv
}

$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

Write-Host ''
Write-Host 'Setup complete.' -ForegroundColor Green
Write-Host "Virtual environment: $projectRoot\.venv"
Write-Host 'In Visual Studio, select this interpreter:'
Write-Host "  $venvPython"
Write-Host 'Then start run.py.'
