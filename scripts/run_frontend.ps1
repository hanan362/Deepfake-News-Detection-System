$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "frontend")
npm run dev
