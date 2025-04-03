Write-Host "You just executed a file called `"script1.ps1`" " 
1..10 | ForEach-Object {
    Write-Verbose -Message "$_" -Verbose
    sleep 1
}