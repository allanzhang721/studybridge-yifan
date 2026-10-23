param([int]$Port = 8502)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$studybridgePython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $studybridgePython)) {
    Write-Host 'Create the environment first: python -m venv .venv'
    Write-Host 'Then install: .venv/Scripts/python.exe -m pip install -r requirements.txt'
    exit 1
}
& $studybridgePython -m streamlit run app.py --server.port $Port --server.address 127.0.0.1

