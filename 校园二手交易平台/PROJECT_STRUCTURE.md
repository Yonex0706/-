# 项目结构说明 — 校园二手交易平台

## 目录结构

```
校园二手交易平台/
├── .claude/                        # Claude Code 配置文件
│   └── settings.local.json         # 本地权限/设置（自动生成，可忽略）
├── .idea/                          # IDE 配置文件（自动生成，可忽略）
├── backend/                        # Python FastAPI 后端
│   ├── __pycache__/                # Python 字节码缓存（自动生成，可忽略）
│   ├── __init__.py                 # 包初始化文件（空）
│   ├── database.py                 # 数据库连接与会话配置
│   ├── main.py                     # FastAPI 应用：路由、种子数据、静态文件服务
│   ├── models.py                   # SQLAlchemy ORM 数据模型（8张表）
│   └── schemas.py                  # Pydantic 请求/响应模型
├── frontend/                       # Vue 3 前端 SPA
│   ├── app.js                      # Vue 3 应用：组件、API 函数、路由、状态管理
│   ├── index.html                  # SPA 入口页面
│   └── style.css                   # 全局样式（响应式布局）
├── static/                         # 静态资源目录
│   └── uploads/                    # 用户上传图片存储目录
├── campus_trade.db                 # SQLite 数据库文件
└── README.md                       # 项目说明文档
```

---

## 一、backend/ — Python 后端

### `backend/database.py` — 数据库引擎与会话

| 内容 | 说明 |
|------|------|
| `engine` | SQLAlchemy 引擎，连接 SQLite 文件 `campus_trade.db` |
| `SessionLocal` | 数据库会话工厂，每次请求创建独立会话 |
| `Base` | ORM 声明基类，所有模型继承自此类 |
| `get_db()` | FastAPI 依赖注入函数，自动管理会话生命周期 |

### `backend/models.py` — ORM 数据模型（8张表）

| 模型 | 表名 | 核心字段 | 说明 |
|------|------|---------|------|
| `User` | `users` | `id, username, password_hash, role, real_name, student_id, phone, college, avatar_url, bio` | 用户（user/admin 角色） |
| `Category` | `categories` | `id, name, description` | 物品分类（6种预置） |
| `Item` | `items` | `id, title, description, price, original_price, status, view_count, seller_id, category_id, image_url` | 物品（关联 User、Category） |
| `ItemImage` | `item_images` | `id, item_id, image_url, sort_order` | 物品多图（一对多） |
| `Favorite` | `favorites` | `id, user_id, item_id` | 收藏（用户-物品唯一约束） |
| `Message` | `messages` | `id, sender_id, receiver_id, item_id, content, is_read` | 站内私信 |
| `Review` | `reviews` | `id, reviewer_id, reviewee_id, item_id, rating, comment` | 商品评价（1-5分） |
| `Order` | `orders` | `id, buyer_id, item_id, status` | 订单/交易追踪 |
| `Post` | `posts` | `id, user_id, content` | 用户个人动态 |

### `backend/schemas.py` — Pydantic 数据校验模型

| Schema | 用途 |
|--------|------|
| `UserRegister` / `UserLogin` | 注册/登录请求体 |
| `UserOut` / `UserUpdate` | 用户信息返回 / 资料更新 |
| `CategoryOut` | 分类返回 |
| `ItemCreate` / `ItemUpdate` / `ItemOut` / `ItemListOut` | 物品 CRUD |
| `ItemImageOut` | 图片返回 |
| `FavoriteToggle` / `FavoriteToggleOut` | 收藏切换 |
| `MessageCreate` / `MessageOut` | 消息发送与返回 |
| `ReviewCreate` / `ReviewOut` | 评价创建与返回 |
| `OrderCreate` / `OrderUpdate` / `OrderOut` | 订单操作 |
| `StatsOut` | 平台统计 |
| `BatchUpdate` | 批量修改物品状态 |
| `PostCreate` / `PostOut` | 动态创建与返回 |

### `backend/main.py` — FastAPI 应用核心

