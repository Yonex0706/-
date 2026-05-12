import csv
import io
import os
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import engine, Base, SessionLocal, get_db
from backend.models import User, Category, Item, ItemImage, Favorite, Message, Review, Order, Post
from backend.schemas import (
    UserRegister, UserLogin, UserOut, UserUpdate,
    CategoryOut,
    ItemCreate, ItemUpdate, ItemOut, ItemListOut,
    FavoriteToggle, FavoriteToggleOut,
    MessageCreate, MessageOut,
    ReviewCreate, ReviewOut,
    OrderCreate, OrderUpdate, OrderOut,
    StatsOut, BatchUpdate, PostCreate, PostOut,
)

app = FastAPI(title="校园二手交易平台 API", version="2.0")

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files directory for uploads ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ══════════════════════════════════════════════════
#  Helper
# ══════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def item_to_out(item: Item, user_id: Optional[int] = None) -> ItemOut:
    """Convert an Item ORM object to ItemOut schema, with optional is_favorited."""
    is_fav = False
    if user_id is not None:
        is_fav = any(f.user_id == user_id for f in item.favorites)
    return ItemOut(
        id=item.id,
        title=item.title,
        description=item.description,
        price=item.price,
        original_price=item.original_price,
        status=item.status,
        view_count=item.view_count,
        seller_id=item.seller_id,
        category_id=item.category_id,
        image_url=item.image_url,
        created_at=item.created_at,
        updated_at=item.updated_at,
        seller_name=item.seller.username if item.seller else None,
        category_name=item.category.name if item.category else None,
        images=[{"id": img.id, "image_url": img.image_url, "sort_order": img.sort_order}
                for img in (item.images or [])],
        is_favorited=is_fav,
    )


# ══════════════════════════════════════════════════
#  Auth
# ══════════════════════════════════════════════════

@app.post("/api/register", response_model=UserOut)
def register(body: UserRegister, db: Session = Depends(get_db)):
    """注册新用户"""
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "用户名已存在")
    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/login", response_model=UserOut)
def login(body: UserLogin, db: Session = Depends(get_db)):
    """用户登录，返回用户信息"""
    user = db.query(User).filter(User.username == body.username).first()
    if not user or user.password_hash != hash_password(body.password):
        raise HTTPException(401, "用户名或密码错误")
    return user


@app.get("/api/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


@app.put("/api/users/{user_id}/profile", response_model=UserOut)
def update_profile(user_id: int, body: UserUpdate, db: Session = Depends(get_db)):
    """更新用户个人资料"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


# ══════════════════════════════════════════════════
#  Categories
# ══════════════════════════════════════════════════

@app.get("/api/categories", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """获取所有分类"""
    return db.query(Category).all()


# ══════════════════════════════════════════════════
#  Items – CRUD
# ══════════════════════════════════════════════════

@app.get("/api/items/", response_model=ItemListOut)
def list_items(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    keyword: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    status: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    分页 + 高级筛选 + 排序 查询物品
    多表联查: Item ←→ Category, Item ←→ User
    """
    q = db.query(Item).join(Item.seller).outerjoin(Item.category)

    if keyword:
        like = f"%{keyword}%"
        q = q.filter((Item.title.ilike(like)) | (Item.description.ilike(like)))
    if category_id:
        q = q.filter(Item.category_id == category_id)
    if min_price is not None:
        q = q.filter(Item.price >= min_price)
    if max_price is not None:
        q = q.filter(Item.price <= max_price)
    if status:
        q = q.filter(Item.status == status)

    # Sorting
    sort_map = {
        "created_at": Item.created_at,
        "price": Item.price,
        "view_count": Item.view_count,
    }
    col = sort_map.get(sort_by, Item.created_at)
    order_fn = col.desc if sort_order == "desc" else col.asc
    q = q.order_by(order_fn())

    total = q.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # Build favorite set for the requesting user
    fav_item_ids = set()
    if user_id is not None:
        favs = db.query(Favorite.item_id).filter(Favorite.user_id == user_id).all()
        fav_item_ids = {f[0] for f in favs}

    out_items = []
    for item in items:
        obj = item_to_out(item)
        obj.is_favorited = item.id in fav_item_ids
        out_items.append(obj)

    return ItemListOut(
        items=out_items, total=total, page=page,
        page_size=page_size, total_pages=total_pages,
    )


@app.get("/api/items/hot", response_model=list[ItemOut])
def hot_items(limit: int = Query(8, ge=1, le=50), db: Session = Depends(get_db)):
    """浏览量最高的热门商品"""
    items = db.query(Item).filter(Item.status == "active") \
        .order_by(Item.view_count.desc()).limit(limit).all()
    return [item_to_out(it) for it in items]


@app.get("/api/items/export")
def export_items_csv(db: Session = Depends(get_db)):
    """导出物品数据为CSV"""
    items = db.query(Item).order_by(Item.id).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ID", "标题", "描述", "价格", "原价", "状态", "浏览量",
                     "卖家", "分类", "创建时间"])
    for it in items:
        writer.writerow([
            it.id, it.title, it.description, it.price, it.original_price,
            it.status, it.view_count,
            it.seller.username if it.seller else "",
            it.category.name if it.category else "",
            it.created_at,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=items_export.csv"},
    )


@app.post("/api/items/batch-update")
def batch_update_items(body: BatchUpdate, db: Session = Depends(get_db)):
    """管理员批量修改物品状态"""
    items = db.query(Item).filter(Item.id.in_(body.item_ids)).all()
    if not items:
        raise HTTPException(404, "未找到任何匹配的物品")
    for item in items:
        item.status = body.status
        item.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "updated": len(items)}


