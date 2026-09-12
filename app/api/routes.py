from fastapi import APIRouter, HTTPException, Request
from app.models.schemas import CodeReviewRequest, CodeReviewResponse
from app.services.review_service import ReviewService
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def root():
    return {"status": "ok", "message": "Code Review Bot is running!"}

@router.post("/review", response_model=CodeReviewResponse)
async def submit_review(request: CodeReviewRequest):
    """
    提交代码审查任务 - Day 2 增强版
    支持:
    1. 直接提交代码文本（code 字段）
    2. 提交 GitHub URL（github_url 字段）
    """
    try:
        # 调用 Service 层处理
        task_id, source_type = ReviewService.submit_task(
            code=request.code,
            github_url=str(request.github_url) if request.github_url else None,
            language=request.language
        )
        
        return CodeReviewResponse(
            task_id=task_id,
            status="PENDING",
            message="Task submitted, use /task/{task_id} to check status",
            source_type=source_type
        )
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """查询任务状态"""
    result = ReviewService.get_task_status(task_id)
    if result.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@router.post("/review/stream")
async def submit_review_stream(request: Request):
    """
    流式接收大文本代码（用于超大文件上传）
    使用 TextIOWrapper 思想，直接从请求体流式读取
    """
    # 获取 Content-Length
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")
    
    # 流式读取请求体
    body = await request.body()
    code = body.decode("utf-8")
    
    # 验证
    if not code:
        raise HTTPException(status_code=400, detail="Empty code content")
    
    # 生成任务
    task_id, source_type = ReviewService.submit_task(
        code=code,
        github_url=None,
        language="python"
    )
    
    return CodeReviewResponse(
        task_id=task_id,
        status="PENDING",
        message="Task submitted via stream",
        source_type="code_stream"
    )

from app.models.database import get_history, get_review_detail, get_stats


@router.get("/history")
async def history(limit: int = 20, offset: int = 0):
    """获取历史记录列表"""
    return {"items": get_history(limit, offset)}


@router.get("/history/{task_id}")
async def history_detail(task_id: str):
    """获取单条记录详情"""
    detail = get_review_detail(task_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Record not found")
    return detail


@router.get("/stats")
async def stats():
    """获取统计信息"""
    return get_stats()