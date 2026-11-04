param(
    [string]$Version = '',
    [string]$Notes = '',
    [string]$InnoCompiler = ''
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$releaseArguments = @('-X', 'utf8', (Join-Path $projectRoot 'tools\release.py'))
if ($Version) { $releaseArguments += @('--version', $Version) }
else { $releaseArguments += '--interactive' }
if ($Notes) { $releaseArguments += @('--notes', $Notes) }
if ($InnoCompiler) { $releaseArguments += @('--inno-compiler', $InnoCompiler) }
& $python @releaseArguments
if ($LASTEXITCODE -ne 0) { throw 'A atualizacao nao foi gerada. Consulte o erro acima.' }
