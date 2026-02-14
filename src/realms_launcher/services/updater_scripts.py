from __future__ import annotations

# flake8: noqa


def write_updater_ps1(ps1_path: str) -> None:
    """
    PowerShell updater with detailed logging:
      - Waits for main process (PID) to exit
      - Copies staged -> target via robocopy with retries
      - Logs every step to LogPath
      - Cleans up staged dir
      - Relaunches the launcher with proper working directory
    """
    ps1 = r'''
param(
    [string]$TargetDir,
    [string]$StagedDir,
    [string]$MainPid,
    [string]$RelaunchPath,
    [string]$RelaunchArgs,
    [string]$RelaunchCwd,
    [string]$LogPath
)

# Ensure parent folder exists (esp. if redirected elsewhere)
try {
    $parent = Split-Path -Parent $LogPath
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
} catch {}

# --- Logging helper ---
function Write-Log {
    param([string]$msg)
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss.fff")
    try {
        Add-Content -LiteralPath $LogPath -Value "[$timestamp] $msg"
    } catch {}
}

# Wait for a file to be unlocked (no sharing) for up to TimeoutMs
function Wait-Unlocked {
    param([string]$Path, [int]$TimeoutMs = 15000)
    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        while ($true) {
            try {
                $fs = [System.IO.File]::Open($Path, 'Open', 'ReadWrite', 'None')
                $fs.Close()
                return $true
            } catch {
                if ($sw.ElapsedMilliseconds -gt $TimeoutMs) { return $false }
                Start-Sleep -Milliseconds 200
            }
        }
    } catch { return $false }
}

# Ensure log file exists
try {
    New-Item -ItemType File -Force -Path $LogPath | Out-Null
} catch {}

try { Start-Transcript -Path $LogPath -Append | Out-Null } catch {}

Write-Log "==== Updater started ===="
Write-Log "TargetDir=$TargetDir"
Write-Log "StagedDir=$StagedDir"
Write-Log "MainPid=$MainPid"
Write-Log "RelaunchPath=$RelaunchPath"
Write-Log "RelaunchArgs=$RelaunchArgs"
Write-Log "RelaunchCwd=$RelaunchCwd"
Write-Log "PSVersion=$($PSVersionTable.PSVersion)"

# Wait for main process to exit (best effort)
try { $pidInt = [int]$MainPid } catch { $pidInt = 0 }
if ($pidInt -gt 0) {
    try {
        Write-Log "Waiting for PID $pidInt to exit..."
        Wait-Process -Id $pidInt -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
    } catch {
        Write-Log "Wait-Process threw: $($_.Exception.Message)"
    }
}

# Copy loop (robust against transient locks)
function Copy-With-Retry {
    param([string]$src, [string]$dst)
    $max = 10
    for ($i=1; $i -le $max; $i++) {
        try {
            if (Test-Path -LiteralPath $src) {
                if (-not (Test-Path -LiteralPath $dst)) {
                    try { New-Item -ItemType Directory -Force -Path $dst | Out-Null } catch {}
                }
                # Ensure target exe is unlocked before attempting a mirror
                if ($RelaunchPath) {
                    Write-Log "Waiting for target EXE to unlock: $RelaunchPath"
                    $unlocked = Wait-Unlocked -Path $RelaunchPath -TimeoutMs (2000 + 300 * $i)
                    Write-Log "Unlock wait result = $unlocked"
                }
                Write-Log "robocopy try #$i"
                # /E copies all subdirs (incl. empty); NOT /MIR which would
                # purge files in the target that are absent from the source —
                # catastrophic when the launcher lives inside the game folder.
                robocopy "$src" "$dst" /E /R:2 /W:0 /NFL /NDL /NJH /NJS /NP
                $code = $LASTEXITCODE
                Write-Log "robocopy exit code = $code"
                # robocopy: codes 0-7 are success-ish
                if ($code -le 7) { return $true }
            } else {
                Write-Log "Source staged dir missing: $src"
                return $false
            }
        } catch {
            Write-Log "Copy exception: $($_.Exception.Message)"
        }
        Start-Sleep -Milliseconds (500 * $i)
    }
    return $false
}

$ok = Copy-With-Retry -src $StagedDir -dst $TargetDir

if (-not $ok) {
    Write-Log "robocopy failed; attempting fallback copy"
    try {
        Copy-Item -Path (Join-Path $StagedDir '*') -Destination $TargetDir -Recurse -Force -ErrorAction Stop
        $ok = $true
        Write-Log "Fallback copy succeeded"
    } catch {
        Write-Log "Fallback copy failed: $($_.Exception.Message)"
    }
}

# Cleanup staged
try {
    if (Test-Path -LiteralPath $StagedDir) {
        Remove-Item -LiteralPath $StagedDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Log "Staged dir cleaned"
    }
} catch {
    Write-Log "Cleanup exception: $($_.Exception.Message)"
}

# Relaunch
if ($ok -and $RelaunchPath) {
    try {
        Write-Log "Relaunching..."
        if ($RelaunchCwd) { Set-Location -LiteralPath $RelaunchCwd }
        if ($RelaunchArgs) {
            # If path isn't a file, attempt to run it as a command line
            Start-Process -FilePath $RelaunchPath -ArgumentList $RelaunchArgs -WorkingDirectory $RelaunchCwd
        } else {
            Start-Process -FilePath $RelaunchPath -WorkingDirectory $RelaunchCwd
        }
    } catch {
        Write-Log "Relaunch exception: $($_.Exception.Message)"
    }
}

Write-Log "==== Updater finished ===="
try { Stop-Transcript | Out-Null } catch {}
'''
    with open(ps1_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write(ps1)


def write_updater_cmd(cmd_path: str) -> None:
    """
    Write a CMD-based updater that doesn't rely on PowerShell script policy.
    """
    lines = [
        "@echo off",
        "setlocal enableextensions enabledelayedexpansion",
        "set TargetDir=%~1",
        "set StagedDir=%~2",
        "set MainPid=%~3",
        "set RelaunchPath=%~4",
        "set RelaunchArgs=%~5",
        "set RelaunchCwd=%~6",
        "set LogPath=%~7",
        "",
        "if \"%LogPath%\"==\"\" set LogPath=%TEMP%\\realms_launcher_update_cmd.log",
        "call :log ==== CMD Updater started ====",
        "call :log TargetDir=%TargetDir%",
        "call :log StagedDir=%StagedDir%",
        "call :log MainPid=%MainPid%",
        "call :log RelaunchPath=%RelaunchPath%",
        "call :log RelaunchArgs=%RelaunchArgs%",
        "call :log RelaunchCwd=%RelaunchCwd%",
        "",
        "REM wait for pid to exit (best effort)",
        "if not \"%MainPid%\"==\"\" (",
        "  for /l %%i in (1,1,30) do (",
        "    tasklist /FI \"PID eq %MainPid%\" | find \"%MainPid%\" >nul",
        "    if errorlevel 1 goto :pid_done",
        "    timeout /t 1 /nobreak >nul",
        "  )",
        ")",
        ":pid_done",
        "",
        "REM robocopy copy from staged to target (NOT /MIR — that would",
        "REM purge unrelated files if the launcher sits inside the game folder)",
        "set tries=0",
        ":copy_try",
        "set /a tries+=1",
        "call :log robocopy try #%tries%",
        "robocopy \"%StagedDir%\" \"%TargetDir%\" /E /R:2 /W:0 /NFL /NDL /NJH /NJS /NP",
        "set rc=%errorlevel%",
        "call :log robocopy exit code=%rc%",
        "if %rc% LEQ 7 goto :copy_ok",
        "if %tries% GEQ 10 goto :copy_fail",
        "timeout /t 1 /nobreak >nul",
        "goto :copy_try",
        "",
        ":copy_ok",
        "call :log Copy succeeded",
        "goto :cleanup",
        "",
        ":copy_fail",
        "call :log Copy failed; attempting fallback xcopy",
        "xcopy \"%StagedDir%\\*\" \"%TargetDir%\\\" /E /I /Y >nul",
        "if errorlevel 1 (",
        "  call :log Fallback xcopy failed",
        "  goto :cleanup",
        ")",
        "call :log Fallback xcopy succeeded",
        "",
        ":cleanup",
        "REM clean staged",
        "if exist \"%StagedDir%\" (",
        "  rmdir /s /q \"%StagedDir%\"",
        "  call :log Staged cleaned",
        ")",
        "",
        "REM relaunch",
        "if exist \"%RelaunchPath%\" (",
        "  call :log Relaunching...",
        "  if not \"%RelaunchCwd%\"==\"\" pushd \"%RelaunchCwd%\"",
        "  start \"\" \"%RelaunchPath%\" %RelaunchArgs%",
        "  if not \"%RelaunchCwd%\"==\"\" popd",
        ") else (",
        "  call :log Relaunch skipped (missing path)",
        ")",
        "call :log ==== CMD Updater finished ====",
        "exit /b 0",
        "",
        ":log",
        ">> \"%LogPath%\" echo [%date% %time%] %*",
        "exit /b 0",
        "",
    ]
    with open(cmd_path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\r\n".join(lines))
