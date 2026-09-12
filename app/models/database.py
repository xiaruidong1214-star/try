import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path("data/reviews.db")
DB_PATH.parent.mkdir(exist_ok=True)


def init_db():
    """初始化数据库表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            code TEXT NOT NULL,
            language TEXT NOT NULL,
            complexity TEXT,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized")


def save_review(task_id: str, code: str, language: str, result: Dict[str, Any]) -> bool:
    """保存分析记录"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO review_history 
            (task_id, code, language, complexity, result_json)
            VALUES (?, ?, ?, ?, ?)
        """, (
            task_id,
            code,
            language,
            result.get("complexity", "UNKNOWN"),
            json.dumps(result, ensure_ascii=False)
        ))
        conn.commit()
        conn.close()
        logger.info(f"Review saved: {task_id}")
        return True
    except Exception as e:
        logger.error(f"Save review failed: {e}")
        return False


def get_history(limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
    """获取历史记录列表"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, task_id, code, language, complexity, created_at
            FROM review_history
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            "id": row["id"],
            "task_id": row["task_id"],
            "code_preview": row["code"][:100] + ("..." if len(row["code"]) > 100 else ""),
            "language": row["language"],
            "complexity": row["complexity"],
            "created_at": row["created_at"]
        } for row in rows]
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        return []


def get_review_detail(task_id: str) -> Optional[Dict[str, Any]]:
    """获取单条记录详情"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM review_history WHERE task_id = ?
        """, (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "task_id": row["task_id"],
            "code": row["code"],
            "language": row["language"],
            "complexity": row["complexity"],
            "result": json.loads(row["result_json"]),
            "created_at": row["created_at"]
        }
    except Exception as e:
        logger.error(f"Get detail failed: {e}")
        return None


def get_stats() -> Dict[str, Any]:
    """获取统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM review_history")
        total = cursor.fetchone()[0]
        conn.close()
        return {"total_reviews": total}
    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        return {"total_reviews": 0}