# Gera narração com as vozes OneCore do Windows (offline).
# Uso: powershell -ExecutionPolicy Bypass -File tools\tts_onecore.ps1 -Lines falas.json -OutDir pasta -Voice Daniel
# falas.json = [{"id": "01", "text": "Olá..."}, ...]  -> pasta\01.wav
param(
    [Parameter(Mandatory = $true)][string]$Lines,
    [Parameter(Mandatory = $true)][string]$OutDir,
    [string]$Voice = "Maria",
    [string]$Rate = "1.0"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($operation, [Type]$type) {
    $task = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
    $task.Wait(-1) | Out-Null
    $task.Result
}
[Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime] | Out-Null
$synth = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$chosen = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | Where-Object { $_.DisplayName -like "*$Voice*" -and $_.Language -eq 'pt-BR' } | Select-Object -First 1
if ($null -eq $chosen) { throw "Voz $Voice (pt-BR) não encontrada." }
$synth.Voice = $chosen
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$items = Get-Content -Raw -Encoding UTF8 $Lines | ConvertFrom-Json
foreach ($item in $items) {
    $escaped = [System.Security.SecurityElement]::Escape($item.text)
    $ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='pt-BR'><prosody rate='$Rate'>$escaped</prosody></speak>"
    $stream = Await ($synth.SynthesizeSsmlToStreamAsync($ssml)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
    $reader = New-Object Windows.Storage.Streams.DataReader($stream.GetInputStreamAt(0))
    $size = [UInt32]$stream.Size
    Await ($reader.LoadAsync($size)) ([UInt32]) | Out-Null
    $bytes = New-Object byte[] $size
    $reader.ReadBytes($bytes)
    [IO.File]::WriteAllBytes((Join-Path $OutDir ($item.id + ".wav")), $bytes)
    $reader.Dispose(); $stream.Dispose()
}
Write-Output "ok $($items.Count) $($chosen.DisplayName)"
