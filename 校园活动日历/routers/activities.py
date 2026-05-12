"""
活动路由模块
处理活动的增删改查、按月/日查询、倒计时等接口
"""
import math
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import extract, func, and_

from database import get_db
from models import Activity, Category
from schemas import (
    ActivityCreate, ActivityUpdate, ActivityOut,
    PaginatedActivities, ApiResponse
)

router = APIRouter(prefix="/api/activities", tags=["活动管理"])


def activity_to_dict(activity: Activity) -> dict:
    """将Activity对象转换为包含分类信息的字典"""
    return {
        "id": activity.id,
        "title": activity.title,
        "description": activity.description,
        "category_id": activity.category_id,
        "location": activity.location,
        "start_time": activity.start_time.isoformat() if activity.start_time else None,
        "end_time": activity.end_time.isoformat() if activity.end_time else None,
        "publisher": activity.publisher,
        "status": activity.status,
        "created_at": activity.created_at.isoformat() if activity.created_at else None,
        "category": {
            "id": activity.category.id,
            "name": activity.category.name,
            "icon": activity.category.icon,
            "color": activity.category.color,
        } if activity.category else None,
    }


@router.get("", response_model=ApiResponse)
def get_activities(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页条数"),
    category_id: Optional[int] = Query(None, description="分类ID筛选"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    start_date: Optional[str] = Query(None, description="开始日期(YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期(YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="状态筛选"),
    db: Session = Depends(get_db),
):
    """
    分页查询活动列表
    支持按分类、关键词、日期范围、状态筛选
    """
    query = db.query(Activity).options(joinedload(Activity.category))

    # 分类筛选
    if category_id is not None:
        query = query.filter(Activity.category_id == category_id)

    # 关键词搜索（标题和描述）
    if keyword:
        query = query.filter(
            (Activity.title.contains(keyword)) |
            (Activity.description.contains(keyword))
        )

    # 日期范围筛选
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(Activity.start_time >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(Activity.start_time < ed)
        except ValueError:
            pass

    # 状态筛选
    if status:
        query = query.filter(Activity.status == status)

    # 统计总数
    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # 分页查询，按开始时间降序
    activities = (
        query.order_by(Activity.start_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = PaginatedActivities(
        items=[ActivityOut.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    return ApiResponse(code=200, msg="success", data=result.model_dump())


@router.get("/month", response_model=ApiResponse)
def get_activities_by_month(
    year: int = Query(..., description="年份"),
    month: int = Query(..., ge=1, le=12, description="月份"),
    db: Session = Depends(get_db),
):
    """
    按月查询活动，返回日历视图所需数据
    包含每天的活动数量和分类颜色标记
    """
    # 构建月份的起止时间
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1)
    else:
        end = datetime(year, month + 1, 1)

    # 查询该月所有活动（关联分类表）
    activities = (
        db.query(Activity)
        .options(joinedload(Activity.category))
        .filter(and_(Activity.start_time >= start, Activity.start_time < end))
        .order_by(Activity.start_time.asc())
        .all()
    )

    # 按日期分组统计
    day_map = {}
    for a in activities:
        day = a.start_time.day
        if day not in day_map:
            day_map[day] = {"count": 0, "categories": []}
        day_map[day]["count"] += 1
        if a.category and a.category.color not in day_map[day]["categories"]:
            day_map[day]["categories"].append(a.category.color)

    return ApiResponse(
        code=200,
        msg="success",
        data={
            "year": year,
            "month": month,
            "day_summary": day_map,
            "total": len(activities),
        },
    )


@router.get("/date", response_model=ApiResponse)
def get_activities_by_date(
    date: str = Query(..., description="日期(YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    db: Session = Depends(get_db),
):
    """按单日查询活动列表（支持分页）"""
    try:
        target = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return ApiResponse(code=400, msg="日期格式错误，请使用YYYY-MM-DD")

    next_day = target + timedelta(days=1)

    query = (
        db.query(Activity)
        .options(joinedload(Activity.category))
        .filter(and_(Activity.start_time >= target, Activity.start_time < next_day))
    )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    activities = (
        query.order_by(Activity.start_time.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = PaginatedActivities(
        items=[ActivityOut.model_validate(a) for a in activities],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
    return ApiResponse(code=200, msg="success", data=result.model_dump())


@router.post("", response_model=ApiResponse)
def create_activity(activity_in: ActivityCreate, db: Session = Depends(get_db)):
    """新增活动"""
    # 验证分类存在
    category = db.query(Category).filter(Category.id == activity_in.category_id).first()
    if not category:
        return ApiResponse(code=400, msg="分类不存在")

    # 验证时间
    if activity_in.end_time <= activity_in.start_time:
        return ApiResponse(code=400, msg="结束时间必须晚于开始时间")

    activity = Activity(**activity_in.model_dump())
    db.add(activity)
    db.commit()
    db.refresh(activity)

    return ApiResponse(code=200, msg="活动创建成功", data=activity_to_dict(activity))


@router.put("/{activity_id}", response_model=ApiResponse)
def update_activity(activity_id: int, activity_in: ActivityUpdate, db: Session = Depends(get_db)):
    """编辑活动"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        return ApiResponse(code=404, msg="活动不存在")

    update_data = activity_in.model_dump(exclude_unset=True)

    # 如果更新分类，验证分类存在
    if "category_id" in update_data:
        category = db.query(Category).filter(Category.id == update_data["category_id"]).first()
        if not category:
            return ApiResponse(code=400, msg="分类不存在")

    # 更新字段
    for key, value in update_data.items():
        setattr(activity, key, value)

    # 验证时间
    if activity.end_time <= activity.start_time:
        return ApiResponse(code=400, msg="结束时间必须晚于开始时间")

    db.commit()
    db.refresh(activity)

    return ApiResponse(code=200, msg="活动更新成功", data=activity_to_dict(activity))


@router.delete("/{activity_id}", response_model=ApiResponse)
def delete_activity(activity_id: int, db: Session = Depends(get_db)):
    """取消/删除活动（标记为已取消状态）"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        return ApiResponse(code=404, msg="活动不存在")

    # 软删除：将状态改为已取消
    activity.status = "已取消"
    db.commit()

    return ApiResponse(code=200, msg="活动已取消", data={"id": activity_id, "status": "已取消"})


@router.get("/{activity_id}/countdown", response_model=ApiResponse)
def get_countdown(activity_id: int, db: Session = Depends(get_db)):
    """获取活动倒计时（返回距离开始的秒数）"""
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity:
        return ApiResponse(code=404, msg="活动不存在")

    now = datetime.now()
    diff = activity.start_time - now
    seconds = int(diff.total_seconds())

    if seconds < 0:
        status = "已开始" if activity.end_time > now else "已结束"
    else:
        status = "未开始"

    return ApiResponse(
        code=200,
        msg="success",
        data={
            "activity_id": activity_id,
            "seconds": seconds,
            "status": status,
            "start_time": activity.start_time.isoformat(),
        },
    )
