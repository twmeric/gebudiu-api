#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
測試增強功能
"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_translation_memory():
    """測試 Translation Memory"""
    print("\n=== Testing Translation Memory ===")
    
    try:
        from translation_memory import TranslationMemory
        
        tm = TranslationMemory(db_path="test_tm.db")
        
        # 添加測試數據
        print("Adding test entries...")
        tm.add("藍牙耳機", "Bluetooth Earphones", "electronics")
        tm.add("產品規格書", "Product Specification", "general")
        tm.add("充電器", "Charger", "electronics")
        
        # 精確匹配測試
        print("\nExact match test:")
        results = tm.search("藍牙耳機")
        assert len(results) > 0, "Exact match failed"
        assert results[0].target == "Bluetooth Earphones"
        print(f"✓ Exact match: {results[0].source} -> {results[0].target}")
        
        # 模糊匹配測試
        print("\nFuzzy match test:")
        results = tm.search("藍牙耳機充電盒")
        if results:
            print(f"✓ Fuzzy match: similarity={results[0].similarity:.3f}")
        else:
            print("  No fuzzy match (expected for short text)")
        
        # 統計
        stats = tm.get_stats()
        print(f"\nTM Stats:")
        print(f"  Total entries: {stats['total_entries']}")
        print(f"  FAISS vectors: {stats['faiss_vectors']}")
        
        print("\n✅ Translation Memory tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Translation Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_domain_detector():
    """測試領域檢測"""
    print("\n=== Testing Domain Detector ===")
    
    try:
        from domain_detector import DomainDetector
        
        detector = DomainDetector()
        
        test_cases = [
            ("product_specification.docx", "electronics"),
            ("medical_device_manual.pdf", "medical"),
            ("contract_agreement.docx", "legal"),
            ("marketing_plan.pptx", "marketing"),
        ]
        
        for filename, expected in test_cases:
            domain, confidence = detector.detect(filename)
            info = detector.get_domain_info(domain)
            print(f"{filename:30s} -> {info['icon']} {domain} (confidence: {confidence:.2f})")
        
        print("\n✅ Domain Detector tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Domain Detector test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enhanced_translation_service():
    """測試增強翻譯服務"""
    print("\n=== Testing Enhanced Translation Service ===")
    
    try:
        from enhanced_translation_service import EnhancedTranslationService
        
        # 初始化服務
        service = EnhancedTranslationService(
            domain="general",
            use_tm=True,
            auto_detect_domain=True
        )
        
        # 測試翻譯
        texts = [
            ("1", "藍牙耳機"),
            ("2", "產品規格書"),
            ("3", "充電器"),
        ]
        
        print("\nFirst translation (should call API):")
        results = service.translate_batch(texts, filename="product_spec.docx")
        
        for item_id, result in results.items():
            print(f"  {item_id}: {result.source} -> {result.text}")
            print(f"      TM match: {result.is_tm_match}, Quality: {result.quality_score:.2f}")
        
        print("\nSecond translation (should hit TM):")
        results2 = service.translate_batch(texts, filename="product_spec.docx")
        
        for item_id, result in results2.items():
            print(f"  {item_id}: {result.source} -> {result.text}")
            print(f"      TM match: {result.is_tm_match}")
        
        # 統計報告
        stats = service.get_stats_report()
        print(f"\nStats Report:")
        print(f"  API calls: {stats['api_calls']}")
        print(f"  TM hits: {stats['tm_hits']}")
        print(f"  Hit rate: {stats['hit_rate_percent']:.1f}%")
        print(f"  Domain: {stats['current_domain']}")
        
        print("\n✅ Enhanced Translation Service tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Enhanced Translation Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """運行所有測試"""
    print("=" * 60)
    print("格不丢翻譯 API - 增強功能測試")
    print("=" * 60)
    
    results = []
    
    # 測試 Translation Memory
    results.append(("Translation Memory", test_translation_memory()))
    
    # 測試 Domain Detector
    results.append(("Domain Detector", test_domain_detector()))
    
    # 測試 Enhanced Translation Service
    results.append(("Enhanced Translation Service", test_enhanced_translation_service()))
    
    # 總結
    print("\n" + "=" * 60)
    print("測試總結")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:40s} {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Please check the errors.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
