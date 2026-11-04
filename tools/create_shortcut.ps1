param()
$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonWindowed = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$entryPoint = Join-Path $projectRoot 'main.py'
$iconPath = Join-Path $projectRoot 'assets\app.ico'
foreach ($required in @($pythonWindowed, $entryPoint, $iconPath)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Arquivo necessario nao encontrado: $required"
    }
}
# Um caminho proprio evita reutilizar a imagem antiga do Python no cache do Explorer.
$desktopIconPath = Join-Path $projectRoot 'assets\studio-fd-desktop.ico'
Copy-Item -LiteralPath $iconPath -Destination $desktopIconPath -Force
$desktopPath = [Environment]::GetFolderPath('Desktop')
if (-not $desktopPath -or -not (Test-Path -LiteralPath $desktopPath -PathType Container)) {
    throw 'Nao foi possivel localizar a Area de Trabalho deste usuario.'
}
$shortcutPath = Join-Path $desktopPath 'Studio FD Performance - Desenvolvimento.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
if ((Test-Path -LiteralPath $shortcutPath) -and $shortcut.TargetPath -ne $pythonWindowed) {
    throw 'Ja existe um atalho com esse nome apontando para outro programa.'
}
$shortcut.TargetPath = $pythonWindowed
$shortcut.Arguments = '"' + $entryPoint + '"'
$shortcut.WorkingDirectory = $projectRoot
$shortcut.IconLocation = $desktopIconPath + ',0'
$shortcut.Description = 'Studio FD Performance - projeto em desenvolvimento'
$shortcut.Save()
if (-not ('StudioDesktopIconRefresh' -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class StudioDesktopIconRefresh {
    [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
    public static extern void SHChangeNotify(uint eventId, uint flags, string item1, IntPtr item2);
}
'@
}
[StudioDesktopIconRefresh]::SHChangeNotify(0x2000, 0x1005, $shortcutPath, [IntPtr]::Zero)
[StudioDesktopIconRefresh]::SHChangeNotify(0x08000000, 0, $null, [IntPtr]::Zero)
Write-Output $shortcutPath