@app.get("/api/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, user_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    """
    物品详情。有原子性 view_count +1 操作。
    通过查询参数 user_id 传入当前用户以标记收藏状态。
    """
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    item.view_count = Item.view_count + 1
    db.commit()
    db.refresh(item)
    return item_to_out(item, user_id)


@app.post("/api/items/", response_model=ItemOut, status_code=201)
def create_item(body: ItemCreate, db: Session = Depends(get_db)):
    """发布物品"""
    if not db.query(User).filter(User.id == body.seller_id).first():
        raise HTTPException(400, "卖家不存在")
    if body.category_id and not db.query(Category).filter(Category.id == body.category_id).first():
        raise HTTPException(400, "分类不存在")
    item = Item(
        title=body.title,
        description=body.description,
        price=body.price,
        original_price=body.original_price,
        category_id=body.category_id,
        image_url=body.image_url,
        seller_id=body.seller_id,
        status="active",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item_to_out(item)


@app.put("/api/items/{item_id}", response_model=ItemOut)
def update_item(item_id: int, body: ItemUpdate, db: Session = Depends(get_db)):
    """编辑物品（仅物主可操作）"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    # Authentication: caller must pass user_id in query param for simplicity
    # We rely on the frontend sending the correct user_id
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item_to_out(item)


@app.delete("/api/items/{item_id}")
def delete_item(item_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    """删除物品（仅物主或管理员可操作）"""
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    if item.seller_id != user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.role != "admin":
            raise HTTPException(403, "无权删除该物品")
    db.delete(item)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
#  User Items & Favorites
# ══════════════════════════════════════════════════

@app.get("/api/users/{user_id}/items", response_model=ItemListOut)
def list_user_items(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1),
    db: Session = Depends(get_db),
):
    """获取某用户发布的所有物品（分页）"""
    q = db.query(Item).filter(Item.seller_id == user_id).order_by(Item.created_at.desc())
    total = q.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return ItemListOut(
        items=[item_to_out(it) for it in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


@app.get("/api/users/{user_id}/favorites", response_model=ItemListOut)
def list_user_favorites(
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1),
    db: Session = Depends(get_db),
):
    """获取用户的收藏列表（分页，携带物品详细信息）"""
    q = db.query(Item).join(Favorite).filter(Favorite.user_id == user_id) \
        .order_by(Favorite.created_at.desc())
    total = q.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return ItemListOut(
        items=[item_to_out(it, user_id) for it in items],
        total=total, page=page, page_size=page_size, total_pages=total_pages,
    )


# ══════════════════════════════════════════════════
#  Favorites Toggle
# ══════════════════════════════════════════════════

@app.post("/api/favorites/", response_model=FavoriteToggleOut)
def toggle_favorite(body: FavoriteToggle, db: Session = Depends(get_db)):
    """
    切换收藏状态。如果已收藏则取消，未收藏则添加。
    使用事务保证原子性。
    """
    existing = db.query(Favorite).filter(
        Favorite.user_id == body.user_id,
        Favorite.item_id == body.item_id,
    ).first()
    if existing:
        db.delete(existing)
        db.commit()
        return FavoriteToggleOut(favorited=False)
    else:
        fav = Favorite(user_id=body.user_id, item_id=body.item_id)
        db.add(fav)
        db.commit()
        return FavoriteToggleOut(favorited=True)


# ══════════════════════════════════════════════════
#  Stats
# ══════════════════════════════════════════════════

@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    """平台统计：物品总数、用户总数、分类总数、平均价格"""
    total_items = db.query(func.count(Item.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_categories = db.query(func.count(Category.id)).scalar() or 0
    avg_price = db.query(func.avg(Item.price)).scalar() or 0.0
    return StatsOut(
        total_items=total_items,
        total_users=total_users,
        total_categories=total_categories,
        avg_price=round(float(avg_price), 2),
    )


# ══════════════════════════════════════════════════
#  Image Upload
# ══════════════════════════════════════════════════

@app.post("/api/upload")
async def upload_image(file: UploadFile = File(...)):
    """上传图片到 static/uploads 目录，返回 URL"""
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    url = f"/static/uploads/{filename}"
    return {"url": url}


# ══════════════════════════════════════════════════
#  Messages (Chat)
# ══════════════════════════════════════════════════

@app.get("/api/messages/", response_model=list[MessageOut])
def list_messages(
    user_id: int = Query(...),
    other_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """获取用户的消息列表。若 other_id 则返回与该用户的对话。"""
    q = db.query(Message).filter(
        (Message.sender_id == user_id) | (Message.receiver_id == user_id)
    )
    if other_id:
        q = q.filter(
            (Message.sender_id == other_id) | (Message.receiver_id == other_id)
        )
    messages = q.order_by(Message.created_at.asc(), Message.id.asc()).all()
    result = []
    for m in messages:
        result.append(MessageOut(
            id=m.id, sender_id=m.sender_id, receiver_id=m.receiver_id,
            item_id=m.item_id, content=m.content, is_read=m.is_read,
            created_at=m.created_at,
            sender_name=m.sender.username if m.sender else None,
            receiver_name=m.receiver.username if m.receiver else None,
        ))
    return result


@app.post("/api/messages/", response_model=MessageOut, status_code=201)
def send_message(body: MessageCreate, db: Session = Depends(get_db)):
    """发送消息"""
    if not db.query(User).filter(User.id == body.sender_id).first():
        raise HTTPException(400, "发送者不存在")
    if not db.query(User).filter(User.id == body.receiver_id).first():
        raise HTTPException(400, "接收者不存在")
    msg = Message(
        sender_id=body.sender_id, receiver_id=body.receiver_id,
        item_id=body.item_id, content=body.content,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(
        id=msg.id, sender_id=msg.sender_id, receiver_id=msg.receiver_id,
        item_id=msg.item_id, content=msg.content, is_read=msg.is_read,
        created_at=msg.created_at,
        sender_name=msg.sender.username if msg.sender else None,
        receiver_name=msg.receiver.username if msg.receiver else None,
    )


@app.get("/api/messages/unread-count")
def unread_count(user_id: int = Query(...), db: Session = Depends(get_db)):
    """未读消息数量"""
    count = db.query(func.count(Message.id)).filter(
        Message.receiver_id == user_id, Message.is_read == 0
    ).scalar() or 0
    return {"count": count}


@app.put("/api/messages/{message_id}/read")
def mark_message_read(message_id: int, db: Session = Depends(get_db)):
    """标记消息为已读"""
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(404, "消息不存在")
    msg.is_read = 1
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
#  Reviews
# ══════════════════════════════════════════════════

@app.post("/api/reviews/", response_model=ReviewOut, status_code=201)
def create_review(body: ReviewCreate, db: Session = Depends(get_db)):
    """创建评价"""
    if body.reviewer_id == body.reviewee_id:
        raise HTTPException(400, "不能给自己评价")
    if not db.query(Item).filter(Item.id == body.item_id).first():
        raise HTTPException(400, "物品不存在")
    review = Review(
        reviewer_id=body.reviewer_id, reviewee_id=body.reviewee_id,
        item_id=body.item_id, rating=body.rating, comment=body.comment,
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return ReviewOut(
        id=review.id, reviewer_id=review.reviewer_id,
        reviewee_id=review.reviewee_id, item_id=review.item_id,
        rating=review.rating, comment=review.comment,
        created_at=review.created_at,
        reviewer_name=review.reviewer.username if review.reviewer else None,
    )


@app.get("/api/reviews/", response_model=list[ReviewOut])
def list_reviews(
    reviewee_id: Optional[int] = None,
    item_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """获取评价列表，可按被评价人或物品筛选"""
    q = db.query(Review)
    if reviewee_id:
        q = q.filter(Review.reviewee_id == reviewee_id)
    if item_id:
        q = q.filter(Review.item_id == item_id)
    reviews = q.order_by(Review.created_at.desc()).all()
    result = []
    for r in reviews:
        result.append(ReviewOut(
            id=r.id, reviewer_id=r.reviewer_id, reviewee_id=r.reviewee_id,
            item_id=r.item_id, rating=r.rating, comment=r.comment,
            created_at=r.created_at,
            reviewer_name=r.reviewer.username if r.reviewer else None,
        ))
    return result


@app.get("/api/users/{user_id}/rating")
def user_rating(user_id: int, db: Session = Depends(get_db)):
    """获取用户的平均评分和评价数量"""
    stats = db.query(
        func.avg(Review.rating), func.count(Review.id),
    ).filter(Review.reviewee_id == user_id).first()
    avg = round(float(stats[0]), 1) if stats[0] else 0.0
    count = stats[1] if stats[1] else 0
    return {"avg_rating": avg, "total_reviews": count}


# ══════════════════════════════════════════════════
#  Orders
# ══════════════════════════════════════════════════

@app.post("/api/orders/", response_model=OrderOut, status_code=201)
def create_order(body: OrderCreate, db: Session = Depends(get_db)):
    """
    创建订单（买家发起购买请求）。
    自动将物品状态变为 reserved。
    """
    item = db.query(Item).filter(Item.id == body.item_id).first()
    if not item:
        raise HTTPException(404, "物品不存在")
    if item.status != "active":
        raise HTTPException(400, "物品不可购买")
    if item.seller_id == body.buyer_id:
        raise HTTPException(400, "不能购买自己的物品")

    order = Order(buyer_id=body.buyer_id, item_id=body.item_id, status="pending")
    item.status = "reserved"
    db.add(order)
    db.commit()
    db.refresh(order)
    return OrderOut(
        id=order.id, buyer_id=order.buyer_id, item_id=order.item_id,
        status=order.status, created_at=order.created_at,
        buyer_name=order.buyer.username if order.buyer else None,
        item_title=order.item.title if order.item else None,
    )


@app.get("/api/orders/", response_model=list[OrderOut])
def list_orders(
    user_id: int = Query(...),
    as_buyer: bool = True,
    db: Session = Depends(get_db),
):
    """获取订单列表（买家或卖家视角）"""
    if as_buyer:
        q = db.query(Order).filter(Order.buyer_id == user_id)
    else:
        q = db.query(Order).join(Item).filter(Item.seller_id == user_id)
    orders = q.order_by(Order.created_at.desc()).all()
    result = []
    for o in orders:
        result.append(OrderOut(
            id=o.id, buyer_id=o.buyer_id, item_id=o.item_id,
            status=o.status, created_at=o.created_at,
            buyer_name=o.buyer.username if o.buyer else None,
            item_title=o.item.title if o.item else None,
        ))
    return result


@app.put("/api/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, body: OrderUpdate, db: Session = Depends(get_db)):
    """
    更新订单状态（卖家确认/拒绝，状态流转）。
    物品状态联动：order completed → item sold
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(404, "订单不存在")
    order.status = body.status
    item = db.query(Item).filter(Item.id == order.item_id).first()
    if body.status == "completed":
        item.status = "sold"
    elif body.status == "cancelled":
        item.status = "active"
    db.commit()
    db.refresh(order)
    return OrderOut(
        id=order.id, buyer_id=order.buyer_id, item_id=order.item_id,
        status=order.status, created_at=order.created_at,
        buyer_name=order.buyer.username if order.buyer else None,
        item_title=order.item.title if order.item else None,
    )



# ══════════════════════════════════════════════════
#  Posts (User Moments)
# ══════════════════════════════════════════════════

@app.post("/api/posts/", response_model=PostOut, status_code=201)
def create_post(body: PostCreate, db: Session = Depends(get_db)):
    """发布个人动态"""
    user = db.query(User).filter(User.id == body.user_id).first()
    if not user:
        raise HTTPException(400, "用户不存在")
    post = Post(user_id=body.user_id, content=body.content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return PostOut(
        id=post.id, user_id=post.user_id, content=post.content,
        created_at=post.created_at,
        author_name=user.username,
        author_avatar=user.avatar_url,
    )


@app.get("/api/users/{user_id}/posts", response_model=list[PostOut])
def list_user_posts(user_id: int, db: Session = Depends(get_db)):
    """获取用户个人动态列表"""
    posts = db.query(Post).filter(Post.user_id == user_id)         .order_by(Post.created_at.desc()).all()
    user = db.query(User).filter(User.id == user_id).first()
    result = []
    for p in posts:
        result.append(PostOut(
            id=p.id, user_id=p.user_id, content=p.content,
            created_at=p.created_at,
            author_name=user.username if user else None,
            author_avatar=user.avatar_url if user else None,
        ))
    return result


@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, user_id: int = Query(...), db: Session = Depends(get_db)):
    """删除自己的动态"""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "动态不存在")
    if post.user_id != user_id:
        raise HTTPException(403, "无权删除")
    db.delete(post)
    db.commit()
    return {"ok": True}


# ══════════════════════════════════════════════════
#  Seed Data# ══════════════════════════════════════════════════

def seed_data():
    """应用启动时自动创建表并插入种子数据"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Category).count() > 0:
            return  # Already seeded

        # ── Categories ──
        cats = [
            Category(name="教材教辅", description="各专业教材、考试辅导书"),
            Category(name="电子产品", description="手机、电脑、耳机、数码配件"),
            Category(name="生活用品", description="宿舍用品、收纳、小电器"),
            Category(name="运动器材", description="球类、健身器材、户外装备"),
            Category(name="服饰鞋包", description="衣物、鞋帽、箱包"),
            Category(name="其他", description="其他二手物品"),
        ]
        db.add_all(cats)
        db.flush()

        # ── Users ──
        users = [
            User(username="alice", email="alice@school.edu",
                 password_hash=hash_password("1234"), role="user"),
            User(username="bob", email="bob@school.edu",
                 password_hash=hash_password("1234"), role="user"),
            User(username="admin", email="admin@school.edu",
                 password_hash=hash_password("admin"), role="admin"),
            User(username="steve", email="steve@school.edu",
                 password_hash=hash_password("1234"), role="user",
                 real_name="史蒂夫", student_id="2024001",
                 phone="13800000001", college="计算机科学与技术学院"),
            User(username="jack", email="jack@school.edu",
                 password_hash=hash_password("1234"), role="user",
                 real_name="杰克", student_id="2024002",
                 phone="13800000002", college="电子信息工程学院"),
        ]
        db.add_all(users)
        db.flush()

        # ── Items ──
        now = datetime.now(timezone.utc)
        items_data = [
            # (title, desc, price, orig_price, cat_idx, seller_idx, image, views, status)
            ("高等数学（第七版）", "同济大学教材，几乎全新，仅翻看过几页", 25.0, 48.0, 0, 0,
             "https://picsum.photos/seed/math/400/300", 120, "sold"),
            ("大学英语四级真题", "含2024年最新真题，附答案解析", 18.0, 39.8, 0, 1,
             "https://picsum.photos/seed/english/400/300", 85, "sold"),
            ("iPhone 15 手机壳", "透明硅胶材质，使用一个月", 10.0, 29.0, 1, 0,
             "https://picsum.photos/seed/iphone/400/300", 200, "active"),
            ("机械键盘 RK87", "红轴，87键，办公游戏皆可", 80.0, 199.0, 1, 1,
             "https://picsum.photos/seed/keyboard/400/300", 56, "sold"),
            ("蓝牙耳机 AirPods Pro", "二代，充电仓完好", 450.0, 899.0, 1, 0,
             "https://picsum.photos/seed/airpods/400/300", 310, "sold"),
            ("宿舍台灯", "LED护眼，三档调光，USB充电", 25.0, 59.0, 2, 1,
             "https://picsum.photos/seed/lamp/400/300", 42, "active"),
            ("电热水壶 1.5L", "九阳品牌，304不锈钢，使用半年", 30.0, 89.0, 2, 0,
             "https://picsum.photos/seed/kettle/400/300", 33, "active"),
            ("瑜伽垫 6mm", "TPE材质，防滑，附收纳带", 35.0, 79.0, 3, 1,
             "https://picsum.photos/seed/yoga/400/300", 67, "sold"),
            ("篮球 Spalding", "室外比赛用球，七成新", 40.0, 129.0, 3, 0,
             "https://picsum.photos/seed/ball/400/300", 91, "active"),
            ("冬季羽绒服 M码", "黑色，波司登，保暖效果好", 120.0, 399.0, 4, 1,
             "https://picsum.photos/seed/jacket/400/300", 78, "sold"),
            ("帆布双肩包", "灰绿色，容量大，日常通勤可用", 45.0, 99.0, 4, 0,
             "https://picsum.photos/seed/bag/400/300", 23, "active"),
            ("C语言程序设计", "谭浩强教材，有笔记标注", 15.0, 36.0, 0, 1,
             "https://picsum.photos/seed/cbook/400/300", 44, "sold"),
            ("充电宝 20000mAh", "小米，支持快充，双USB输出", 50.0, 99.0, 1, 0,
             "https://picsum.photos/seed/powerbank/400/300", 150, "active"),
            ("桌上收纳架", "双层木质，简约风格", 20.0, 45.0, 2, 1,
             "https://picsum.photos/seed/rack/400/300", 18, "sold"),
            ("吉他 41寸民谣", "雅马哈入门款，含琴包和教材", 200.0, 599.0, 5, 0,
             "https://picsum.photos/seed/guitar/400/300", 112, "sold"),
            ("画板画架套装", "4K画板+实木画架，美术生必备", 60.0, 150.0, 5, 1,
             "https://picsum.photos/seed/easel/400/300", 37, "sold"),
            # ── New items from steve & jack ──
            ("Java Web应用开发技术与案例教程", "完整项目案例，适合课程设计参考", 35.0, 68.0, 0, 3,
             "https://picsum.photos/seed/javaweb/400/300", 55, "active"),
            ("计算机操作系统（第四版）", "考研经典教材，有少量划线标注", 20.0, 45.0, 0, 4,
             "https://picsum.photos/seed/osbook/400/300", 73, "active"),
            ("马克思主义基本原理", "大学公共课教材，全新未翻", 15.0, 26.0, 0, 3,
             "https://picsum.photos/seed/marx/400/300", 42, "active"),
            ("李宁运动水壶", "750ml大容量，Tritan材质，使用一个月", 35.0, 89.0, 2, 4,
             "https://picsum.photos/seed/bottle/400/300", 28, "active"),
            ("Yonex 羽毛球拍", "天斧系列，含球包和手胶", 180.0, 450.0, 3, 3,
             "https://picsum.photos/seed/yonex/400/300", 95, "active"),
            ("水豚噜噜玩偶挂件", "正版授权，超可爱毛绒挂件", 25.0, 49.0, 5, 4,
             "https://picsum.photos/seed/capybara/400/300", 67, "active"),
            ("喜德盛 ad350 公路车", "入门公路车，骑行约200km，九五成新", 1200.0, 2899.0, 3, 3,
             "https://picsum.photos/seed/bike/400/300", 180, "active"),
            ("小米 15 Pro Max 1TB", "钛金属版本，全套包装配件齐全", 6999.0, 7999.0, 1, 4,
             "https://picsum.photos/seed/xiaomi15/400/300", 320, "active"),
            ("iPhone 17 Pro 512GB", "沙漠钛色，官网购入，使用一个月", 8999.0, 11999.0, 1, 3,
             "https://picsum.photos/seed/iphone17/400/300", 450, "active"),
            ("白色物品收纳箱", "加厚PP材质，带盖，60L大容量", 30.0, 69.0, 2, 4,
             "https://picsum.photos/seed/box/400/300", 15, "active"),
            ("美的吹风机 1800W", "负离子护发，恒温不伤发", 45.0, 129.0, 2, 3,
             "https://picsum.photos/seed/hairdryer/400/300", 38, "active"),
            ("安踏黑色跑鞋 42码", "轻便透气，仅穿两次，几乎全新", 80.0, 299.0, 4, 4,
             "https://picsum.photos/seed/shoes/400/300", 62, "active"),
        ]
        created_items = []
        for row in items_data:
            item = Item(
                title=row[0], description=row[1], price=row[2],
                original_price=row[3], category_id=cats[row[4]].id,
                seller_id=users[row[5]].id, image_url=row[6],
                view_count=row[7], status=row[8],
                created_at=now, updated_at=now,
            )
            db.add(item)
            db.flush()
            created_items.append(item)

        # ── Reviews ──
        # (item_idx, reviewer_idx, reviewee_idx, rating, comment)
        reviews_data = [
            (0, 1, 0, 5, "教材很新，几乎没有笔记，性价比很高"),
            (1, 0, 1, 5, "真题很全，解析详细，好好复习争取过级"),
            (3, 0, 1, 4, "红轴手感不错，打字很舒服"),
            (4, 1, 0, 5, "正品无疑，充电仓很干净，卖家很诚信"),
            (7, 0, 1, 5, "厚度刚好，做瑜伽很舒服，防滑效果好"),
            (9, 0, 1, 5, "羽绒服很暖和，波司登质量没话说，还送到了寝室楼下"),
            (11, 0, 1, 4, "书上有笔记，帮我省了很多时间"),
            (13, 0, 1, 3, "木质质量一般，但这个价格还要什么自行车"),
            (14, 1, 0, 5, "同学人很好，还教了我几个和弦，服务态度特别好"),
            (14, 1, 0, 1, "学不会吉他，不好玩，就练了一天放弃了"),
            (15, 0, 1, 5, "画架很稳，画板质量好，美术生强烈推荐"),
            # ── Reviews for new items ──
            (16, 1, 3, 5, "项目案例很实用，正好课程设计用得上"),
            (17, 0, 4, 4, "考研经典教材，有笔记省了自己总结的时间"),
            (18, 0, 3, 4, "公共课教材，这个价格很实惠"),
            (19, 0, 4, 5, "水壶质量很好，没有异味，容量也大"),
            (20, 1, 3, 5, "手感很好，比实体店便宜好多"),
            (21, 0, 4, 5, "太可爱了吧！室友看到都想要链接"),
            (22, 1, 3, 5, "成色很新，骑行很顺滑，卖家还送了头盔"),
            (23, 3, 4, 5, "顶配旗舰就是不一样，拍照太强了"),
            (24, 4, 3, 5, "沙漠钛太帅了，价格比官网便宜三千，真香"),
            (25, 3, 4, 4, "收纳箱容量很大，宿舍收纳神器"),
            (26, 4, 3, 4, "风力很大，吹干很快，负离子功能好用"),
            (27, 3, 4, 5, "鞋子很轻很透气，跑步非常舒服"),
        ]
        for item_idx, reviewer_idx, reviewee_idx, rating, comment in reviews_data:
            db.add(Review(
                reviewer_id=users[reviewer_idx].id,
                reviewee_id=users[reviewee_idx].id,
                item_id=created_items[item_idx].id,
                rating=rating, comment=comment,
                created_at=now,
            ))

        # ── Messages ──
        messages_data = [
            # Alice(0) ↔ Bob(1) — item 0: 高数教材
            (1, 0, 0, "同学你好，请问高数教材还在吗？", -21),
            (0, 1, 0, "在的，只有几页笔记，基本全新", -20.5),
            (1, 0, 0, "好的我要了，可以约个时间当面交易吗？", -20),
            (0, 1, 0, "可以，下午三点在图书馆一楼见？", -19),
            (1, 0, 0, "没问题，到时候联系", -18),
            # Alice(0) ↔ Bob(1) — item 4: 水壶
            (1, 0, 4, "同学你好，可以再发几张实物图吗，真心想要", -17),
            (0, 1, 4, "当然可以了，我现在在上课，你等我下课拍给你", -16),
            (1, 0, 4, "好的好的，不急", -15),
            # Alice(0) ↔ Steve(3) — item 16: Java教材
            (1, 3, 16, "学长好，请问Java教材还在吗？", -14),
            (3, 1, 16, "在的，里面项目案例很全", -13),
            (1, 3, 16, "好的我买了，方便今晚交易吗？", -12),
            # Alice(0) ↔ Jack(4) — item 21: 水豚挂件
            (0, 4, 21, "你好，水豚挂件还在吗？好可爱", -11),
            (4, 0, 21, "还在的，正版授权，全新仅拆封检查", -10),
            (0, 4, 21, "我要了！萌翻了", -9),
            # Bob(1) ↔ Steve(3) — item 22: 公路车
            (1, 3, 22, "兄弟，公路车出了吗？想看看实车", -8),
            (3, 1, 22, "还没出，这周末可以来看车", -7),
            # Steve(3) ↔ Jack(4) — item 23: 小米手机
            (3, 4, 23, "老哥，小米15 Pro Max还在吗？", -6),
            (4, 3, 23, "在的，全套包装都在，99新", -5),
            (3, 4, 23, "能少点吗？真心想要", -4),
            (4, 3, 23, "最多再少100，可以的话面交", -3),
        ]
        for sender_idx, receiver_idx, item_idx, content, hours_ago in messages_data:
            db.add(Message(
                sender_id=users[sender_idx].id,
                receiver_id=users[receiver_idx].id,
                item_id=created_items[item_idx].id,
                content=content,
                created_at=now + timedelta(hours=hours_ago),
            ))

        db.commit()
        print(f"[OK] Seed data: 6 categories, {len(users)} users, {len(items_data)} items, {len(reviews_data)} reviews, {len(messages_data)} messages")
    finally:
        db.close()


# ══════════════════════════════════════════════════
#  Serve Frontend SPA
# ══════════════════════════════════════════════════

# Serve uploaded files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


import mimetypes
frontend_dir = os.path.join(BASE_DIR, "frontend")


@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend static files with SPA fallback to index.html"""
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)
    # Try to serve actual file
    safe_path = full_path.split("?")[0]
    fp = os.path.normpath(os.path.join(frontend_dir, safe_path))
    if fp.startswith(os.path.normpath(frontend_dir)) and os.path.isfile(fp):
        media_type, _ = mimetypes.guess_type(fp)
        return FileResponse(fp, media_type=media_type)
    # SPA fallback
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "Frontend not found"}, status_code=404)


# ── Startup ──
@app.on_event("startup")
def on_startup():
    seed_data()
