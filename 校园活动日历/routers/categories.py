"""
分类路由模块
处理活动分类相关的API请求
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Category
from schemas import CategoryOut, ApiResponse

router = APIRouter(prefix="/api/categories", tags=["分类管理"])


@router.get("", response_model=ApiResponse)
def get_categories(db: Session = Depends(get_db)):
    """获取所有活动分类列表"""
    categories = db.query(Category).all()
    return ApiResponse(
        code=200,
        msg="success",
        data=[CategoryOut.model_validate(c) for c in categories]
    )
