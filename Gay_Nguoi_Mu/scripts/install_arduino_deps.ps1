# Cai dat moi truong Arduino cho du an Gay Nguoi Mu
# Chay: powershell -ExecutionPolicy Bypass -File scripts\install_arduino_deps.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Cfg = Join-Path $env:USERPROFILE ".arduinoIDE\arduino-cli.yaml"

# Doc sketchbook thuc te tu arduino-cli.yaml (khong phai Documents\Arduino mac dinh)
$Sketchbook = Join-Path $env:USERPROFILE "Documents\Arduino"
if (Test-Path $Cfg) {
    $yaml = Get-Content $Cfg -Raw
    if ($yaml -match 'user:\s*(.+)') {
        $Sketchbook = $Matches[1].Trim()
    }
}
$ArduinoLibs = Join-Path $Sketchbook "libraries"
$LibSrc = Join-Path $ProjectRoot "libraries\gay_nguoi_mu_vnd_inferencing"
$LibFallback = Join-Path $env:USERPROFILE "Documents\Arduino\libraries\gay_nguoi_mu_vnd_inferencing"

function Test-EiLibrary($dir) {
    if (-not $dir) { return $false }
    return (Test-Path (Join-Path $dir "src\gay_nguoi_mu_vnd_inferencing.h")) -or
           (Test-Path (Join-Path $dir "gay_nguoi_mu_vnd_inferencing.h"))
}
$AudioLibName = "ESP32-audioI2S-master"
$AudioVersion = "3.4.6"

Write-Host "=== Gay Nguoi Mu - Cai dat Arduino ===" -ForegroundColor Cyan
Write-Host "Sketchbook: $Sketchbook"

if (-not (Get-Command arduino-cli -ErrorAction SilentlyContinue)) {
    Write-Host "LOI: Chua co arduino-cli. Cai Arduino IDE 2 hoac arduino-cli truoc." -ForegroundColor Red
    exit 1
}

Write-Host "[1/5] Cap nhat ESP32 core..."
arduino-cli core update-index --config-file $Cfg
arduino-cli core install esp32:esp32 --config-file $Cfg

Write-Host "[2/5] Cai ESP32-audioI2S $AudioVersion (TTS Google, Audio.connecttohost)..."
arduino-cli lib uninstall ESP8266Audio --config-file $Cfg 2>$null
arduino-cli lib install "${AudioLibName}@${AudioVersion}" --config-file $Cfg

$SketchbookPaths = @(
    $Sketchbook,
    $ProjectRoot,
    "C:\Gay_Nguoi_Mu"
) | Where-Object { $_ -and (Test-Path $_ -ErrorAction SilentlyContinue) } | Select-Object -Unique

# Copy ESP32-audioI2S vao moi sketchbook path (neu khac noi arduino-cli da cai)
$AudioInstalled = Join-Path $ArduinoLibs $AudioLibName
if (-not (Test-Path $AudioInstalled)) {
    $AudioInstalled = Join-Path $ProjectRoot "libraries\$AudioLibName"
}
$audioSrcResolved = $null
if (Test-Path $AudioInstalled) {
    $audioSrcResolved = (Resolve-Path $AudioInstalled).Path
}
if ($audioSrcResolved -and (Test-Path (Join-Path $audioSrcResolved "src\Audio.h"))) {
    foreach ($sb in $SketchbookPaths) {
        $audioDest = Join-Path $sb "libraries\$AudioLibName"
        $audioDestResolved = $null
        if (Test-Path $audioDest) {
            $audioDestResolved = (Resolve-Path $audioDest).Path
        }
        if ($audioDestResolved -eq $audioSrcResolved) {
            Write-Host "  OK $audioDest (da co san)" -ForegroundColor Green
            continue
        }
        New-Item -ItemType Directory -Path (Join-Path $sb "libraries") -Force | Out-Null
        if (Test-Path $audioDest) { Remove-Item $audioDest -Recurse -Force }
        Copy-Item -Path $audioSrcResolved -Destination $audioDest -Recurse -Force
        Write-Host "  -> $audioDest (ESP32-audioI2S)" -ForegroundColor Green
    }
} else {
    Write-Host "CANH BAO: Khong tim thay Audio.h trong $AudioInstalled" -ForegroundColor Yellow
}

