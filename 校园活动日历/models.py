"""
SQLAlchemy ORM 模型定义
定义活动分类表、活动表、用户表及其关联关系
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Category(Base):
    """活动分类表"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, comment="分类名称")
    icon = Column(String(50), default="", comment="分类图标")
    color = Column(String(20), default="#409EFF", comment="分类颜色")

    # 与活动表的一对多关系
    activities = relationship("Activity", back_populates="category")


class Activity(Base):
    """活动表"""
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, comment="活动标题")
    description = Column(Text, default="", comment="活动描述")
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False, comment="分类ID")
    location = Column(String(200), default="", comment="活动地点")
    start_time = Column(DateTime, nullable=False, comment="开始时间")
    end_time = Column(DateTime, nullable=False, comment="结束时间")
    publisher = Column(String(100), default="", comment="发布者")
    status = Column(String(20), default="正常", comment="状态：正常/已取消")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 与分类表的多对一关系
    category = relationship("Category", back_populates="activities")


class User(Base):
    """用户表（简化版）"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, comment="用户名")
    role = Column(String(20), default="普通用户", comment="角色：管理员/普通用户")
