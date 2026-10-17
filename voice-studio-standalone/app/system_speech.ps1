param([ValidateSet('list','speak')][string]$Action='list', [string]$InputFile)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($Action -eq 'list') {
        $voices = @($speaker.GetInstalledVoices() | Where-Object {$_.Enabled} | ForEach-Object {
            @{name=$_.VoiceInfo.Name; culture=$_.VoiceInfo.Culture.Name}
        })
        ConvertTo-Json -InputObject $voices -Compress
    } else {
        $job = Get-Content -LiteralPath $InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $speaker.SelectVoice([string]$job.voice)
        $speaker.Rate = 0
        $speaker.SetOutputToWaveFile([string]$job.output)
        $speaker.Speak([string]$job.text)
        $speaker.SetOutputToNull()
    }
} finally {$speaker.Dispose()}
