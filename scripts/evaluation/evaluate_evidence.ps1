$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py ai_models\training\evaluate_evidence_nli.py @args