**API 路由一览（共 31 个端点 + 1 个 SPA 兜底）：**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/register` | 用户注册 |
| POST | `/api/login` | 用户登录 |
| GET | `/api/users/{id}` | 获取用户信息 |
| PUT | `/api/users/{id}/profile` | 更新个人资料 |
| GET | `/api/categories` | 获取全部分类 |
| GET | `/api/items/` | 分页+筛选查询物品 |
| GET | `/api/items/hot` | 热门物品推荐 |
| GET | `/api/items/export` | 导出 CSV |
| POST | `/api/items/batch-update` | 批量修改物品状态 |
| GET | `/api/items/{id}` | 物品详情 |
| POST | `/api/items/` | 发布物品 |
| PUT | `/api/items/{id}` | 编辑物品 |
| DELETE | `/api/items/{id}` | 删除物品 |
| GET | `/api/users/{id}/items` | 用户发布的物品 |
| GET | `/api/users/{id}/favorites` | 用户收藏的物品 |
| POST | `/api/favorites/` | 切换收藏状态 |
| GET | `/api/stats` | 平台统计数据 |
| POST | `/api/upload` | 上传图片 |
| GET | `/api/messages/` | 获取消息列表（可指定对方用户） |
| POST | `/api/messages/` | 发送消息 |
| GET | `/api/messages/unread-count` | 未读消息数量 |
| PUT | `/api/messages/{id}/read` | 标记消息已读 |
| GET | `/api/reviews/` | 获取评价列表 |
| POST | `/api/reviews/` | 创建评价 |
| GET | `/api/users/{id}/rating` | 用户评分统计 |
| GET | `/api/orders/` | 获取订单列表 |
| POST | `/api/orders/` | 创建订单 |
| PUT | `/api/orders/{id}` | 更新订单状态 |
| GET | `/api/users/{id}/posts` | 获取用户动态 |
| POST | `/api/posts/` | 发布动态 |
| DELETE | `/api/posts/{id}` | 删除动态 |
| GET | `/{path}` | SPA 兜底：优先返回静态文件，否则返回 `index.html` |

**其他关键函数：**
- `seed_data()` — 首次启动时填充 6 个分类、5 个用户、24 个物品、20 条消息、28 条评价等演示数据

---

## 二、frontend/ — Vue 3 前端

### `frontend/index.html` — SPA 入口

| 内容 | 说明 |
|------|------|
| `<div id="app">` | Vue 3 挂载点 |
| 导航栏 | `首页 / 发布 / 我的发布 / 收藏 / 我的 / 消息 / 订单 / 管理 / 登录` |
| `<component :is="currentComponent">` | 动态页面组件占位符 |
| 页脚 | 版权信息 |
| Vue 3 CDN | `https://unpkg.com/vue@3` |
| `<script src="/app.js">` | 应用逻辑 |

**三个文件协作方式：**
```
index.html 提供骨架
    ↓ 加载
style.css 提供样式
    ↓ 加载
app.js 启动 Vue 应用，动态渲染页面到 <div id="app">
```

### `frontend/app.js` — Vue 3 应用逻辑

| 模块 | 说明 |
|------|------|
| **全局状态** (`store`) | `reactive` 对象：当前用户、当前页面、收藏状态、未读数等 |
| **工具函数** | `formatDate()`（相对时间）、`highlight()`（搜索高亮）、`statusLabel()`、`ratingStars()` |
| **API 函数** | 封装 `fetch`，涵盖所有后端端点（约 20 个函数） |
| **全局组件** | `PaginationWidget`、`ItemCard`、`ReviewCard` |

**页面组件（9个）：**

| 组件 | 路由键 | 功能 |
|------|--------|------|
| `HomePage` | `home` | 物品网格、筛选面板（关键词/分类/价格/排序）、分页 |
| `ItemDetail` | `detail` | 商品详情、图片画廊、收藏、购买、联系卖家、评价 |
| `ItemForm` | `publish` | 发布/编辑物品表单 |
| `MyItemsPage` | `my-items` | 当前用户物品列表、状态切换、编辑/删除 |
| `FavoritesPage` | `favorites` | 收藏物品网格 |
| `ProfilePage` | `profile` | 个人中心：头像上传、昵称/学院/学号/手机/邮箱内联编辑、统计、动态 |
| `LoginPage` | `login` | 登录/注册切换 |
| `ChatPage` | `chat` | 站内消息：左右两栏布局（联系人列表 + 聊天区），绿色/灰色气泡 |
| `OrdersPage` | `orders` | 订单列表（买家/卖家视图切换） |
| `AdminPage` | `admin` | 管理面板：统计数据、批量修改、CSV 导出、物品管理 |

