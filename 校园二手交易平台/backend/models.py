from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(String(20), default="user")  # 'user' or 'admin'
    real_name = Column(String(50), nullable=True)   # 真实姓名
    student_id = Column(String(30), nullable=True)  # 学号
    phone = Column(String(20), nullable=True)       # 联系方式
    college = Column(String(100), nullable=True)    # 学院
    avatar_url = Column(String(500), nullable=True) # 头像URL
    bio = Column(String(200), nullable=True)        # 个性签名
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    items = relationship("Item", back_populates="seller", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    sent_messages = relationship(
        "Message", foreign_keys="Message.sender_id",
        back_populates="sender", cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "Message", foreign_keys="Message.receiver_id",
        back_populates="receiver", cascade="all, delete-orphan"
    )
    reviews_given = relationship(
        "Review", foreign_keys="Review.reviewer_id",
        back_populates="reviewer", cascade="all, delete-orphan"
    )
    reviews_received = relationship(
        "Review", foreign_keys="Review.reviewee_id",
        back_populates="reviewee", cascade="all, delete-orphan"
    )
    orders = relationship("Order", back_populates="buyer", cascade="all, delete-orphan")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(200), nullable=True)

    items = relationship("Item", back_populates="category")


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    original_price = Column(Float, nullable=True)
    status = Column(String(20), default="active")  # active, reserved, sold
    view_count = Column(Integer, default=0)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    seller = relationship("User", back_populates="items")
    category = relationship("Category", back_populates="items")
    favorites = relationship("Favorite", back_populates="item", cascade="all, delete-orphan")
    images = relationship("ItemImage", back_populates="item", cascade="all, delete-orphan",
                          order_by="ItemImage.sort_order")
    messages = relationship("Message", back_populates="item", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="item", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="item", cascade="all, delete-orphan")


class ItemImage(Base):
    """多图上传支持"""
    __tablename__ = "item_images"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    image_url = Column(String(500), nullable=False)
    sort_order = Column(Integer, default=0)

    item = relationship("Item", back_populates="images")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "item_id", name="uq_user_item_favorite"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="favorites")
    item = relationship("Item", back_populates="favorites")


class Message(Base):
    """站内私信"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    is_read = Column(Integer, default=0)  # 0=unread, 1=read
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    item = relationship("Item", back_populates="messages")


class Review(Base):
    """商品评价"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reviewee_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    reviewer = relationship("User", foreign_keys=[reviewer_id], back_populates="reviews_given")
    reviewee = relationship("User", foreign_keys=[reviewee_id], back_populates="reviews_received")
    item = relationship("Item", back_populates="reviews")


class Order(Base):
    """订单/交易追踪"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")  # pending, paid, shipped, completed, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    buyer = relationship("User", back_populates="orders")
    item = relationship("Item", back_populates="orders")


class Post(Base):
    """用户个人动态"""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    author = relationship("User", back_populates="posts")
