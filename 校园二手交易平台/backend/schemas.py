from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── User ──
class UserRegister(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: Optional[str] = None
    password: str = Field(min_length=4)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    real_name: Optional[str] = None
    student_id: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """用户资料更新"""
    email: Optional[str] = None
    real_name: Optional[str] = None
    student_id: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None


# ── Category ──
class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ── ItemImage ──
class ItemImageOut(BaseModel):
    id: int
    image_url: str
    sort_order: int

    class Config:
        from_attributes = True


# ── Item ──
class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    price: float = Field(gt=0)
    original_price: Optional[float] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    seller_id: int


class ItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    original_price: Optional[float] = None
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    status: Optional[str] = None


class ItemOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    status: str
    view_count: int
    seller_id: int
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    seller_name: Optional[str] = None
    category_name: Optional[str] = None
    images: List[ItemImageOut] = []
    is_favorited: bool = False

    class Config:
        from_attributes = True


class ItemListOut(BaseModel):
    items: List[ItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int


# ── Favorite ──
class FavoriteToggle(BaseModel):
    user_id: int
    item_id: int


class FavoriteToggleOut(BaseModel):
    favorited: bool


# ── Message ──
class MessageCreate(BaseModel):
    sender_id: int
    receiver_id: int
    item_id: Optional[int] = None
    content: str = Field(min_length=1)


class MessageOut(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    item_id: Optional[int] = None
    content: str
    is_read: int
    created_at: datetime
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Review ──
class ReviewCreate(BaseModel):
    reviewer_id: int
    reviewee_id: int
    item_id: int
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None


class ReviewOut(BaseModel):
    id: int
    reviewer_id: int
    reviewee_id: int
    item_id: int
    rating: int
    comment: Optional[str] = None
    created_at: datetime
    reviewer_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Order ──
class OrderCreate(BaseModel):
    buyer_id: int
    item_id: int


class OrderUpdate(BaseModel):
    status: str


class OrderOut(BaseModel):
    id: int
    buyer_id: int
    item_id: int
    status: str
    created_at: datetime
    buyer_name: Optional[str] = None
    item_title: Optional[str] = None

    class Config:
        from_attributes = True


# ── Stats ──
class StatsOut(BaseModel):
    total_items: int
    total_users: int
    total_categories: int
    avg_price: float


# ── Batch Update ──
class BatchUpdate(BaseModel):
    item_ids: List[int]
    status: str


# ── Post ──
class PostCreate(BaseModel):
    user_id: int
    content: str = Field(min_length=1, max_length=500)


class PostOut(BaseModel):
    id: int
    user_id: int
    content: str
    created_at: datetime
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None

    class Config:
        from_attributes = True
