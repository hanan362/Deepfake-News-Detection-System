# Downloads the pretrained models (CLIP, the evidence NLI model, the video frame classifier) once, about 1 GB in total, so
# that the first analysis on each page does not wait for them. Usage: download_models.ps1 [clip] [nli] [video]
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
& (Join-Path $Root ".venv\Scripts\python.exe") scripts\setup\download_models.py @args
exit $LASTEXITCODE
