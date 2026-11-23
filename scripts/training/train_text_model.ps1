param([string]$Stage = "all")
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
& (Join-Path $Root ".venv\Scripts\python.exe") ai_models\training\train_text_baseline.py $Stage
