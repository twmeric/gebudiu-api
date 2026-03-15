#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部署後 API 測試腳本
驗證 Translation Memory 增強功能
"""

import requests
import json
import sys

API_BASE = "https://gebudiu-api.onrender.com"

def test_health():
    """測試健康檢查"""
    print("\n=== Testing /health ===")
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=30)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Service: {data.get('service')}")
            print(f"Version: {data.get('version')}")
            print(f"Enhanced Mode: {data.get('enhanced_mode')}")
            
            if data.get('enhanced_mode'):
                features = data.get('features', {})
                print(f"Features:")
                for feat, enabled in features.items():
                    print(f"  - {feat}: {'✅' if enabled else '❌'}")
                
                stats = data.get('stats', {})
                print(f"Stats:")
                print(f"  - API calls: {stats.get('api_calls', 0)}")
                print(f"  - TM hits: {stats.get('tm_hits', 0)}")
                print(f"  - Hit rate: {stats.get('hit_rate_percent', 0):.1f}%")
            
            return True
        else:
            print(f"❌ Health check failed: {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_tm_stats():
    """測試 TM 統計"""
    print("\n=== Testing /tm/stats ===")
    try:
        resp = requests.get(f"{API_BASE}/tm/stats", timeout=30)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Total entries: {data.get('total_entries', 0)}")
            print(f"FAISS vectors: {data.get('faiss_vectors', 0)}")
            print(f"Total hits: {data.get('total_hits', 0)}")
            print(f"Hit rate: {data.get('hit_rate', 0):.1f}%")
            return True
        else:
            print(f"Response: {resp.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_domain_detection():
    """測試領域檢測"""
    print("\n=== Testing /detect-domain ===")
    try:
        test_cases = [
            {"filename": "bluetooth_earphones_spec.docx", "expected": "electronics"},
            {"filename": "medical_device_manual.pdf", "expected": "medical"},
            {"filename": "contract_agreement.docx", "expected": "legal"},
        ]
        
        for case in test_cases:
            resp = requests.post(
                f"{API_BASE}/detect-domain",
                json={"filename": case["filename"]},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                detected = data.get('domain')
                confidence = data.get('confidence', 0)
                info = data.get('info', {})
                
                match = "✅" if detected == case["expected"] else "⚠️"
                print(f"{match} {case['filename']}: {info.get('icon', '')} {detected} ({confidence:.2f})")
            else:
                print(f"❌ {case['filename']}: {resp.status_code}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_tm_search():
    """測試 TM 搜索"""
    print("\n=== Testing /tm/search ===")
    try:
        queries = ["藍牙", "產品規格", "充電器"]
        
        for query in queries:
            resp = requests.post(
                f"{API_BASE}/tm/search",
                json={"query": query, "domain": "electronics"},
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results', [])
                print(f"'{query}': {len(results)} results")
                for r in results[:2]:
                    print(f"  - {r.get('source')} -> {r.get('target')} (sim: {r.get('similarity', 0):.3f})")
            else:
                print(f"'{query}': {resp.status_code} - {resp.text}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """運行所有測試"""
    print("=" * 60)
    print("GeBuDiu API 部署測試")
    print(f"API: {API_BASE}")
    print("=" * 60)
    
    results = []
    
    # 測試健康檢查
    results.append(("Health Check", test_health()))
    
    # 測試 TM 統計
    results.append(("TM Stats", test_tm_stats()))
    
    # 測試領域檢測
    results.append(("Domain Detection", test_domain_detection()))
    
    # 測試 TM 搜索
    results.append(("TM Search", test_tm_search()))
    
    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:30s} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Enhanced features are working.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Check the deployment status.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
