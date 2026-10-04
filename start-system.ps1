param([string]$Python = 'C:\ProgramData\anaconda3\python.exe')
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root '干部动态调整系统后端'
$frontend = Join-Path $root '干部动态调整系统前端\vue-project'
$localEnv = Join-Path $root '.env'
if (Test-Path -LiteralPath $localEnv) {
    $qwenLine = Get-Content -LiteralPath $localEnv | Where-Object { $_ -match '^QWEN_KEY=' } | Select-Object -Last 1
    if ($qwenLine) { $env:DASHSCOPE_API_KEY = $qwenLine.Substring('QWEN_KEY='.Length).Trim() }
}
$logs = Join-Path $root 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
if (!(Test-Path -LiteralPath $Python)) { throw "Python not found: $Python" }
$node = (Get-Command node.exe -ErrorAction Stop).Source
docker info --format '{{.ServerVersion}}' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop first.' }

# Windows reserves port 5432 on this machine. Reuse the existing data on 15432.
$originalJson = docker inspect cadre-postgres
if ($LASTEXITCODE -ne 0) { throw 'Existing cadre-postgres container not found.' }
$original = ($originalJson | ConvertFrom-Json)[0]
$dbPort = 5432
if (!$original.State.Running) {
    $dbPort = 15432
    $name = 'cadre-postgres-local'
    $existing = @(docker ps -a --format '{{.Names}}')
    if ($existing -notcontains $name) {
        $mount = @($original.Mounts | Where-Object Destination -eq '/var/lib/postgresql/data')[0]
        if (!$mount -or $mount.Type -ne 'volume') { throw 'Expected existing PostgreSQL data volume.' }
        docker create --name $name --publish '127.0.0.1:15432:5432' --mount "type=volume,source=$($mount.Name),target=/var/lib/postgresql/data" $original.Image | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Could not create local PostgreSQL container.' }
    }
    docker start $name | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not start local PostgreSQL container.' }
} else {
    $name = 'cadre-postgres'
    $localRunning = @(docker ps --format '{{.Names}}') -contains 'cadre-postgres-local'
    if ($localRunning) { throw 'Both database containers are running. Stop one before continuing.' }
}
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker exec $name pg_isready -U postgres -d cadre_management_db 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (!$ready) { throw 'PostgreSQL did not become ready.' }

function Start-App($port, $exe, $arguments, $directory, $label) {
    $pidFile = Join-Path $logs "$label.pid"
    $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        if ((Test-Path $pidFile) -and ($listener.OwningProcess -contains [int](Get-Content $pidFile))) {
            Write-Host "$label already running on $port"
            return
        }
        throw "Port $port is occupied by another process."
    }
    $process = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory $directory -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logs "$label.out.log") -RedirectStandardError (Join-Path $logs "$label.err.log") -PassThru
    Set-Content -Path $pidFile -Value $process.Id
    Write-Host "$label PID: $($process.Id)"
}
$env:OPENHRM_DB_PORT = "$dbPort"
Start-App 8000 $Python ('"' + (Join-Path $root 'scripts\run-local.py') + '"') $backend 'backend'
Start-App 5173 $node 'node_modules/vite/bin/vite.js' $frontend 'frontend'
foreach ($url in @('http://127.0.0.1:8000/swagger/', 'http://127.0.0.1:5173/')) {
    $available = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $response = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) { $available = $true; break }
        } catch { Start-Sleep -Seconds 1 }
    }
    if (!$available) { throw "Service unavailable: $url. Check $logs" }
}
Write-Host 'System ready: http://localhost:5173'
Write-Host "Database port: $dbPort. Logs: $logs"
