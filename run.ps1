param(
    [switch]$E2ETest,
    [string]$E2EWebDir
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$apiDir = Join-Path $root 'apps\api'
$webDir = Join-Path $root 'apps\web'
$apiPort = if ($E2ETest) { 8100 } else { 8000 }
$webPort = if ($E2ETest) { 3100 } else { 3000 }

function Get-AvailableLoopbackPort([int]$preferredPort) {
    for ($candidate = $preferredPort; $candidate -lt ($preferredPort + 100); $candidate++) {
        $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $candidate)
        try {
            $listener.Start()
            return $candidate
        } catch {
        } finally {
            $listener.Stop()
        }
    }
    throw "No available local port found near $preferredPort."
}

if (-not $E2ETest) {
    $apiPort = Get-AvailableLoopbackPort 8000
    $webPort = Get-AvailableLoopbackPort 3000
    if ($apiPort -ne 8000) { Write-Host "Port 8000 is unavailable; using API port $apiPort." -ForegroundColor Yellow }
    if ($webPort -ne 3000) { Write-Host "Port 3000 is unavailable; using web port $webPort." -ForegroundColor Yellow }
}
$venvPython = Join-Path $apiDir '.venv\Scripts\python.exe'
$nodeExe = (Get-Command node.exe -ErrorAction Stop).Source
$nodeVersion = & $nodeExe --version
if ($nodeVersion -match '^v(\d+)\.' -and [int]$Matches[1] -lt 22) {
    Write-Warning "Node.js $nodeVersion is end-of-life. Install a supported LTS release (Node.js 24 is recommended) for maintained security updates."
}
$runDir = Join-Path $root '.run'
$logDir = Join-Path $runDir 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$e2eStopFile = $null
if ($E2ETest -and $env:E2E_STOP_FILE) {
    $runRoot = [System.IO.Path]::GetFullPath($runDir).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    $resolvedStopFile = [System.IO.Path]::GetFullPath($env:E2E_STOP_FILE)
    if (-not $resolvedStopFile.StartsWith($runRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'The isolated E2E stop signal must be inside .run.'
    }
    $e2eStopFile = $resolvedStopFile
    Remove-Item -LiteralPath $e2eStopFile -Force -ErrorAction SilentlyContinue
}

if ($E2ETest -and $E2EWebDir) {
    $runRoot = [System.IO.Path]::GetFullPath($runDir).TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    $resolvedE2EWebDir = [System.IO.Path]::GetFullPath($E2EWebDir)
    if (-not $resolvedE2EWebDir.StartsWith($runRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'The isolated E2E web directory must be inside .run.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $resolvedE2EWebDir 'package-lock.json'))) {
        throw 'The isolated E2E web directory is missing package-lock.json.'
    }
    $webDir = $resolvedE2EWebDir
}

function Get-FileSha256([string]$path) {
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($path)
    try {
        return ([BitConverter]::ToString($sha256.ComputeHash($stream))).Replace('-', '')
    } finally {
        $stream.Dispose()
        $sha256.Dispose()
    }
}

# Keep the runnable frontend and its installed dependencies out of apps/web/node_modules.
# npm ci replaces node_modules, which fails on Windows if another Node process has loaded
# the native Next/SWC module from that directory. A lockfile-specific runtime lets the
# source checkout remain editable while each dependency set gets its own safe install.
$sourceWebDir = $webDir
$hasIsolatedE2EWebDir = $E2ETest -and [bool]$E2EWebDir
if (-not $hasIsolatedE2EWebDir) {
    $sourcePackageHash = Get-FileSha256 (Join-Path $sourceWebDir 'package-lock.json')
    $runtimePrefix = if ($E2ETest) { 'web-e2e-' } else { 'web-runtime-' }
    $webDir = Join-Path $runDir ($runtimePrefix + $sourcePackageHash.ToLowerInvariant())
    New-Item -ItemType Directory -Force -Path $webDir | Out-Null

    $copyArguments = @(
        $sourceWebDir, $webDir, '/E', '/XJ', '/XD',
        (Join-Path $sourceWebDir 'node_modules'),
        (Join-Path $sourceWebDir '.next'),
        '/XF', 'tsconfig.tsbuildinfo',
        '/NFL', '/NDL', '/NJH', '/NJS', '/NC', '/NS', '/NP'
    )
    & robocopy.exe @copyArguments | Out-Null
    if ($LASTEXITCODE -ge 8) { throw 'Could not prepare the isolated web runtime.' }

    # Robocopy's /E does not remove files renamed or removed from the source.
    # Retire removed frontend files from this lockfile-specific runtime cache.
    foreach ($retiredRelativePath in @(
        'src\middleware.ts',
        'src\components\credits-context.tsx',
        'src\app\credits.css'
    )) {
        $sourceRetiredFile = Join-Path $sourceWebDir $retiredRelativePath
        $runtimeRetiredFile = Join-Path $webDir $retiredRelativePath
        if (-not (Test-Path -LiteralPath $sourceRetiredFile) -and (Test-Path -LiteralPath $runtimeRetiredFile)) {
            Remove-Item -LiteralPath $runtimeRetiredFile -Force
        }
    }
}

$savedEnvironment = @{}
foreach ($name in @('APP_ENV', 'DATABASE_URL', 'STORAGE_DIR', 'AI_DETECTOR_PROVIDER', 'ADMIN_EMAILS', 'ADMIN_LOGIN_SLUG', 'SESSION_COOKIE_SECURE', 'RATE_LIMIT_AUTH_LIMIT', 'RATE_LIMIT_UPLOAD_LIMIT', 'MAX_ACCOUNTS_PER_IP', 'E2E_ADMIN_PASSWORD', 'NEXT_API_ORIGIN', 'APP_ORIGINS')) {
    $savedEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

$processes = @()
try {
    $envFile = Join-Path $root '.env'
    if (-not (Test-Path -LiteralPath $envFile)) {
        $environmentTemplate = Get-Content -Raw -LiteralPath (Join-Path $root '.env.example')
        $randomBytes = New-Object byte[] 48
        $randomSource = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $randomSource.GetBytes($randomBytes) } finally { $randomSource.Dispose() }
        $generatedSecret = [Convert]::ToBase64String($randomBytes)
        $environmentTemplate = $environmentTemplate -replace '(?m)^APP_SECRET_KEY=.*$', "APP_SECRET_KEY=$generatedSecret"
        Set-Content -LiteralPath $envFile -Value $environmentTemplate -NoNewline
        Write-Host 'Created .env with a fresh random secret. Set ADMIN_EMAILS there before using the administrator console.'
    }

    $envContent = Get-Content -Raw -LiteralPath $envFile
    $slugMatch = [regex]::Match($envContent, '(?m)^ADMIN_LOGIN_SLUG=(.*)$')
    $adminSlug = if ($slugMatch.Success) { $slugMatch.Groups[1].Value.Trim() } else { '' }
    if ($adminSlug -notmatch '^[A-Za-z0-9_-]{32,128}$') {
        $slugBytes = New-Object byte[] 32
        $slugRandom = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try { $slugRandom.GetBytes($slugBytes) } finally { $slugRandom.Dispose() }
        $adminSlug = [Convert]::ToBase64String($slugBytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
        if ($slugMatch.Success) {
            $slugLine = [regex]::new('(?m)^ADMIN_LOGIN_SLUG=.*$')
            $envContent = $slugLine.Replace($envContent, "ADMIN_LOGIN_SLUG=$adminSlug", 1)
        } else {
            $envContent = $envContent.TrimEnd("`r", "`n") + "`r`nADMIN_LOGIN_SLUG=$adminSlug`r`n"
        }
        [System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.UTF8Encoding]::new($false))
        Write-Host 'Generated and saved a private administrator entry slug in .env.'
    }
    $env:ADMIN_LOGIN_SLUG = $adminSlug

    if ($E2ETest) {
        $e2eRunId = if ($env:E2E_RUN_ID -match '^[a-zA-Z0-9_-]{1,48}$') { $env:E2E_RUN_ID } else { [guid]::NewGuid().ToString('N') }
        $env:APP_ENV = 'e2e'
        $env:DATABASE_URL = "sqlite:///./data/e2e-$e2eRunId.db"
        $env:STORAGE_DIR = "./e2e-storage-$e2eRunId"
        $env:AI_DETECTOR_PROVIDER = 'test'
        $env:ADMIN_EMAILS = 'admin@cgs-example.com'
        $env:SESSION_COOKIE_SECURE = 'false'
        $env:RATE_LIMIT_AUTH_LIMIT = '1000'
        $env:RATE_LIMIT_UPLOAD_LIMIT = '1000'
        $env:MAX_ACCOUNTS_PER_IP = '1000'
        $env:SMTP_HOST = ''
        $env:SMTP_FROM_EMAIL = ''
        $env:PUBLIC_APP_ORIGIN = "http://127.0.0.1:$webPort"
        $env:NEXT_API_ORIGIN = "http://127.0.0.1:$apiPort"
        $env:APP_ORIGINS = "http://127.0.0.1:$webPort,http://localhost:$webPort"
    } else {
        $env:PUBLIC_APP_ORIGIN = "http://127.0.0.1:$webPort"
        $env:NEXT_API_ORIGIN = "http://127.0.0.1:$apiPort"
        $env:APP_ORIGINS = "http://127.0.0.1:$webPort,http://localhost:$webPort"
    }

    if (-not (Test-Path -LiteralPath $venvPython)) {
        $basePython = (Get-Command python.exe -ErrorAction Stop).Source
        Write-Host 'Creating the local Python environment…'
        & $basePython -m venv (Join-Path $apiDir '.venv')
        if ($LASTEXITCODE -ne 0) { throw 'Python environment setup failed.' }
    }

    $requirementsHash = Get-FileSha256 (Join-Path $apiDir 'requirements.txt')
    $requirementsStamp = Join-Path $apiDir '.venv\.requirements-hash'
    $installedHash = if (Test-Path -LiteralPath $requirementsStamp) { (Get-Content -Raw -LiteralPath $requirementsStamp).Trim() } else { '' }
    if ($installedHash -ne $requirementsHash) {
        Write-Host 'Installing or updating API dependencies…'
        & $venvPython -m pip install -r (Join-Path $apiDir 'requirements.txt')
        if ($LASTEXITCODE -ne 0) { throw 'API dependency installation failed.' }
        Set-Content -NoNewline -LiteralPath $requirementsStamp -Value $requirementsHash
    }

    $packageHash = Get-FileSha256 (Join-Path $webDir 'package-lock.json')
    $webModules = Join-Path $webDir 'node_modules'
    $packageStamp = Join-Path $webModules '.cgs-shield-deps-hash'
    $installedPackageHash = if (Test-Path -LiteralPath $packageStamp) { (Get-Content -Raw -LiteralPath $packageStamp).Trim() } else { '' }
    if (-not (Test-Path -LiteralPath $webModules) -or $installedPackageHash -ne $packageHash) {
        Write-Host 'Installing or updating web dependencies…'
        Push-Location $webDir
        try {
            npm.cmd ci --cache (Join-Path $runDir 'npm-cache')
            if ($LASTEXITCODE -ne 0) { throw 'Web dependency installation failed.' }
        } finally { Pop-Location }
        Set-Content -NoNewline -LiteralPath $packageStamp -Value $packageHash
    }

    $configuredProvider = $env:AI_DETECTOR_PROVIDER
    if (-not $configuredProvider) {
        $providerSetting = Select-String -LiteralPath $envFile -Pattern '^AI_DETECTOR_PROVIDER=' | Select-Object -First 1
        if ($providerSetting) { $configuredProvider = $providerSetting.Line.Substring('AI_DETECTOR_PROVIDER='.Length).Trim() }
    }
    if (-not $E2ETest -and $configuredProvider -ne 'disabled') {
        Push-Location $apiDir
        try {
            & $venvPython -m app.download_model
            if ($LASTEXITCODE -ne 0) { Write-Warning 'The real model could not be fetched. The app will still start and will clearly mark synthetic screening unavailable.' }
        } finally { Pop-Location }
    }

    Write-Host 'Applying database migrations…'
    Push-Location $apiDir
    try {
        & $venvPython -m app.migrate
        if ($LASTEXITCODE -ne 0) { throw 'Database migrations failed.' }
        if ($E2ETest) {
            $env:E2E_ADMIN_PASSWORD = 'correct horse battery staple'
            & $venvPython -m app.bootstrap_admin admin@cgs-example.com --name 'E2E Administrator'
            if ($LASTEXITCODE -ne 0) { throw 'E2E administrator setup failed.' }
            Remove-Item Env:E2E_ADMIN_PASSWORD -ErrorAction SilentlyContinue
        }
    } finally { Pop-Location }

    $apiProc = Start-Process -FilePath $venvPython -ArgumentList @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', [string]$apiPort) -WorkingDirectory $apiDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'api.log') -RedirectStandardError (Join-Path $logDir 'api-error.log')
    $processes += $apiProc
    $workerProc = Start-Process -FilePath $venvPython -ArgumentList @('-m', 'app.worker') -WorkingDirectory $apiDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'worker.log') -RedirectStandardError (Join-Path $logDir 'worker-error.log')
    $processes += $workerProc

    $apiReady = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $apiProc.Refresh()
        if ($apiProc.HasExited -or $workerProc.HasExited) { throw 'The API or analysis worker stopped during startup. Check .run\logs.' }
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:$apiPort/health/ready" -TimeoutSec 2 -UseBasicParsing
            $apiReady = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $apiReady) { throw 'The API did not become ready. Check .run\logs.' }

    Push-Location $webDir
    try {
        $webProc = Start-Process -FilePath $nodeExe -ArgumentList @('node_modules/next/dist/bin/next', 'dev', '--hostname', '127.0.0.1', '--port', [string]$webPort) -WorkingDirectory $webDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logDir 'web.log') -RedirectStandardError (Join-Path $logDir 'web-error.log')
    } finally { Pop-Location }
    $processes += $webProc

    $webReady = $false
    for ($attempt = 0; $attempt -lt 90; $attempt++) {
        $webProc.Refresh()
        if ($webProc.HasExited) { throw 'The web server stopped during startup. Check .run\logs.' }
        try {
            $null = Invoke-WebRequest -Uri "http://127.0.0.1:$webPort" -TimeoutSec 2 -UseBasicParsing
            $webReady = $true
            break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $webReady) { throw 'The web server did not become ready. Check .run\logs.' }

    Write-Host ''
    Write-Host 'CGS DeepFake Shield is running.' -ForegroundColor Cyan
    Write-Host "Web app:       http://127.0.0.1:$webPort"
    Write-Host "Admin sign-in: http://127.0.0.1:$webPort/admin/$adminSlug"
    Write-Host "API docs:      http://127.0.0.1:$apiPort/docs"
    Write-Host 'Logs:          .run\logs'
    if ($E2ETest) { Write-Host 'E2E mode uses an isolated database and a test-only detector fixture.' -ForegroundColor Yellow }
    Write-Host 'Press Ctrl+C to stop all services.'

    while ($true) {
        if ($e2eStopFile -and (Test-Path -LiteralPath $e2eStopFile)) {
            Write-Host 'Stopping isolated E2E services…'
            break
        }
        foreach ($service in $processes) {
            $service.Refresh()
            if ($service.HasExited) { throw "A service exited (PID $($service.Id)); see .run\logs." }
        }
        if ($e2eStopFile) { Start-Sleep -Milliseconds 200 } else { Start-Sleep -Seconds 1 }
    }
} finally {
    foreach ($service in $processes) {
        try {
            $service.Refresh()
            if (-not $service.HasExited) { Stop-Process -Id $service.Id -Force -ErrorAction SilentlyContinue }
        } catch { }
    }
    foreach ($name in $savedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedEnvironment[$name], 'Process')
    }
    if ($e2eStopFile -and (Test-Path -LiteralPath $e2eStopFile)) {
        Remove-Item -LiteralPath $e2eStopFile -Force -ErrorAction SilentlyContinue
    }
}
