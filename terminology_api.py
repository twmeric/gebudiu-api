#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
術語表 API 端點
為 app_enhanced.py 提供術語表相關路由
"""

from flask import Blueprint, request, jsonify, Response
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 創建 Blueprint
terminology_bp = Blueprint('terminology', __name__, url_prefix='/terminology')

def init_terminology_routes(app, terminology_manager):
    """初始化術語表路由"""
    
    @terminology_bp.route('/stats', methods=['GET'])
    def get_stats():
        """獲取術語表統計"""
        try:
            stats = terminology_manager.get_stats()
            return jsonify(stats)
        except Exception as e:
            logger.error(f"Failed to get terminology stats: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/terms', methods=['GET'])
    def get_terms():
        """
        獲取術語列表
        
        Query參數:
        - domain: 領域過濾
        - category: 類別過濾
        - limit: 數量限制 (默認 1000)
        """
        try:
            domain = request.args.get('domain')
            category = request.args.get('category')
            limit = int(request.args.get('limit', 1000))
            
            terms = terminology_manager.get_terms(domain, category, limit)
            
            return jsonify({
                "terms": [
                    {
                        "source": t.source,
                        "target": t.target,
                        "domain": t.domain,
                        "category": t.category,
                        "priority": t.priority,
                        "usage_count": t.usage_count,
                        "created_at": t.created_at
                    }
                    for t in terms
                ],
                "count": len(terms)
            })
            
        except Exception as e:
            logger.error(f"Failed to get terms: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/terms', methods=['POST'])
    def add_term():
        """
        添加術語
        
        Body:
        {
            "source": "原文",
            "target": "譯文",
            "domain": "領域 (可選)",
            "category": "類別 (可選)",
            "priority": 優先級 (可選, 1-10)
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'source' not in data or 'target' not in data:
                return jsonify({"error": "source and target are required"}), 400
            
            source = data['source'].strip()
            target = data['target'].strip()
            domain = data.get('domain', 'general')
            category = data.get('category', 'custom')
            priority = int(data.get('priority', 5))
            
            if not source or not target:
                return jsonify({"error": "source and target cannot be empty"}), 400
            
            success = terminology_manager.add_term(source, target, domain, category, priority)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Term '{source}' added successfully",
                    "term": {
                        "source": source,
                        "target": target,
                        "domain": domain
                    }
                })
            else:
                return jsonify({"error": "Failed to add term"}), 500
                
        except Exception as e:
            logger.error(f"Failed to add term: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/terms/<source>', methods=['DELETE'])
    def delete_term(source: str):
        """
        刪除術語
        
        Query參數:
        - domain: 領域 (默認 general)
        """
        try:
            domain = request.args.get('domain', 'general')
            
            success = terminology_manager.delete_term(source, domain)
            
            if success:
                return jsonify({
                    "success": True,
                    "message": f"Term '{source}' deleted successfully"
                })
            else:
                return jsonify({"error": "Failed to delete term or term not found"}), 404
                
        except Exception as e:
            logger.error(f"Failed to delete term: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/search', methods=['GET'])
    def search_terms():
        """
        搜索術語
        
        Query參數:
        - q: 搜索關鍵詞
        - domain: 領域過濾 (可選)
        """
        try:
            query = request.args.get('q', '').strip()
            domain = request.args.get('domain')
            
            if not query:
                return jsonify({"error": "Query parameter 'q' is required"}), 400
            
            terms = terminology_manager.search_terms(query, domain)
            
            return jsonify({
                "query": query,
                "domain": domain,
                "terms": [
                    {
                        "source": t.source,
                        "target": t.target,
                        "domain": t.domain,
                        "priority": t.priority
                    }
                    for t in terms
                ],
                "count": len(terms)
            })
            
        except Exception as e:
            logger.error(f"Failed to search terms: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/import', methods=['POST'])
    def import_csv():
        """
        從 CSV 導入術語表
        
        FormData:
        - file: CSV 文件
        - domain: 領域 (默認 general)
        
        CSV格式: source,target,category(可選),priority(可選)
        """
        try:
            if 'file' not in request.files:
                return jsonify({"error": "No file provided"}), 400
            
            file = request.files['file']
            domain = request.form.get('domain', 'general')
            
            if not file.filename.endswith('.csv'):
                return jsonify({"error": "Only CSV files are supported"}), 400
            
            # 讀取 CSV 內容
            csv_content = file.read().decode('utf-8')
            
            # 導入
            success, failed = terminology_manager.import_from_csv(csv_content, domain)
            
            return jsonify({
                "success": True,
                "imported": success,
                "failed": failed,
                "domain": domain
            })
            
        except Exception as e:
            logger.error(f"Failed to import CSV: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/export', methods=['GET'])
    def export_csv():
        """
        導出術語表到 CSV
        
        Query參數:
        - domain: 領域過濾 (可選)
        """
        try:
            domain = request.args.get('domain')
            
            csv_content = terminology_manager.export_to_csv(domain)
            
            filename = f"terminology_{domain or 'all'}.csv"
            
            return Response(
                csv_content,
                mimetype='text/csv',
                headers={
                    'Content-Disposition': f'attachment; filename={filename}'
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to export CSV: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/check', methods=['POST'])
    def check_consistency():
        """
        檢查術語一致性
        
        Body:
        {
            "source_text": "原文",
            "target_text": "譯文",
            "domain": "領域 (可選)"
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'source_text' not in data or 'target_text' not in data:
                return jsonify({"error": "source_text and target_text are required"}), 400
            
            source_text = data['source_text']
            target_text = data['target_text']
            domain = data.get('domain')
            
            inconsistencies = terminology_manager.check_consistency(
                source_text, target_text, domain
            )
            
            return jsonify({
                "source_text": source_text[:100] + "..." if len(source_text) > 100 else source_text,
                "target_text": target_text[:100] + "..." if len(target_text) > 100 else target_text,
                "domain": domain,
                "inconsistencies": inconsistencies,
                "is_consistent": len(inconsistencies) == 0
            })
            
        except Exception as e:
            logger.error(f"Failed to check consistency: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/domains', methods=['GET'])
    def get_domains():
        """獲取所有術語領域"""
        try:
            stats = terminology_manager.get_stats()
            domains = list(stats.get('domain_distribution', {}).keys())
            
            return jsonify({
                "domains": domains,
                "count": len(domains)
            })
            
        except Exception as e:
            logger.error(f"Failed to get domains: {e}")
            return jsonify({"error": str(e)}), 500
    
    @terminology_bp.route('/preview', methods=['POST'])
    def preview_preprocessing():
        """
        預覽術語預處理效果
        
        Body:
        {
            "text": "要處理的文本",
            "domain": "領域 (可選)"
        }
        """
        try:
            data = request.get_json()
            
            if not data or 'text' not in data:
                return jsonify({"error": "text is required"}), 400
            
            text = data['text']
            domain = data.get('domain')
            
            # 獲取術語映射
            mapping = terminology_manager.get_preprocessing_map(domain)
            
            # 找出匹配的術語
            matched_terms = []
            for source, marker in mapping.items():
                if source in text:
                    matched_terms.append({
                        "source": source,
                        "marker": marker
                    })
            
            # 預處理
            processed, marker_map = terminology_manager.preprocess_text(text, domain)
            
            return jsonify({
                "original": text,
                "processed": processed,
                "matched_terms": matched_terms,
                "domain": domain
            })
            
        except Exception as e:
            logger.error(f"Failed to preview preprocessing: {e}")
            return jsonify({"error": str(e)}), 500
    
    # 註冊 Blueprint
    app.register_blueprint(terminology_bp)
    logger.info("Terminology API routes registered")
