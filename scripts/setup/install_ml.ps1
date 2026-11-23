param([switch]$SkipModels)
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py -m pip install torch --index-url https://download.pytorch.org/whl/cpu
if ($LASTEXITCODE -ne 0) { throw "Installing torch failed (exit code $LASTEXITCODE)." }
& $Py -m pip install -r backend\requirements-ml.txt
if ($LASTEXITCODE -ne 0) { throw "Installing the machine-learning packages failed (exit code $LASTEXITCODE)." }
# Fetch the pretrained models now (about 1 GB) so the first analysis on each page is not slow. -SkipModels skips this step.
# A failed download does not fail the install: each model is then fetched the first time its page is used.
if (-not $SkipModels) {
  & $Py scripts\setup\download_models.py
  if ($LASTEXITCODE -ne 0) { Write-Warning "Some models were not downloaded. Run scripts\setup\download_models.ps1 later." }
}
