#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
術語表功能測試腳本
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_terminology_manager():
    """測試術語表管理器"""
    print("\n=== Testing Terminology Manager ===")
    
    try:
        from terminology_manager import TerminologyManager
        
        tm = TerminologyManager("test_terminology.db")
        
        # 測試添加術語
        print("Adding custom terms...")
        tm.add_term("定制術語1", "Custom Term 1", "general", "custom", 9)
        tm.add_term("定制術語2", "Custom Term 2", "electronics", "custom", 8)
        
        # 測試獲取術語
        print("\nGetting electronics terms:")
        terms = tm.get_terms("electronics", limit=5)
        for t in terms[:5]:
            print(f"  {t.source} -> {t.target} (priority: {t.priority})")
        
        # 測試搜索
        print("\nSearching for 'bluetooth':")
        results = tm.search_terms("蓝牙", "electronics")
        for r in results[:3]:
            print(f"  {r.source} -> {r.target}")
        
        # 測試預處理
        print("\nTesting preprocessing:")
        text = "藍牙耳機和充電器"
        processed, marker_map = tm.preprocess_text(text, "electronics")
        print(f"  Original: {text}")
        print(f"  Processed: {processed}")
        print(f"  Markers: {marker_map}")
        
        # 測試後處理
        print("\nTesting postprocessing:")
        translated = "Bluetooth Earphones and Charger"
        restored = tm.postprocess_text(processed, marker_map, "electronics")
        print(f"  Translated (simulated): {translated}")
        print(f"  Restored: {restored}")
        
        # 測試統計
        print("\nStatistics:")
        stats = tm.get_stats()
        print(f"  Total: {stats['total_terms']}")
        print(f"  System: {stats['system_terms']}")
        print(f"  User: {stats['user_terms']}")
        
        print("\n✅ Terminology Manager tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Terminology Manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_terminology_integration():
    """測試術語表與翻譯服務集成"""
    print("\n=== Testing Terminology Integration ===")
    
    try:
        from enhanced_translation_service import EnhancedTranslationService
        
        # 創建服務實例
        service = EnhancedTranslationService(
            domain="electronics",
            use_tm=False,  # 禁用TM以專注測試術語
            use_terminology=True
        )
        
        # 測試預處理
        print("Testing preprocessing:")
        text = "這款藍牙耳機支持快速充電"
        processed, marker_map = service.preprocess_with_terminology(text)
        print(f"  Original: {text}")
        print(f"  Processed: {processed}")
        print(f"  Protected terms: {len(marker_map)}")
        
        # 測試一致性檢查
        print("\nTesting consistency check:")
        source = "藍牙耳機和充電器"
        target = "Bluetooth Headphones and Power Adapter"  # 故意不一致
        issues = service.check_terminology_consistency(source, target)
        if issues:
            print(f"  Found {len(issues)} inconsistencies:")
            for issue in issues:
                print(f"    - {issue['source']}: expected '{issue['expected_target']}'")
        else:
            print("  No inconsistencies found")
        
        # 測試統計
        print("\nService stats:")
        stats = service.get_stats_report()
        print(f"  Use terminology: {stats.get('use_terminology')}")
        print(f"  Terminology hits: {stats.get('terminology_hits', 0)}")
        
        print("\n✅ Terminology Integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Terminology Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_csv_import_export():
    """測試 CSV 導入導出"""
    print("\n=== Testing CSV Import/Export ===")
    
    try:
        from terminology_manager import TerminologyManager
        from io import StringIO
        
        tm = TerminologyManager("test_terminology_csv.db")
        
        # 測試導入
        print("Testing CSV import:")
        csv_content = """source,target,category,priority
定制詞A,Custom A,custom,9
定制詞B,Custom B,custom,8
定制詞C,Custom C,technical,7"""
        
        success, failed = tm.import_from_csv(csv_content, "test_domain")
        print(f"  Imported: {success}, Failed: {failed}")
        
        # 測試導出
        print("\nTesting CSV export:")
        exported = tm.export_to_csv("test_domain")
        print(f"  Exported CSV length: {len(exported)} chars")
        print(f"  First few lines:")
        for line in exported.split('\n')[:4]:
            print(f"    {line}")
        
        print("\n✅ CSV Import/Export tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ CSV Import/Export test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """運行所有測試"""
    print("=" * 60)
    print("術語表功能測試")
    print("=" * 60)
    
    results = []
    
    # 測試術語表管理器
    results.append(("Terminology Manager", test_terminology_manager()))
    
    # 測試術語表集成
    results.append(("Terminology Integration", test_terminology_integration()))
    
    # 測試 CSV 導入導出
    results.append(("CSV Import/Export", test_csv_import_export()))
    
    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:40s} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All terminology tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
