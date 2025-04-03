param (
    [int]$Port = 54321,
    [string]$IPAddress = "0.0.0.0"
)

$webFolder = "$PSScriptRoot\web"

# Diagnostic output
Write-Host "`n=== Server Diagnostics ===" -ForegroundColor Cyan
Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"
Write-Host "Web Folder: $webFolder (Exists: $(Test-Path $webFolder))"
Write-Host "Requested URL: http://$($IPAddress):$($Port)/"
Write-Host "Admin Privileges: $([bool]([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))"
Write-Host "===`n" -ForegroundColor Cyan

try {
    # Check for port availability
    $tcpListener = [System.Net.Sockets.TcpListener]$Port
    $tcpListener.Start()
    $tcpListener.Stop()
}
catch {
    Write-Host "Port $Port is unavailable or access denied. Error: $_" -ForegroundColor Red
    exit 1
}

try {
    $listener = [System.Net.HttpListener]::new()
    $prefix = "http://$($IPAddress):$($Port)/"
    $listener.Prefixes.Add($prefix)
    $listener.Start()

    Write-Host "Server successfully started on $prefix" -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop..." -ForegroundColor Yellow

    while ($true) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        
        try {
            $filePath = Join-Path $webFolder ($request.Url.LocalPath.TrimStart('/') -replace '[\/\\]', [IO.Path]::DirectorySeparatorChar)
            
            if ($filePath -like "*..*") {
                $response.StatusCode = 403
                $response.Close()
                continue
            }

            if (Test-Path $filePath -PathType Leaf) {
                [IO.File]::OpenRead($filePath).CopyTo($response.OutputStream)
            }
            else {
                $response.StatusCode = 404
            }
        }
        finally {
            $response.Close()
        }
    }
}
catch {
    Write-Host "Server Error: $_" -ForegroundColor Red
}
finally {
    if ($null -ne $listener -and $listener.IsListening) {
        $listener.Stop()
        Write-Host "Server stopped." -ForegroundColor Yellow
    }
}