$hasEiLib = Test-EiLibrary $LibSrc
if (-not $hasEiLib -and (Test-EiLibrary $LibFallback)) {
    Write-Host "Tim thay Edge Impulse trong Documents\Arduino\libraries - copy vao project..."
    New-Item -ItemType Directory -Path (Join-Path $ProjectRoot "libraries") -Force | Out-Null
    if (Test-Path $LibSrc) { Remove-Item $LibSrc -Recurse -Force }
    Copy-Item -Path $LibFallback -Destination $LibSrc -Recurse -Force
    $hasEiLib = $true
    Write-Host "  -> $LibSrc" -ForegroundColor Green
}
if (-not $hasEiLib) {
    Write-Host ""
    Write-Host "CANH BAO: Chua co library Edge Impulse tai:" -ForegroundColor Yellow
    Write-Host "  $LibSrc"
    Write-Host "Deploy tu Edge Impulse Studio -> Arduino library -> giai nen vao libraries\gay_nguoi_mu_vnd_inferencing\"
    Write-Host "Bo qua copy Edge Impulse va bien dich sketch can AI." -ForegroundColor Yellow
} else {
    Write-Host "[3/5] Copy Edge Impulse vao sketchbook..."
    $eiSrcResolved = (Resolve-Path $LibSrc).Path
    foreach ($sb in $SketchbookPaths) {
        $dest = Join-Path $sb "libraries\gay_nguoi_mu_vnd_inferencing"
        $destResolved = $null
        if (Test-Path $dest) { $destResolved = (Resolve-Path $dest).Path }
        if ($destResolved -eq $eiSrcResolved) {
            Write-Host "  OK $dest (da co san)" -ForegroundColor Green
            continue
        }
        New-Item -ItemType Directory -Path (Join-Path $sb "libraries") -Force | Out-Null
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item -Path $eiSrcResolved -Destination $dest -Recurse -Force
        Write-Host "  -> $dest" -ForegroundColor Green
    }
}

$fqbn = "esp32:esp32:esp32s3:PSRAM=opi,PartitionScheme=huge_app,FlashMode=qio,FlashSize=16M"
$fqbnEsp = "esp32:esp32:esp32:PSRAM=disabled,PartitionScheme=default,FlashMode=qio,FlashSize=4M"
$libDirs = @($ArduinoLibs, (Join-Path $ProjectRoot "libraries")) | Select-Object -Unique

if ($hasEiLib) {
    Write-Host "[4/5] Kiem tra bien dich currency_detector + collect_images..."
    foreach ($lib in $libDirs) {
        if (Test-Path $lib) {
            arduino-cli compile --config-file $Cfg --fqbn $fqbn --libraries $lib (Join-Path $ProjectRoot "firmware\currency_detector")
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            arduino-cli compile --config-file $Cfg --fqbn $fqbn --libraries $lib (Join-Path $ProjectRoot "firmware\collect_images")
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            break
        }
    }
} else {
    Write-Host "[4/5] Bo qua bien dich currency_detector / collect_images (thieu Edge Impulse)"
}

Write-Host "[5/5] Kiem tra bien dich gay_nguoi_mu_main + esp32_periph..."
$compileOk = $true
if ($hasEiLib) {
    foreach ($lib in $libDirs) {
        if (Test-Path $lib) {
            arduino-cli compile --config-file $Cfg --fqbn $fqbn --libraries $lib (Join-Path $ProjectRoot "firmware\gay_nguoi_mu_main")
            if ($LASTEXITCODE -ne 0) { $compileOk = $false }
            break
        }
    }
} else {
    Write-Host "  Bo qua gay_nguoi_mu_main (can gay_nguoi_mu_vnd_inferencing)" -ForegroundColor Yellow
}
arduino-cli compile --config-file $Cfg --fqbn $fqbnEsp (Join-Path $ProjectRoot "firmware\esp32_periph")
if ($LASTEXITCODE -ne 0) { $compileOk = $false }

Write-Host ""
if ($compileOk -and $hasEiLib) {
    Write-Host "XONG! Tat ca sketch bien dich thanh cong." -ForegroundColor Green
} elseif (-not $hasEiLib) {
    Write-Host "XONG (mot phan): Thu vien TTS da cai. Can them Edge Impulse de bien dich sketch AI." -ForegroundColor Yellow
} else {
    Write-Host "XONG (co loi bien dich) - xem log phia tren." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Mo Arduino IDE, chon board ESP32S3 Dev Module:" -ForegroundColor Cyan
Write-Host "  PSRAM: OPI PSRAM | Flash: 16MB | Partition: Huge APP"
Write-Host "  Sketch 1: firmware\gay_nguoi_mu_main\gay_nguoi_mu_main.ino (ESP32-S3)"
Write-Host "  Sketch 2: firmware\esp32_periph\esp32_periph.ino (ESP32 thuong)"
Write-Host "  Sketch 3: firmware\currency_detector\currency_detector.ino (test tien)"
Write-Host "  Sketch 4: firmware\collect_images\collect_images.ino"
Write-Host ""
Write-Host "TTS: dung ESP32-audioI2S (schreibfaul1) - KHONG dung ESP8266Audio 2.x" -ForegroundColor Yellow
Write-Host "Neu Arduino IDE van bao thieu library: dong IDE, mo lai sau khi chay script nay." -ForegroundColor Yellow

if (-not $hasEiLib) { exit 0 }
