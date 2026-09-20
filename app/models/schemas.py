from pydantic import BaseModel, HttpUrl, validator
from typing import Optional

class CodeReviewRequest(BaseModel):
    """代码审查请求 - Day 2 增强版"""
    code: Optional[str] = None  # 代码文本（可选）
    github_url: Optional[HttpUrl] = None  # GitHub 链接（可选）
    language: str = "python"  # 编程语言，默认 python
    
    @validator('code')
    def validate_code_length(cls, v):
        """验证代码长度，防止过大文本"""
        if v and len(v) > 10 * 1024 * 1024:  # 10MB 限制
            raise ValueError('Code size exceeds 10MB limit')
        return v
    
    @validator('github_url', always=True)
    def validate_at_least_one_source(cls, v, values):
        """至少提供 code 或 github_url 之一"""
        if not v and not values.get('code'):
            raise ValueError('Either code or github_url must be provided')
        return v

class CodeReviewResponse(BaseModel):
    """代码审查响应（提交任务）"""
    task_id: str
    status: str = "PENDING"
    message: str = "Task submitted successfully"
    source_type: str  # "code" 或 "github"

class TaskResult(BaseModel):
    """任务结果"""
    task_id: str
    status: str  # PENDING, SUCCESS, FAILED
    result: Optional[dict] = None
    error: Optional[str] = None