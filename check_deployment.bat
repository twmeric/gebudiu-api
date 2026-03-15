@echo off
chcp 65001 >nul
echo ==========================================
echo  GeBuDiu API 部署狀態檢查
echo ==========================================
echo.

echo [1/4] 檢查健康狀態...
curl -s https://gebudiu-api.onrender.com/health | findstr "enhanced_mode" >nul
if %errorlevel% == 0 (
    echo ✅ 服務正常運行 (Enhanced Mode)
) else (
    echo ❌ 服務未響應或為 Legacy Mode
)
echo.

echo [2/4] 檢查 TM 統計...
curl -s https://gebudiu-api.onrender.com/tm/stats | findstr "total_entries" >nul
if %errorlevel% == 0 (
    echo ✅ TM 統計接口正常
) else (
    echo ⚠️ TM 接口未響應
)
echo.

echo [3/4] 檢查領域檢測...
curl -s -X POST https://gebudiu-api.onrender.com/detect-domain -H "Content-Type: application/json" -d "{\"filename\":\"test.docx\"}" | findstr "domain" >nul
if %errorlevel% == 0 (
    echo ✅ 領域檢測接口正常
) else (
    echo ⚠️ 領域檢測接口未響應
)
echo.

echo [4/4] 檢查文檔列表...
echo 部署文檔:
echo   - DEPLOY_STATUS.md
echo   - DEPLOY_ENHANCED.md
echo   - test_deployed_api.py
echo.

echo ==========================================
echo  檢查完成！
echo  詳細信息請查看 DEPLOY_STATUS.md
echo ==========================================
pause
