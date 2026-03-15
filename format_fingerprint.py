#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式指紋與自學習引擎
GeBuDiu USP: "越翻譯，格式越精準"

核心概念：
- ContentFingerprint: 內容特徵指紋（決定格式的關鍵）
- FormatOutcome: 格式產出結果
- 無監督學習：自動從佈局差異中學習，無需用戶反饋
"""

import os
import sqlite3
import json
import logging
import hashlib
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class ContentFingerprint:
    """內容指紋 - 決定格式的關鍵特徵"""
    domain: str                      # 領域
    total_chars: int                 # 總字符數
    avg_sentence_length: float       # 平均句長
    paragraph_count: int             # 段落數
    table_count: int                 # 表格數
    image_count: int                 # 圖片數
    structure_complexity: float      # 結構複雜度 (0-1)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ContentFingerprint':
        return cls(**data)
    
    def get_similarity_key(self) -> str:
        """生成相似性比對鍵（用於查找類似內容）"""
        # 量化特徵以便比對
        char_bucket = self.total_chars // 500 * 500  # 每500字一檔
        sent_bucket = int(self.avg_sentence_length // 10) * 10  # 每10字一檔
        return f"{self.domain}_{char_bucket}_{sent_bucket}_{self.table_count}"

@dataclass
class FormatParams:
    """格式參數配置"""
    font_size: float = 11.0          # 字體大小 (pt)
    line_spacing: float = 1.15       # 行距倍數
    paragraph_spacing: float = 6.0   # 段前段後間距 (pt)
    margin_cm: float = 2.5           # 頁邊距 (cm)
    
    def to_dict(self) -> Dict:
        return asdict(self)

@dataclass
class FormatOutcome:
    """格式產出結果 - 可從 DOCX 分析得出"""
    page_count: int                  # 頁數
    text_expansion_ratio: float      # 文本膨脹率 (譯文/原文)
    paragraph_growth_rate: float     # 段落增長率
    whitespace_ratio: float          # 留白佔比
    line_break_density: float        # 斷行密度
    
    def calculate_satisfaction_score(self) -> float:
        """
        計算客觀滿意度 (0-1，越高越好)
        完全自動，無需用戶反饋
        """
        score = 1.0
        
        # 文本膨脹過高扣分 (中文譯英文通常 1.2-1.4)
        if self.text_expansion_ratio > 1.5:
            score -= 0.25
        elif self.text_expansion_ratio > 1.4:
            score -= 0.15
        
        # 頁數激增扣分
        if self.text_expansion_ratio > 1.3:
            score -= 0.1
        
        # 段落異常增長扣分 (可能表示分段過細)
        if self.paragraph_growth_rate > 0.3:
            score -= 0.1
        
        # 留白過多扣分 (浪費空間)
        if self.whitespace_ratio > 0.35:
            score -= 0.15
        
        # 斷行過多扣分
        if self.line_break_density > 0.12:
            score -= 0.1
        
        return max(0.0, min(1.0, score))

@dataclass
class FormatDiffReport:
    """格式差異報告"""
    text_expansion_ratio: float
    paragraph_diff: int
    font_size_diff: float
    page_increase: int
    severity: str  # minor, moderate, major
    satisfaction_score: float
    suggestions: List[str]
    auto_fix_params: FormatParams

class FormatLearningEngine:
    """格式自學習引擎 - GBD 核心 USP"""
    
    def __init__(self, db_path: str = None):
        # 優先從環境變量獲取路徑，默認使用 /data
        if db_path is None:
            db_path = os.getenv("FORMAT_LEARNING_DB_PATH", "/data/format_learning.db")
        
        self.db_path = db_path
        
        # 確保目錄存在
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except Exception as e:
                logger.warning(f"Failed to create db directory {db_dir}: {e}")
                # 回退到當前目錄
                self.db_path = "format_learning.db"
        
        self._init_db()
        logger.info(f"FormatLearningEngine initialized: {self.db_path}")
    
    def _init_db(self):
        """初始化數據庫"""
        try:
            db_dir = os.path.dirname(self.db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create directory: {e}, using current directory")
            self.db_path = "format_learning.db"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 格式指紋記錄表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS format_fingerprints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint_key TEXT NOT NULL,
                domain TEXT,
                total_chars INTEGER,
                avg_sentence_length REAL,
                paragraph_count INTEGER,
                table_count INTEGER,
                image_count INTEGER,
                structure_complexity REAL,
                font_size REAL,
                line_spacing REAL,
                paragraph_spacing REAL,
                margin_cm REAL,
                outcome_score REAL,
                page_count INTEGER,
                text_expansion_ratio REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                usage_count INTEGER DEFAULT 1
            )
        """)
        
        # 創建索引加速查詢
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fingerprint_key 
            ON format_fingerprints(fingerprint_key)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain_score 
            ON format_fingerprints(domain, outcome_score DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def record_translation_outcome(self,
                                   fingerprint: ContentFingerprint,
                                   params_used: FormatParams,
                                   outcome: FormatOutcome):
        """
        記錄翻譯結果到學習數據庫
        這是「越翻譯越聰明」的核心
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fingerprint_key = fingerprint.get_similarity_key()
            satisfaction = outcome.calculate_satisfaction_score()
            
            # 檢查是否已存在相似記錄
            cursor.execute("""
                SELECT id, usage_count FROM format_fingerprints
                WHERE fingerprint_key = ? 
                  AND ABS(font_size - ?) < 0.5
                  AND ABS(line_spacing - ?) < 0.1
                LIMIT 1
            """, (fingerprint_key, params_used.font_size, params_used.line_spacing))
            
            existing = cursor.fetchone()
            
            if existing:
                # 更新現有記錄（累積學習）
                cursor.execute("""
                    UPDATE format_fingerprints
                    SET outcome_score = (outcome_score * usage_count + ?) / (usage_count + 1),
                        usage_count = usage_count + 1,
                        text_expansion_ratio = (text_expansion_ratio * usage_count + ?) / (usage_count + 1),
                        created_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (satisfaction, outcome.text_expansion_ratio, existing[0]))
            else:
                # 插入新記錄
                cursor.execute("""
                    INSERT INTO format_fingerprints
                    (fingerprint_key, domain, total_chars, avg_sentence_length,
                     paragraph_count, table_count, image_count, structure_complexity,
                     font_size, line_spacing, paragraph_spacing, margin_cm,
                     outcome_score, page_count, text_expansion_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    fingerprint_key, fingerprint.domain, fingerprint.total_chars,
                    fingerprint.avg_sentence_length, fingerprint.paragraph_count,
                    fingerprint.table_count, fingerprint.image_count,
                    fingerprint.structure_complexity, params_used.font_size,
                    params_used.line_spacing, params_used.paragraph_spacing,
                    params_used.margin_cm, satisfaction, outcome.page_count,
                    outcome.text_expansion_ratio
                ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Format learning recorded: key={fingerprint_key}, score={satisfaction:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to record format learning: {e}")
    
    def predict_optimal_params(self, fingerprint: ContentFingerprint) -> FormatParams:
        """
        預測最佳格式參數
        基於歷史相似內容的最佳表現
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            fingerprint_key = fingerprint.get_similarity_key()
            
            # 策略1: 精確匹配相同指紋
            cursor.execute("""
                SELECT font_size, line_spacing, paragraph_spacing, margin_cm,
                       AVG(outcome_score) as avg_score, COUNT(*) as cnt
                FROM format_fingerprints
                WHERE fingerprint_key = ?
                GROUP BY font_size, line_spacing
                ORDER BY avg_score DESC, cnt DESC
                LIMIT 1
            """, (fingerprint_key,))
            
            result = cursor.fetchone()
            
            # 策略2: 如果沒有精確匹配，找同領域的最佳表現
            if not result or result[4] < 0.6:  # 分數太低
                cursor.execute("""
                    SELECT font_size, line_spacing, paragraph_spacing, margin_cm,
                           AVG(outcome_score) as avg_score
                    FROM format_fingerprints
                    WHERE domain = ?
                      AND total_chars BETWEEN ? AND ?
                    GROUP BY font_size, line_spacing
                    ORDER BY avg_score DESC
                    LIMIT 1
                """, (fingerprint.domain, 
                       int(fingerprint.total_chars * 0.7),
                       int(fingerprint.total_chars * 1.3)))
                
                result = cursor.fetchone()
            
            conn.close()
            
            if result and result[4] > 0.5:  # 有可信的歷史數據
                logger.info(f"Predicted params from learning: font={result[0]}, spacing={result[1]}, score={result[4]:.2f}")
                return FormatParams(
                    font_size=result[0],
                    line_spacing=result[1],
                    paragraph_spacing=result[2] if result[2] else 6.0,
                    margin_cm=result[3] if result[3] else 2.5
                )
            
            # 默認值（無歷史數據時）
            return self._get_default_params(fingerprint)
            
        except Exception as e:
            logger.error(f"Failed to predict params: {e}")
            return self._get_default_params(fingerprint)
    
    def _get_default_params(self, fingerprint: ContentFingerprint) -> FormatParams:
        """根據內容特徵生成默認參數"""
        params = FormatParams()
        
        # 長文本 -> 稍小字體
        if fingerprint.total_chars > 5000:
            params.font_size = 10.5
            params.line_spacing = 1.1
        
        # 多表格 -> 緊湊格式
        if fingerprint.table_count > 5:
            params.font_size = 10.0
            params.paragraph_spacing = 3.0
        
        # 醫療/法律文件 -> 標準格式
        if fingerprint.domain in ['medical', 'legal']:
            params.font_size = 11.0
            params.line_spacing = 1.2
        
        return params
    
    def get_learning_stats(self) -> Dict:
        """獲取學習統計（供前端展示）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*), AVG(outcome_score) FROM format_fingerprints")
            total, avg_score = cursor.fetchone()
            
            cursor.execute("SELECT SUM(usage_count) FROM format_fingerprints")
            total_usage = cursor.fetchone()[0] or 0
            
            cursor.execute("""
                SELECT domain, COUNT(*) as cnt, AVG(outcome_score) as score
                FROM format_fingerprints
                GROUP BY domain
                ORDER BY cnt DESC
            """)
            by_domain = [
                {"domain": row[0], "count": row[1], "avg_score": round(row[2], 2)}
                for row in cursor.fetchall()
            ]
            
            conn.close()
            
            return {
                "total_patterns": total,
                "average_satisfaction": round(avg_score, 2) if avg_score else 0,
                "total_optimizations": total_usage,
                "domain_breakdown": by_domain,
                "status": "active" if total > 0 else "learning"
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {"status": "error", "message": str(e)}

# 全局引擎實例
_format_learning_engine = None

def get_format_learning_engine(db_path: str = "/data/format_learning.db") -> FormatLearningEngine:
    """獲取格式學習引擎單例"""
    global _format_learning_engine
    if _format_learning_engine is None:
        _format_learning_engine = FormatLearningEngine(db_path)
    return _format_learning_engine
