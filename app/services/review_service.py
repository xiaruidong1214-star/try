import uuid
import logging
from typing import Dict, Any, Optional
from app.core.celery_app import celery_app
from app.tasks.review_tasks import analyze_code_task
from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)


class ReviewService:
    
    @staticmethod
    def submit_task(code: Optional[str], github_url: Optional[str], language: str) -> tuple:
        task_id = str(uuid.uuid4())
        source_type = "code" if code else "github"
        code_content = code or "# GitHub 代码获取待实现"
        
        # ★ 1. 先查缓存
        cache_key = cache_service.make_cache_key(code_content, language)
        cached = cache_service.get(cache_key)
        
        if cached:
            # 缓存命中：直接把结果存到 Celery 结果后端，用户查 task_id 就能拿到
            logger.info(f"Cache hit for task {task_id}, skipping Celery")
            from app.core.celery_app import celery_app
            celery_app.backend.store_result(task_id, cached, state="SUCCESS")
            return task_id, source_type
        
        # ★ 2. 缓存未命中：提交 Celery 任务
        analyze_code_task.apply_async(
            args=[code_content, language, cache_key],   # 把 cache_key 传给任务
            task_id=task_id
        )
        
        logger.info(f"Task {task_id} submitted to Celery, source_type={source_type}")
        return task_id, source_type
    
    @staticmethod
    def get_task_status(task_id: str) -> Dict[str, Any]:
        from celery.result import AsyncResult
        
        task_result = AsyncResult(task_id, app=celery_app)
        state = task_result.state
        
        status_map = {
            "PENDING": "PENDING",
            "STARTED": "PROCESSING",
            "PROGRESS": "PROCESSING",
            "SUCCESS": "SUCCESS",
            "FAILURE": "FAILED",
            "RETRY": "RETRYING"
        }
        
        response = {
            "task_id": task_id,
            "status": status_map.get(state, "PENDING")
        }
        
        if state == "SUCCESS":
            response["result"] = task_result.result
        elif state in ["FAILURE", "RETRY"]:
            response["error"] = str(task_result.info)
        elif state in ["STARTED", "PROGRESS"]:
            info = task_result.info or {}
            response["progress"] = info.get("progress", 0)
            response["step"] = info.get("step", "Processing...")
        
        return response