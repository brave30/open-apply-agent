$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
$pin = '9a120949aca3e58a2628f4b4e6edd0474d984873'
if (!(Test-Path 'vendor/OpenWebRL/.git')) {
    git clone https://github.com/OpenWebRL/OpenWebRL.git vendor/OpenWebRL
    if ($LASTEXITCODE -ne 0) { throw 'OpenWebRL clone failed' }
    git -C vendor/OpenWebRL checkout $pin
    if ($LASTEXITCODE -ne 0) { throw 'OpenWebRL checkout failed' }
}
$revision = git -C vendor/OpenWebRL rev-parse HEAD
if ($revision -ne $pin) { throw 'Unexpected upstream revision; use the documented pin.' }
if (!(Test-Path '.venv/Scripts/python.exe')) { python -m venv .venv }
python -m uv --version 2>$null
if ($LASTEXITCODE -eq 0) {
    python -m uv pip install --python .venv/Scripts/python.exe -e '.[test]'
} else {
    .venv/Scripts/python -m pip install -e '.[test]'
}
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
.venv/Scripts/python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed' }
Write-Host 'Ready. Run .venv/Scripts/python -m auto_apply.cli demo'
