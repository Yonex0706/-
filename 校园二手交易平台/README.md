# 校园二手交易平台（进阶版）

基于 **FastAPI + SQLAlchemy + Vue 3 (CDN)** 的全栈校园二手交易平台，用于 Web 可视化课程设计答辩。

## 技术栈

- **后端**: Python FastAPI, SQLAlchemy ORM, SQLite
- **前端**: Vue 3 (Composition API, CDN), HTML5, CSS3 (Flex/Grid)
- **通信**: RESTful JSON API, `fetch` 异步请求

## 功能特性

### 核心功能
- 用户注册/登录（模拟 Session，localStorage 持久化）
- 物品发布、编辑、删除（仅物主可操作）
- 物品卡片网格浏览与分页
- 多条件筛选（关键词、分类、价格区间、排序）
- 物品详情页（浏览量计数、收藏状态、图片画廊）
- 收藏/取消收藏（全局状态同步）
- 搜索关键词高亮显示
- 响应式布局（桌面 4 列 → 平板 3 列 → 手机 1 列）

### 🏆 进阶功能（答辩亮点）
- **多图上传 & 图片画廊**: 支持上传多张图片，详情页画廊浏览
- **站内私信/聊天**: 实时对话界面，5000ms 轮询未读消息
- **商品评价系统**: 1-5 星评分，平均评分显示，评价列表
- **订单/交易追踪**: 购买请求 → 卖家确认 → 完成/取消，物品状态联动
- **管理面板**: 数据统计、批量修改物品状态、CSV 导出
- **全局收藏状态同步**: 在一处收藏/取消，所有页面同步更新

## 项目结构

```
campus_trade/
├── backend/
│   ├── main.py       # FastAPI 应用、API 路由、种子数据
│   ├── database.py   # SQLAlchemy 数据库连接配置
│   ├── models.py     # 数据模型（User, Item, Category, Favorite, etc.）
│   └── schemas.py    # Pydantic 请求/响应模型
├── frontend/
│   ├── index.html    # SPA 入口（Vue 3 CDN）
│   ├── style.css     # 样式文件（响应式布局）
│   └── app.js        # Vue 3 应用逻辑（组件、API、路由）
├── static/
│   └── uploads/      # 图片上传目录
└── README.md
```

## 数据库模型（8 张表）

- **User** — 用户（支持 user/admin 角色）
- **Category** — 物品分类（6 种预置）
- **Item** — 物品（关联 User、Category，级联删除）
- **ItemImage** — 物品多图（一对多，排序）
- **Favorite** — 收藏（用户-物品唯一约束，级联删除）
- **Message** — 站内私信（sender, receiver, item）
- **Review** — 商品评价（1-5 分）
- **Order** — 订单/交易追踪（状态机流转）

## 启动方法

### 环境要求
- Python 3.9+
- 安装依赖包

### 1. 安装依赖

```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

### 2. 启动服务

在项目根目录 `campus_trade/` 下运行：

```bash
uvicorn backend.main:app --reload
```

### 3. 访问

打开浏览器访问：**http://127.0.0.1:8100**

### 4. 演示账号

| 用户名 | 密码 | 真实姓名 | 角色 |
|--------|------|---------|------|
| alice  | 1234 | 杨一鸣 | 普通用户（卖家/买家） |
| bob    | 1234 | — | 普通用户（卖家/买家） |
| steve  | 1234 | 史蒂夫 | 普通用户（卖家/买家） |
| jack   | 1234 | 杰克 | 普通用户（卖家/买家） |
| admin  | admin | — | 管理员 |

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/register | 注册 |
| POST | /api/login | 登录 |
| GET | /api/items/ | 分页+筛选查询物品 |
| GET | /api/items/{id} | 物品详情 |
| POST | /api/items/ | 发布物品 |
| PUT | /api/items/{id} | 编辑物品 |
| DELETE | /api/items/{id} | 删除物品 |
| GET | /api/items/hot | 热门物品 |
| GET | /api/items/export | 导出 CSV |
| POST | /api/items/batch-update | 批量修改状态 |
| GET | /api/categories | 分类列表 |
| POST | /api/favorites/ | 切换收藏 |
| GET | /api/users/{id}/items | 用户物品 |
| GET | /api/users/{id}/favorites | 用户收藏 |
| GET | /api/users/{id}/rating | 用户评分 |
| GET | /api/stats | 平台统计 |
| POST | /api/upload | 图片上传 |
| GET/POST | /api/messages/ | 消息列表/发送 |
| GET/POST | /api/reviews/ | 评价列表/创建 |
| GET/POST | /api/orders/ | 订单列表/创建 |
| PUT | /api/orders/{id} | 更新订单状态 |

## 课程设计要点

- **多表关联查询**: Item ↔ Category ↔ User 联查，分页 + 条件筛选
- **事务处理**: 浏览量原子递增、收藏切换、订单状态流转
- **响应式布局**: CSS Grid + Media Query，四档响应断点
- **前后端分离**: 纯 JSON 交互，Vue 动态组件 SPA
- **状态管理**: reactive 全局 store，收藏状态跨组件同步
