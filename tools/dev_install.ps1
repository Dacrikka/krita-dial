# Dev install: links the plugin folder into Krita's pykrita, so edits are live after a Krita restart.
# Junction (mklink /J) needs no admin rights. Run with Krita closed.
# Uninstall: delete %APPDATA%\krita\pykrita\krita_dial (the junction only) and krita_dial.desktop.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pykrita = Join-Path $env:APPDATA "krita\pykrita"
$link = Join-Path $pykrita "krita_dial"
$target = Join-Path $root "krita_dial"

if (Test-Path $link) {
    $item = Get-Item $link -Force
    if ($item.LinkType -ne "Junction") {
        throw "$link exists and is not a junction: remove it manually"
    }
    Write-Host "Junction already present: $link -> $($item.Target)"
} else {
    cmd /c mklink /J "$link" "$target" | Out-Null
    Write-Host "Created junction: $link -> $target"
}

Copy-Item (Join-Path $root "krita_dial.desktop") $pykrita -Force
Write-Host "Copied krita_dial.desktop to $pykrita"
Write-Host "First time: Settings > Configure Krita > Python Plugin Manager > enable 'Krita Dial', restart Krita."
