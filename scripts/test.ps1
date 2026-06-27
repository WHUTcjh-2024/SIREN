$ErrorActionPreference = 'Stop'
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest
Push-Location $PSScriptRoot\..\frontend
try {
    npm run build
} finally {
    Pop-Location
}
