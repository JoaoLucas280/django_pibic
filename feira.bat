@echo off
chcp 65001 >nul
title Gestao Academica - servidor da feira
cd /d "%~dp0app"

echo.
echo  ============================================================
echo   GESTAO ACADEMICA - abra no computador pelo endereco abaixo
echo   (o celular precisa estar no MESMO Wi-Fi para ler o QR Code)
echo  ============================================================
powershell -NoProfile -Command "Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.AddressState -eq 'Preferred' -and $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } | ForEach-Object { '    http://' + $_.IPAddress + ':8000    (' + $_.InterfaceAlias + ')' }"
echo.
echo  Se o Windows perguntar sobre o Firewall, clique em "Permitir"
echo  (rede privada). Para parar o servidor: Ctrl+C
echo.

python manage.py runserver 0.0.0.0:8000
pause
