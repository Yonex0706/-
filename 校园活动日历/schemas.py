"""
Pydantic 模型定义
用于API请求参数验证和响应数据序列化
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class CategoryOut(BaseModel):
    """分类输出模型"""
    id: int
    name: str
    icon: str
    color: str

    class Config:
        from_attributes = True


class ActivityCreate(BaseModel):
    """活动创建请求模型"""
    title: str
    description: str = ""
    category_id: int
    location: str = ""
    start_time: datetime
    end_time: datetime
    publisher: str = ""
    status: str = "正常"


class ActivityUpdate(BaseModel):
    """活动更新请求模型"""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    publisher: Optional[str] = None
    status: Optional[str] = None


class ActivityOut(BaseModel):
    """活动输出模型（含分类信息）"""
    id: int
    title: str
    description: str
    category_id: int
    location: str
    start_time: datetime
    end_time: datetime
    publisher: str
    status: str
    created_at: datetime
    category: Optional[CategoryOut] = None

    class Config:
        from_attributes = True


class PaginatedActivities(BaseModel):
    """分页活动列表"""
    items: List[ActivityOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class ApiResponse(BaseModel):
    """统一API响应格式"""
    code: int = 200
    msg: str = "success"
    data: Optional[object] = None
