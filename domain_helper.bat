@echo off
chcp 65001 >nul
title GeBuDiu Domain Helper
color 0B
cls

echo ================================================
echo    GEBUDIU (格不丢) - Domain Registration Helper
echo ================================================
echo.
echo  A tool to help you choose and register domains
echo.

:: Get IP
echo [1] Detecting your network...
for /f "tokens=*" %%a in ('powershell -Command "(Invoke-WebRequest -Uri 'https://api.ipify.org' -UseBasicParsing).Content"') do set MY_IP=%%a

echo     Your IP: %MY_IP%
echo.

:: Show menu
:MENU
cls
echo ================================================
echo    GEBUDIU DOMAIN HELPER
echo ================================================
echo.
echo  Your IP: %MY_IP% (Whitelist this in Namecheap)
echo.
echo  [1] Open Namecheap API Settings (Whitelist IP)
echo  [2] Search "typelock.io" (RECOMMENDED)
echo  [3] Search "stayformed.io" (Alternative)
echo  [4] Search "gebudiu.io" (Chinese style)
echo  [5] Check all .co options (Budget)
echo  [6] View price comparison
echo  [7] Exit
echo.
echo ================================================
echo.

choice /C 1234567 /N /M "Select option (1-7): "

if %errorlevel%==1 goto NAMECHEAP_API
if %errorlevel%==2 goto TYPELOCK
if %errorlevel%==3 goto STAYFORMED
if %errorlevel%==4 goto GEBUDIU
if %errorlevel%==5 goto BUDGET
if %errorlevel%==6 goto PRICES
if %errorlevel%==7 goto EXIT

:NAMECHEAP_API
echo.
echo Opening Namecheap API settings...
echo [Action Required] Add IP %MY_IP% to whitelist
timeout /t 2 >nul
start https://ap.www.namecheap.com/settings/tools/apiaccess/
echo.
echo [TIP] After adding IP, wait 2 minutes before using API
echo.
pause
goto MENU

:TYPELOCK
echo.
echo [RECOMMENDED] Opening typelock.io search...
echo [Brand] Type + Lock = Professional, clean, SaaS vibe
echo [Price] ~$35/year for .io domain
timeout /t 1 >nul
start https://www.namecheap.com/domains/registration/results/?domain=typelock.io
goto MENU

:STAYFORMED
echo.
echo [Alternative] Opening stayformed.io search...
echo [Brand] Stay + Formed = Attitude, professional, B2B
echo [Price] ~$35/year for .io domain
timeout /t 1 >nul
start https://www.namecheap.com/domains/registration/results/?domain=stayformed.io
goto MENU

:GEBUDIU
echo.
echo [Unique] Opening gebudiu.io search...
echo [Brand] Keep Chinese identity, like "TikTok"
echo [Price] ~$35/year for .io domain
timeout /t 1 >nul
start https://www.namecheap.com/domains/registration/results/?domain=gebudiu.io
goto MENU

:BUDGET
echo.
echo [Budget Options] Opening .co domain search...
echo.
echo Checking typelock.co...
start https://www.namecheap.com/domains/registration/results/?domain=typelock.co
timeout /t 2 >nul
echo Checking stayformed.co...
start https://www.namecheap.com/domains/registration/results/?domain=stayformed.co
goto MENU

:PRICES
cls
echo ================================================
echo    DOMAIN PRICE COMPARISON (Namecheap)
echo ================================================
echo.
echo  [TOP RECOMMENDATIONS]
echo.
echo  typelock.io        ~$35/year    [BEST]
echo  stayformed.io      ~$35/year    [Good]
echo  gebudiu.io         ~$35/year    [Unique]
echo.
echo  [BUDGET OPTIONS]
echo.
echo  typelock.co        ~$12/year    [Cheap]
echo  stayformed.co      ~$12/year    [Cheap]
echo.
echo  [TOTAL COST if buying both .io + .co]
echo  typelock.io + typelock.co = ~$47/year
echo  (Protect your brand from copycats)
echo.
echo ================================================
echo.
pause
goto MENU

:EXIT
echo.
echo Good luck with your domain!
echo Remember: "typelock.io" is the best choice ;)
echo.
pause
exit
