@echo off
chcp 65001 >nul
title GeBuDiu Domain Checker
color 0A

echo ==========================================
echo   GeBuDiu (格不丢) Domain Checker
echo ==========================================
echo.

:: 获取当前IP
echo [Step 1] Getting your public IP...
curl -s https://api.ipify.org > temp_ip.txt
set /p CURRENT_IP=<temp_ip.txt
del temp_ip.txt

echo [OK] Your IP: %CURRENT_IP%
echo.

:: 显示Namecheap设置提示
echo ==========================================
echo   Namecheap API Setup Required
echo ==========================================
echo.
echo [IMPORTANT] Add this IP to Namecheap whitelist:
echo   %CURRENT_IP%
echo.
echo [Steps]:
echo   1. Login: https://ap.www.namecheap.com/
echo   2. Go to: Profile ^> Tools ^> API Access
echo   3. Click: Manage ^> Add IP
echo   4. Enter: %CURRENT_IP%
echo   5. Save and wait 2 minutes
echo.
echo [Press any key to open Namecheap...]
pause >nul

:: 打开Namecheap后台
start https://ap.www.namecheap.com/settings/tools/apiaccess/

echo.
echo ==========================================
echo   Recommended Domains to Check
echo ==========================================
echo.
echo [Priority 1 - .io domains]:
echo   - typelock.io     [BEST]
echo   - stayformed.io   [Good]
echo   - gebudiu.io      [Unique]
echo.
echo [Priority 2 - Budget .co domains]:
echo   - typelock.co     [Cheap]
echo   - stayformed.co   [Cheap]
echo.
echo [Press any key to open domain search...]
pause >nul

:: 打开Namecheap域名搜索，自动填入typelock
start https://www.namecheap.com/domains/registration/results/?domain=typelock

echo.
echo ==========================================
echo   Quick Check with Python (Optional)
echo ==========================================
echo.
echo Run Python script to auto-check all domains?
echo [Y] Yes  [N] No
echo.
choice /C YN /N /M "Your choice: "

if %errorlevel%==1 (
    echo.
    echo Running Python checker...
    python check_domains_quick.py
    echo.
)

echo.
echo ==========================================
echo   Done!
echo ==========================================
echo.
echo Recommended: Register "typelock.io"
echo Price: ~$35/year
echo.
pause