### `frontend/style.css` — 全局样式

| 模块 | 说明 |
|------|------|
| 基础样式 | reset、字体、颜色变量 |
| 导航栏 | 固定顶部、响应式折叠 |
| 按钮 | primary/success/danger/warning/outline/sm 变体 |
| 卡片 | 圆角 16px、阴影、悬停效果 |
| 表单 | 输入框、选择框、文本域、错误状态 |
| 物品网格 | 4 列响应式布局（→ 3 列 → 2 列 → 1 列） |
| 筛选面板 | 水平排列搜索条件 |
| 详情页 | 图片画廊 + 信息双栏 |
| 聊天页 | 左右两栏、绿色/灰色气泡 |
| 个人中心 | 卡片布局、内联编辑字段 |
| 动态面板 | 发布输入框、动态列表 |
| 评价格式 | 星级评分 |
| 管理面板 | 统计卡片、表格 |
| 响应式断点 | 1024px / 768px / 480px |

---

## 三、数据库 campus_trade.db

SQLite 数据库，包含 8 张业务表 + 种子演示数据：

| 表名 | 记录数 | 说明 |
|------|--------|------|
| `users` | 5 | alice、bob、admin、steve、jack |
| `categories` | 6 | 教材、电子产品、生活用品等 |
| `items` | 24 | 各用户发布的物品 |
| `item_images` | 若干 | 物品多图 |
| `favorites` | 若干 | 收藏关系 |
| `messages` | 20 | 用户之间的私信 |
| `reviews` | 28 | 商品评价 |
| `orders` | 若干 | 交易订单 |
| `posts` | 2 | 用户动态 |

---

## 四、如何启动项目

### 环境要求
- Python 3.9+
- 安装依赖：`pip install fastapi uvicorn sqlalchemy pydantic`

### 启动命令

```bash
# 在项目根目录执行
uvicorn backend.main:app --reload --port 8100
```

### 访问地址
浏览器打开 **http://127.0.0.1:8100**

### 演示账号

| 用户名 | 密码 | 真实姓名 | 角色 |
|--------|------|---------|------|
| alice | 1234 | 杨一鸣 | 普通用户 |
| bob | 1234 | — | 普通用户 |
| steve | 1234 | 史蒂夫 | 普通用户 |
| jack | 1234 | 杰克 | 普通用户 |
| admin | admin | — | 管理员 |

---

## 五、核心功能模块

| 模块 | 涉及文件 | 说明 |
|------|---------|------|
| 用户认证 | `main.py` (login/register) + `LoginPage` | 注册/登录，localStorage 维持会话 |
| 物品管理 | `main.py` (items CRUD) + `ItemForm` + `MyItemsPage` | 发布/编辑/删除物品 |
| 浏览筛选 | `main.py` (items list) + `HomePage` + `ItemCard` | 网格展示、关键词/分类/价格筛选、排序、分页 |
| 收藏系统 | `main.py` (favorites) + `FavoritesPage` | 收藏/取消收藏，全局状态同步 |
| 站内消息 | `main.py` (messages) + `ChatPage` | 左右两栏聊天，5 秒轮询未读 |
| 商品评价 | `main.py` (reviews) + `ReviewCard` | 1-5 星评分，平均分计算 |
| 订单交易 | `main.py` (orders) + `OrdersPage` | 买家/卖家双视角，状态流转 |
| 个人中心 | `main.py` (profile/posts) + `ProfilePage` | 内联编辑资料、头像上传、动态发布 |
| 管理面板 | `main.py` (stats/batch/export) + `AdminPage` | 数据统计、批量更新、CSV 导出 |
| 图片上传 | `main.py` (upload) + `static/uploads/` | 文件上传，返回 URL |
