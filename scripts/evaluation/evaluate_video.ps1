$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py ai_models\training\prepare_video_data.py
& $Py ai_models\training\evaluate_video.py --write-registry @args
