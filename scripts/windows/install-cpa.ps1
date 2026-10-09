#requires -Version 5.1
[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "cliproxyapi"),
    [string]$Version = "latest",
    [int]$Port = 8317,
    [ValidateSet("claude", "codex", "codex-device", "antigravity", "kimi", "xai")]
    [string[]]$Login = @(),
    [switch]$NoAutostart,
    [switch]$NoUserEnv,
    [switch]$Uninstall,
    [switch]$Purge
)

$ErrorActionPreference = "Stop"
$TaskName = "CLIProxyAPI"

function Stop-CpaProcess {
    if ([string]::IsNullOrWhiteSpace([string]$script:Executable)) { return }
    $processes = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq [IO.Path]::GetFullPath($script:Executable)
    }
    foreach ($process in $processes) { Stop-Process -Id $process.ProcessId -Force -ErrorAction SilentlyContinue }
}

function Get-ApiKey([string]$Path) {
    if (-not (Test-Path $Path)) { return "" }
    $inApiKeys = $false
    $apiKeysIndent = -1
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if (-not $inApiKeys) {
            if ($line -match '^(\s*)api-keys:\s*(?:#.*)?$') {
                $apiKeysIndent = $Matches[1].Length
                $inApiKeys = $true
            }
            continue
        }
        if ($line -match '^\s*$') { continue }
        $indent = ([regex]::Match($line, '^\s*')).Value.Length
        if ($indent -le $apiKeysIndent) { break }
        if ($line -match '^\s*-\s*(.*?)\s*(?:#.*)?$') {
            $value = $Matches[1].Trim()
            if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) {
                $value = $value.Substring(1, $value.Length - 2)
            }
            if (-not [string]::IsNullOrWhiteSpace($value)) { return $value }
        }
    }
    return ""
}

function Get-CpaPort([string]$Path, [int]$Fallback) {
    if (-not (Test-Path $Path)) { return $Fallback }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match '^\s*port:\s*(\d+)\s*(?:#.*)?$') { return [int]$Matches[1] }
    }
    return $Fallback
}

function New-ApiKey {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes) -replace "-", "").ToLowerInvariant()
}

function Get-Release([string]$RequestedVersion) {
    $url = if ($RequestedVersion -eq "latest") {
        "https://api.github.com/repos/router-for-me/CLIProxyAPI/releases/latest"
    } else {
        "https://api.github.com/repos/router-for-me/CLIProxyAPI/releases/tags/$RequestedVersion"
    }
    return Invoke-RestMethod -Uri $url -UseBasicParsing -TimeoutSec 30
}

function Get-Asset([object]$Release, [string]$Name) {
    $asset = @($Release.assets) | Where-Object { $_.name -eq $Name } | Select-Object -First 1
    if (-not $asset) { throw "发布版本中缺少资产：$Name" }
    return $asset
}

function Register-CpaTask([string]$Exe, [string]$Config) {
    $argument = "-config " + [char]34 + $Config + [char]34
    $action = New-ScheduledTaskAction -Execute $Exe -Argument $argument
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -Hidden
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
}

function Start-Cpa([string]$Exe, [string]$Config) {
    $script:Executable = $Exe
    $running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ExecutablePath -and [IO.Path]::GetFullPath($_.ExecutablePath) -eq [IO.Path]::GetFullPath($Exe)
    }
    if (-not $running) { Start-Process -FilePath $Exe -ArgumentList @("-config", $Config) -WindowStyle Hidden | Out-Null }
}

function Wait-Cpa([string]$ApiKey) {
    $deadline = (Get-Date).AddSeconds(30)
    do {
        try {
            $requestParams = @{ Uri = "http://127.0.0.1:$Port/v1/models"; Headers = @{ Authorization = "Bearer $ApiKey" }; UseBasicParsing = $true; TimeoutSec = 3 }
            if ($PSVersionTable.PSVersion.Major -ge 7) { $requestParams.NoProxy = $true } else { [Net.WebRequest]::DefaultWebProxy = $null }
            $response = Invoke-WebRequest @requestParams
            if ([int]$response.StatusCode -eq 200) { return }
        } catch {}
        Start-Sleep -Milliseconds 500
    } while ((Get-Date) -lt $deadline)
    throw "CPA 启动后 30 秒内未能通过 /v1/models 检查"
}

