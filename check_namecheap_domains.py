#!/usr/bin/env python3
"""
Namecheap 域名可用性檢查工具
用於批量檢查品牌域名
"""

import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
import time

# ===== 配置你的 Namecheap API 憑證 =====
API_USER = "twmeric"
API_KEY = "6d910f8ac94e4520b00100c544fa7d15"
CLIENT_IP = "221.124.9.100"  # 需要在 Namecheap 後台白名單

# 推薦的域名列表
SUGGESTED_DOMAINS = [
    # 主要推薦
    "formagic",
    "stayformed", 
    "gridlock",
    "typelock",
    "gebudiu",
    
    # 變體
    "formagik",
    "stayformat",
    "formatlock",
    "typelockr",
    "doculock",
    "layoutlock",
    "formlock",
    "cellock",
    
    # 組合
    "formatguard",
    "docguard",
    "layoutkeep",
    "formkeep",
    "formatkeeper",
]

TLDS = ["com", "io", "co", "so", "app", "net", "tech", "ai"]

def check_domain_availability(domain, tld):
    """檢查單個域名可用性"""
    
    endpoint = "https://api.namecheap.com/xml.response"
    
    params = {
        "ApiUser": API_USER,
        "ApiKey": API_KEY,
        "UserName": API_USER,
        "ClientIp": CLIENT_IP,
        "Command": "namecheap.domains.check",
        "DomainList": f"{domain}.{tld}",
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        
        # 解析 XML
        root = ET.fromstring(response.text)
        
        # 檢查是否有錯誤
        if root.find('.//{http://api.namecheap.com/xml.response}Errors'):
            error = root.find('.//{http://api.namecheap.com/xml.response}Errors/{http://api.namecheap.com/xml.response}Error')
            return None, error.text if error is not None else "API Error"
        
        # 查找可用性結果
        domain_check_result = root.find('.//{http://api.namecheap.com/xml.response}DomainCheckResult')
        
        if domain_check_result is not None:
            available = domain_check_result.get('Available', 'false').lower() == 'true'
            premium = domain_check_result.get('IsPremiumName', 'false').lower() == 'true'
            price = domain_check_result.get('PremiumRegistrationPrice', 'N/A')
            
            return {
                'domain': f"{domain}.{tld}",
                'available': available,
                'premium': premium,
                'price': price if premium else 'Standard'
            }, None
            
        return None, "No result found"
        
    except Exception as e:
        return None, str(e)

def batch_check():
    """批量檢查所有推薦域名"""
    
    print("=" * 60)
    print("[GeBuDiu] Domain Availability Check")
    print("=" * 60)
    print(f"\n檢查 {len(SUGGESTED_DOMAINS)} 個域名 x {len(TLDS)} 個後綴...")
    print("-" * 60)
    
    available_domains = []
    taken_domains = []
    
    for domain in SUGGESTED_DOMAINS:
        for tld in TLDS:
            result, error = check_domain_availability(domain, tld)
            
            if error:
                print(f"[ERROR] {domain}.{tld}: {error}")
                continue
            
            if result['available']:
                status = "[OK] Available"
                if result['premium'] != 'Standard':
                    status += f" (Premium ${result['price']})"
                available_domains.append(result)
            else:
                status = "[TAKEN]"
                taken_domains.append(result['domain'])
            
            print(f"{status:<25} {result['domain']:<25}")
            
            # Namecheap API 有限速，每個請求間隔 1 秒
            time.sleep(1)
    
    # 輸出總結
    print("\n" + "=" * 60)
    print("📊 檢查結果總結")
    print("=" * 60)
    
    print(f"\n[AVAILABLE] ({len(available_domains)} domains):")
    for d in available_domains:
        price_info = f" [Premium: {d['price']}]" if d['premium'] else ""
        print(f"   • {d['domain']}{price_info}")
    
    print(f"\n[TAKEN] ({len(taken_domains)} domains):")
    for d in taken_domains[:10]:  # 只顯示前 10 個
        print(f"   • {d}")
    if len(taken_domains) > 10:
        print(f"   ... 還有 {len(taken_domains) - 10} 個")
    
    # 推薦最佳選擇
    print("\n" + "=" * 60)
    print("[RECOMMENDED] (Based on availability & branding)")
    print("=" * 60)
    
    priority_tlds = ['io', 'co', 'so', 'com']
    for domain in ['formagic', 'stayformed', 'typelock', 'gebudiu', 'gridlock']:
        for tld in priority_tlds:
            full = f"{domain}.{tld}"
            if any(d['domain'] == full for d in available_domains):
                print(f"   [STAR] {full}")
                break

if __name__ == "__main__":
    # 檢查配置
    if API_USER == "你的_namecheap_用戶名" or API_KEY == "你的_api_key":
        print("[WARNING] Please fill in your Namecheap API credentials!")
        print("\nSteps to get API credentials:")
        print("1. Login Namecheap → Account → Profile")
        print("2. Find Tools → API Access → Enable")
        print("3. Copy ApiKey and ApiUser")
        print("4. Add your IP to whitelist")
        print("5. Fill in this script")
    else:
        batch_check()
