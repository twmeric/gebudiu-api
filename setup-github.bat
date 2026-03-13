@echo off
echo Setting up GitHub repository for gebudiu-api...
echo.

REM Initialize git
git init

REM Add all files
git add .

REM Commit
git commit -m "Initial commit: gebudiu translation API"

echo.
echo ============================================
echo Next steps:
echo 1. Create a new repository on GitHub
echo    (go to https://github.com/new)
echo 2. Name it: gebudiu-api
echo 3. Make it Public or Private
echo 4. DO NOT initialize with README
echo 5. Copy the repository URL
echo 6. Run the following commands:
echo.
echo    git remote add origin YOUR_REPO_URL
echo    git branch -M main
echo    git push -u origin main
echo ============================================
pause
