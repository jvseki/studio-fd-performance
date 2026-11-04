param()
$ErrorActionPreference = 'Stop'
function Get-SharedFileHash([string]$FilePath) {
    if (-not (Test-Path -LiteralPath $FilePath)) { return $null }
    $stream = [IO.File]::Open($FilePath, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '')
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$appVersion = & (Join-Path $projectRoot '.venv\Scripts\python.exe') -c 'from studio_fd import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao ler a versao.' }
$installer = Join-Path $projectRoot ('release\StudioFDPerformance-Setup-' + $appVersion.Trim() + '.exe')
$uninstallKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{A71B7309-A7B7-4BDA-A1EC-26B673AEBC84}_is1'
if (Test-Path -LiteralPath $uninstallKey) {
    throw 'Ja existe uma instalacao registrada. Use uma conta de teste para nao alterar o aplicativo instalado.'
}
$testRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot ('build\install-check-' + [guid]::NewGuid().ToString('N'))))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'build')) + '\'
if (-not $testRoot.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'O destino de teste precisa estar dentro de build.'
}
$dataRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'StudioFDPerformance\data'
$database = Join-Path $dataRoot 'studio_fd.db'
$beforeHash = Get-SharedFileHash $database
$installLog = Join-Path $projectRoot 'build\installer-test.log'
$uninstallLog = Join-Path $projectRoot 'build\uninstaller-test.log'
$arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/NOICONS', '/TASKS=""', ('/DIR="' + $testRoot + '"'), ('/LOG="' + $installLog + '"'))
$process = Start-Process -FilePath $installer -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Instalacao falhou: $($process.ExitCode)" }
try {
    $exePath = Join-Path $testRoot 'Studio FD Performance.exe'
    if (-not (Test-Path -LiteralPath $exePath)) { throw 'Executavel nao instalado.' }
    & (Join-Path $projectRoot '.venv\Scripts\python.exe') (Join-Path $projectRoot 'tools\test_frozen.py') $exePath
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao testar o executavel instalado.' }
} finally {
    $uninstaller = Join-Path $testRoot 'unins000.exe'
    if (Test-Path -LiteralPath $uninstaller) {
        $uninstallArguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', ('/LOG="' + $uninstallLog + '"'))
        $process = Start-Process -FilePath $uninstaller -ArgumentList $uninstallArguments -WindowStyle Hidden -PassThru -Wait
        if ($process.ExitCode -ne 0) { throw "Desinstalacao falhou: $($process.ExitCode)" }
    }
}
if (Test-Path -LiteralPath (Join-Path $testRoot 'Studio FD Performance.exe')) { throw 'O executavel permaneceu apos desinstalar.' }
if (Test-Path -LiteralPath $uninstallKey) { throw 'O registro da instalacao permaneceu apos desinstalar.' }
$afterHash = Get-SharedFileHash $database
if ($beforeHash -ne $afterHash) { throw 'O banco real foi alterado durante o teste.' }
Write-Output 'OK: instalacao, aplicativo instalado, desinstalacao e preservacao do banco real verificados.'
