#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wrangler CLI Auto-Test for Cloudflare Workers
類似的自動測試邏輯可以應用於 Wrangler
"""

import subprocess
import json
import re
from datetime import datetime

class WranglerLogMonitor:
    """Wrangler CLI 日誌監控"""
    
    def __init__(self, worker_name: str = "gebudiu-worker"):
        self.worker_name = worker_name
    
    def tail_logs(self, duration: int = 30) -> str:
        """使用 wrangler tail 獲取實時日誌"""
        try:
            # wrangler tail 會持續輸出，我們只捕獲一段時間
            result = subprocess.run(
                ["wrangler", "tail", self.worker_name],
                capture_output=True,
                text=True,
                timeout=duration
            )
            return result.stdout
        except subprocess.TimeoutExpired as e:
            return e.output.decode() if e.output else ""
        except Exception as e:
            return f"Failed to fetch logs: {e}"
    
    def get_deployment_logs(self) -> str:
        """獲取部署日誌"""
        try:
            result = subprocess.run(
                ["wrangler", "deploy", "--dry-run"],
                capture_output=True,
                text=True
            )
            return result.stderr + result.stdout
        except Exception as e:
            return f"Failed: {e}"

class CloudflareAutoDevOps:
    """Cloudflare Workers 自動 DevOps"""
    
    def __init__(self):
        self.error_patterns = {
            "worker_exception": r"Uncaught Exception|worker thread panicked",
            "kv_error": r"KV (get|put|delete) failed",
            "d1_error": r"D1_ERROR|Database error",
            "rate_limit": r"rate limited|429",
            "timeout": r"Timeout|worker exceeded",
        }
    
    def analyze_and_fix(self, logs: str) -> dict:
        """分析日誌並生成修復建議"""
        findings = []
        
        for error_type, pattern in self.error_patterns.items():
            if re.search(pattern, logs, re.IGNORECASE):
                findings.append({
                    "type": error_type,
                    "suggested_fix": self._get_fix_suggestion(error_type)
                })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "findings": findings,
            "should_redeploy": len(findings) > 0
        }
    
    def _get_fix_suggestion(self, error_type: str) -> str:
        fixes = {
            "worker_exception": "Add try-catch blocks and error handling",
            "kv_error": "Check KV namespace binding and permissions",
            "d1_error": "Verify D1 database connection and schema",
            "rate_limit": "Implement exponential backoff",
            "timeout": "Optimize worker code or increase CPU time limit"
        }
        return fixes.get(error_type, "Investigate manually")

# 使用示例
def demo_wrangler_workflow():
    """演示 Wrangler 自動化工作流程"""
    print("🚀 Cloudflare Wrangler Auto-DevOps Demo")
    
    # 1. 獲取日誌
    monitor = WranglerLogMonitor()
    logs = monitor.get_deployment_logs()
    
    # 2. 分析
    devops = CloudflareAutoDevOps()
    report = devops.analyze_and_fix(logs)
    
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    demo_wrangler_workflow()