try {
    $InstallDir = [IO.Path]::GetFullPath($InstallDir)
    $config = Join-Path $InstallDir "config.yaml"
    $authDir = Join-Path $InstallDir "auth"
    $exe = Join-Path $InstallDir "cliproxyapi.exe"
    $script:Executable = $exe
    $versionFile = Join-Path $InstallDir "version.txt"

    if ($Uninstall) {
        $userConfigKey = Get-ApiKey $config
        $userConfigPort = Get-CpaPort $config $Port
        $userBase = [Environment]::GetEnvironmentVariable("AICJ_EXECUTOR_BASE_URL", "User")
        $userToken = [Environment]::GetEnvironmentVariable("AICJ_EXECUTOR_TOKEN", "User")
        $expectedBase = ("http://127.0.0.1:{0}" -f $userConfigPort).Trim().ToLowerInvariant()
        $normalizedUserBase = ([string]$userBase).Trim().ToLowerInvariant().TrimEnd("/")
        $normalizedUserToken = ([string]$userToken).Trim()
        if (-not [string]::IsNullOrWhiteSpace($userConfigKey) -and $normalizedUserToken -eq $userConfigKey.Trim() -and $normalizedUserBase -eq $expectedBase.TrimEnd("/")) {
            [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_TOKEN", $null, "User")
            [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_BASE_URL", $null, "User")
            Write-Host "已删除与本 CPA 配置匹配的用户级 AICJ_EXECUTOR_TOKEN/AICJ_EXECUTOR_BASE_URL。"
        } else {
            Write-Host "用户级 AICJ_EXECUTOR_TOKEN/AICJ_EXECUTOR_BASE_URL 与本 CPA 配置不同时保留。"
        }
        Stop-CpaProcess
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        if (Test-Path $exe) { Remove-Item -LiteralPath $exe -Force }
        if (Test-Path $versionFile) { Remove-Item -LiteralPath $versionFile -Force }
        if ($Purge) {
            Write-Host "删除配置：$config"
            Write-Host "删除凭证目录：$authDir"
            if (Test-Path $config) { Remove-Item -LiteralPath $config -Force }
            if (Test-Path $authDir) { Remove-Item -LiteralPath $authDir -Recurse -Force }
        }
        Write-Host "CLIProxyAPI 已卸载。"
        exit 0
    }

    if (-not (Test-Path $InstallDir)) { New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null }
    $configExists = Test-Path $config
    $apiKey = Get-ApiKey $config
    if ($configExists -and [string]::IsNullOrWhiteSpace($apiKey)) { throw "已有配置但未找到 api-keys：请在 config.yaml 的 access.api-keys 下添加一项或删除配置重建" }
    if (-not $configExists) { $apiKey = New-ApiKey }
    if (-not $configExists) {
        @(
            "config-version: 8"
            "server:"
            '  host: "127.0.0.1"'
            "  port: $Port"
            "access:"
            "  api-keys:"
            "    - $apiKey"
            "oauth:"
            "  auth-dir: '" + ($authDir -replace "'", "''") + "'"
        ) -join "`n" | ForEach-Object { [IO.File]::WriteAllText($config, $_ + "`n", (New-Object Text.UTF8Encoding($false))) }
    } else {
        Write-Host "保留已有配置：$config"
    }

    $release = Get-Release $Version
    $releaseVersion = [string]$release.tag_name
    $installedVersion = if (Test-Path $versionFile) { (Get-Content -LiteralPath $versionFile -Raw).Trim() } else { "" }
    if ((Test-Path $exe) -and $installedVersion -eq $releaseVersion) {
        Write-Host "CLIProxyAPI $releaseVersion 已安装，跳过下载。"
    } else {
    $arch = if ($env:PROCESSOR_ARCHITECTURE -match "ARM64") { "aarch64" } else { "amd64" }
    $assetName = "CLIProxyAPI_{0}_windows_{1}.zip" -f ($releaseVersion.TrimStart("v")), $arch
    $asset = Get-Asset $release $assetName
    $checksums = Get-Asset $release "checksums.txt"
    $temp = Join-Path ([IO.Path]::GetTempPath()) ("cliproxyapi-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $temp -Force | Out-Null
    try {
        $zip = Join-Path $temp $assetName
        $sumFile = Join-Path $temp "checksums.txt"
        Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing -TimeoutSec 120
        Invoke-WebRequest -Uri $checksums.browser_download_url -OutFile $sumFile -UseBasicParsing -TimeoutSec 30
        $expected = ""
        foreach ($line in Get-Content -LiteralPath $sumFile -Encoding UTF8) {
            if ($line -match '^([0-9A-Fa-f]{64})\s+\*?(.+)$' -and $Matches[2].Trim() -eq $assetName) { $expected = $Matches[1].ToLowerInvariant() }
        }
        if (-not $expected) { throw "checksums.txt 中找不到 $assetName" }
        $actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actual -ne $expected) { throw "SHA256 校验失败：$assetName" }
        Expand-Archive -LiteralPath $zip -DestinationPath $temp -Force
        $found = @(Get-ChildItem -LiteralPath $temp -Filter "*.exe" -File -Recurse | Where-Object { $_.FullName -ne $exe })
        if ($found.Count -ne 1) { throw "zip 中未能唯一定位主程序 .exe" }
        $newExe = $found[0].FullName
        $oldExe = $exe + ".old"
        if (Test-Path $exe) {
            Stop-CpaProcess
            if (Test-Path $oldExe) { Remove-Item -LiteralPath $oldExe -Force }
            Move-Item -LiteralPath $exe -Destination $oldExe -Force
        }
        try {
            Copy-Item -LiteralPath $newExe -Destination $exe -Force
            if (Test-Path $oldExe) { Remove-Item -LiteralPath $oldExe -Force }
        } catch {
            if (Test-Path $oldExe) { Move-Item -LiteralPath $oldExe -Destination $exe -Force }
            throw
        }
    } finally {
        if (Test-Path $temp) { Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue }
    }
    Set-Content -LiteralPath $versionFile -Value $releaseVersion -Encoding UTF8
    }

    if (-not $NoAutostart) { Register-CpaTask $exe $config }
    Start-Cpa $exe $config
    Wait-Cpa $apiKey

    if ($Login.Count -gt 0) {
        foreach ($name in $Login) {
            & $exe -config $config "-$name-login"
            if ($LASTEXITCODE -ne 0) { throw "$name 登录失败，退出码 $LASTEXITCODE" }
        }
    } else {
        Write-Host "可用登录命令：$exe -config $config -claude-login / -codex-login / -codex-device-login / -antigravity-login / -kimi-login / -xai-login"
    }

    $baseUrl = "http://127.0.0.1:$Port"
    $existingBase = [Environment]::GetEnvironmentVariable("AICJ_EXECUTOR_BASE_URL", "User")
    $existingToken = [Environment]::GetEnvironmentVariable("AICJ_EXECUTOR_TOKEN", "User")
    if ($NoUserEnv) {
        [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_BASE_URL", $baseUrl, "Process")
        [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_TOKEN", $apiKey, "Process")
        $env:AICJ_EXECUTOR_BASE_URL = $baseUrl
        $env:AICJ_EXECUTOR_TOKEN = $apiKey
    } else {
        if ([string]::IsNullOrWhiteSpace($existingBase)) {
            [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_BASE_URL", $baseUrl, "User")
            $env:AICJ_EXECUTOR_BASE_URL = $baseUrl
        } else {
            Write-Host "AICJ_EXECUTOR_BASE_URL 已存在，保留现值：$existingBase"
            $env:AICJ_EXECUTOR_BASE_URL = $existingBase
        }
        if ([string]::IsNullOrWhiteSpace($existingToken)) {
            [Environment]::SetEnvironmentVariable("AICJ_EXECUTOR_TOKEN", $apiKey, "User")
            $env:AICJ_EXECUTOR_TOKEN = $apiKey
        } else {
            Write-Host "AICJ_EXECUTOR_TOKEN 已存在，保留现值。请用 install.ps1 -CpaToken 显式指定。"
            $env:AICJ_EXECUTOR_TOKEN = $existingToken
        }
    }
    Write-Host "配置：$config"
    Write-Host "凭证目录：$authDir"
    Write-Host "管理：Unregister-ScheduledTask -TaskName $TaskName；$exe -config $config"
    exit 0
} catch {
    Write-Error ("CLIProxyAPI 安装失败：" + $_.Exception.Message)
    exit 1
}
