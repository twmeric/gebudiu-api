#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MotherBase AI-Driven DevOps Loop
測試總監 → 分析 → 價格設計師 → 修復 → 部署
"""

import subprocess
import re
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple

class RenderLogMonitor:
    """Render CLI 日誌監控器"""
    
    def __init__(self, service_id: str = "srv-d6q9edv5r7bs738d05n0"):
        self.service_id = service_id
        self.error_patterns = {
            "permission_denied": r"Permission denied",
            "file_not_found": r"No such file or directory",
            "import_error": r"ImportError|ModuleNotFoundError",
            "timeout": r"WORKER TIMEOUT",
            "memory_error": r"MemoryError|out of memory",
            "database_locked": r"database is locked",
            "connection_error": r"ConnectionError|Connection refused"
        }
    
    def fetch_logs(self, lines: int = 100) -> str:
        """使用 Render API 獲取日誌"""
        import requests
        
        # Render REST API 端點
        url = f"https://api.render.com/v1/services/{self.service_id}/logs"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._get_api_key()}"
        }
        
        try:
            response = requests.get(url, headers=headers, params={"limit": lines})
            return response.text
        except Exception as e:
            return f"Failed to fetch logs: {e}"
    
    def _get_api_key(self) -> str:
        """獲取 API Key（從環境變量）"""
        import os
        return os.getenv("RENDER_API_KEY", "")
    
    def analyze_errors(self, logs: str) -> List[Dict]:
        """分析日誌中的錯誤"""
        errors = []
        
        for error_type, pattern in self.error_patterns.items():
            matches = re.finditer(pattern, logs, re.IGNORECASE)
            for match in matches:
                # 獲取上下文（前後 100 字符）
                start = max(0, match.start() - 100)
                end = min(len(logs), match.end() + 100)
                context = logs[start:end]
                
                errors.append({
                    "type": error_type,
                    "pattern": pattern,
                    "context": context,
                    "timestamp": datetime.now().isoformat()
                })
        
        return errors

class TestDirector:
    """測試總監 - 分析問題"""
    
    def __init__(self):
        self.knowledge_base = {
            "permission_denied": {
                "severity": "high",
                "common_causes": [
                    "Disk mount not ready",
                    "Wrong user permissions",
                    "Directory doesn't exist"
                ],
                "solutions": [
                    "Use fallback to local directory",
                    "Create directory with proper permissions",
                    "Use Render's ephemeral disk instead"
                ]
            },
            "file_not_found": {
                "severity": "high", 
                "common_causes": [
                    "/data directory not mounted",
                    "Path typo",
                    "Service started before disk ready"
                ],
                "solutions": [
                    "Add retry logic",
                    "Use relative paths",
                    "Check if directory exists before writing"
                ]
            },
            "timeout": {
                "severity": "medium",
                "common_causes": [
                    "File too large",
                    "Inefficient processing",
                    "Insufficient workers"
                ],
                "solutions": [
                    "Increase timeout",
                    "Optimize processing",
                    "Add progress updates"
                ]
            }
        }
    
    def analyze(self, errors: List[Dict]) -> Dict:
        """分析錯誤並生成報告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_errors": len(errors),
            "error_types": {},
            "recommendations": [],
            "priority": "low"
        }
        
        for error in errors:
            error_type = error["type"]
            if error_type not in report["error_types"]:
                report["error_types"][error_type] = {
                    "count": 0,
                    "knowledge": self.knowledge_base.get(error_type, {})
                }
            report["error_types"][error_type]["count"] += 1
            
            # 更新優先級
            kb = self.knowledge_base.get(error_type, {})
            if kb.get("severity") == "high":
                report["priority"] = "high"
        
        # 生成建議
        for error_type in report["error_types"]:
            kb = self.knowledge_base.get(error_type, {})
            if kb.get("solutions"):
                report["recommendations"].extend(kb["solutions"])
        
        return report

class FixEngineer:
    """價格設計師 - 生成修復方案"""
    
    def generate_fix(self, analysis: Dict) -> Dict:
        """基於分析生成修復方案"""
        fixes = []
        
        if "file_not_found" in analysis["error_types"] or \
           "permission_denied" in analysis["error_types"]:
            fixes.append({
                "file": "format_fingerprint.py",
                "action": "update",
                "description": "修復 /data 目錄訪問問題",
                "code_changes": """
# 在 __init__ 方法中添加更健壯的回退機制
def _ensure_writable_path(self, preferred_path: str) -> str:
    '''確保路徑可寫入，否則回退到本地'''
    test_paths = [
        preferred_path,
        "/tmp/" + os.path.basename(preferred_path),
        os.path.expanduser("~/" + os.path.basename(preferred_path)),
        "./" + os.path.basename(preferred_path)
    ]
    
    for path in test_paths:
        try:
            dir_path = os.path.dirname(path) or "."
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            
            # 測試寫入
            test_file = os.path.join(dir_path, ".write_test")
            with open(test_file, 'w') as f:
                f.write("1")
            os.remove(test_file)
            
            return path
        except Exception as e:
            logger.warning(f"Path {path} not writable: {e}")
            continue
    
    # 最終回退
    return os.path.basename(preferred_path)
"""
            })
        
        return {
            "fixes": fixes,
            "deployment_required": len(fixes) > 0,
            "estimated_fix_time": "5-10 minutes"
        }

# 使用示例
def run_devops_loop():
    """運行完整的 DevOps 循環"""
    print("🔄 MotherBase AI DevOps Loop Starting...")
    
    # 1. 監控日誌
    monitor = RenderLogMonitor()
    logs = monitor.fetch_logs(lines=200)
    print(f"📊 Fetched {len(logs)} characters of logs")
    
    # 2. 分析錯誤
    errors = monitor.analyze_errors(logs)
    print(f"⚠️ Found {len(errors)} errors")
    
    if not errors:
        print("✅ No errors found, system healthy!")
        return
    
    # 3. 測試總監分析
    director = TestDirector()
    analysis = director.analyze(errors)
    print(f"📋 Analysis complete: {analysis['priority']} priority")
    
    # 4. 價格設計師生成方案
    engineer = FixEngineer()
    fix_plan = engineer.generate_fix(analysis)
    print(f"🔧 Fix plan generated: {len(fix_plan['fixes'])} fixes")
    
    # 5. 輸出報告
    report = {
        "analysis": analysis,
        "fix_plan": fix_plan,
        "timestamp": datetime.now().isoformat()
    }
    
    print("\n" + "="*50)
    print("📄 DEVOPS REPORT")
    print("="*50)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    return report

if __name__ == "__main__":
    run_devops_loop()
