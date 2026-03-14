#!/usr/bin/env python3
"""
Namecheap 域名快速檢查 - 只檢查精選推薦
"""

import requests
import xml.etree.ElementTree as ET

# 配置
API_USER = "twmeric"
API_KEY = "6d910f8ac94e4520b00100c544fa7d15"
CLIENT_IP = "221.124.9.100"

# 精選域名 - 只檢查最佳推薦
PRIORITY_DOMAINS = [
    # 首選推薦 (io 後綴)
    ("formagic", "io"),
    ("typelock", "io"),
    ("stayformed", "io"),
    ("gridlock", "io"),
    ("gebudiu", "io"),
    
    # 備選 (co 後綴 - 更便宜)
    ("formagic", "co"),
    ("typelock", "co"),
    ("stayformed", "co"),
    
    # 特色後綴
    ("formagic", "so"),
    ("gebudiu", "so"),
]

def check_domain(domain, tld):
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
        root = ET.fromstring(response.text)
        
        # 檢查錯誤
        errors = root.find('.//{http://api.namecheap.com/xml.response}Errors')
        if errors is not None and len(errors) > 0:
            error = errors[0]
            return None, error.text
        
        # 查找結果
        result = root.find('.//{http://api.namecheap.com/xml.response}DomainCheckResult')
        if result is not None:
            available = result.get('Available', 'false').lower() == 'true'
            premium = result.get('IsPremiumName', 'false').lower() == 'true'
            price = result.get('PremiumRegistrationPrice', '')
            return {
                'domain': f"{domain}.{tld}",
                'available': available,
                'premium': premium,
                'price': price
            }, None
            
        return None, "No result"
        
    except Exception as e:
        return None, str(e)

def main():
    print("=" * 60)
    print("[GeBuDiu] Priority Domain Check")
    print("=" * 60)
    print(f"\nChecking {len(PRIORITY_DOMAINS)} priority domains...\n")
    
    available = []
    taken = []
    errors = []
    
    for i, (domain, tld) in enumerate(PRIORITY_DOMAINS, 1):
        print(f"[{i}/{len(PRIORITY_DOMAINS)}] Checking {domain}.{tld}... ", end="", flush=True)
        
        result, error = check_domain(domain, tld)
        
        if error:
            print(f"[ERROR: {error}]")
            errors.append((domain, tld, error))
        elif result['available']:
            price_info = f" [PREMIUM: ${result['price']}]" if result['premium'] else ""
            print(f"[AVAILABLE]{price_info}")
            available.append(result)
        else:
            print("[TAKEN]")
            taken.append(result['domain'])
    
    # 總結
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    
    if available:
        print(f"\n[AVAILABLE - {len(available)} domains]:")
        for d in available:
            price = f" (${d['price']} premium)" if d['premium'] else " (~$12-35/year)"
            print(f"  - {d['domain']}{price}")
    
    if taken:
        print(f"\n[TAKEN - {len(taken)} domains]:")
        for d in taken:
            print(f"  - {d}")
    
    if errors:
        print(f"\n[ERRORS - {len(errors)} domains]:")
        for domain, tld, err in errors:
            print(f"  - {domain}.{tld}: {err}")
    
    # 最佳推薦
    print("\n" + "=" * 60)
    print("TOP RECOMMENDATIONS")
    print("=" * 60)
    
    top_choices = [
        "formagic.io",
        "typelock.io", 
        "stayformed.io",
        "gebudiu.io",
        "formagic.co"
    ]
    
    for choice in top_choices:
        if any(d['domain'] == choice for d in available):
            print(f"  [STAR] {choice}")
            break
    
    print("\n[Next Steps]:")
    print("1. Go to https://www.namecheap.com/")
    print("2. Search your preferred domain")
    print("3. Add IP 221.124.9.100 to Namecheap API whitelist")
    print("   (Profile -> Tools -> API Access -> Manage)")

if __name__ == "__main__":
    main()
