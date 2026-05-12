"""
校园活动日历系统 - FastAPI 主程序入口
启动命令：uvicorn main:app --reload --port=8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from models import Category, Activity, User
from database import SessionLocal
from routers import activities, categories

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="校园活动日历系统", version="1.0.0")

# 配置CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(activities.router)
app.include_router(categories.router)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def init_data():
    """应用启动时初始化默认分类数据"""
    db = SessionLocal()
    try:
        # 如果分类表为空，插入默认分类
        if db.query(Category).count() == 0:
            default_categories = [
                Category(name="讲座", icon="icon-lecture", color="#409EFF"),
                Category(name="竞赛", icon="icon-competition", color="#E6A23C"),
                Category(name="社团", icon="icon-club", color="#67C23A"),
                Category(name="课程", icon="icon-course", color="#F56C6C"),
                Category(name="会议", icon="icon-meeting", color="#909399"),
                Category(name="其他", icon="icon-other", color="#b37feb"),
            ]
            db.add_all(default_categories)
            db.commit()

        # 如果用户表为空，插入默认用户
        if db.query(User).count() == 0:
            default_users = [
                User(username="admin", role="管理员"),
                User(username="student1", role="普通用户"),
            ]
            db.add_all(default_users)
            db.commit()

        # 插入示例活动数据（仅当活动表为空时）
        if db.query(Activity).count() == 0:
            from datetime import datetime, timedelta
            import random

            categories = db.query(Category).all()
            cat_map = {c.name: c.id for c in categories}

            sample_activities = [
                {
                    "title": "人工智能前沿讲座",
                    "description": "邀请知名教授讲解AI最新研究进展，包括大语言模型和多模态学习",
                    "category_id": cat_map["讲座"],
                    "location": "图书馆报告厅",
                    "start_time": datetime(2026, 5, 15, 14, 0),
                    "end_time": datetime(2026, 5, 15, 16, 0),
                    "publisher": "计算机学院",
                },
                {
                    "title": "数学建模校赛",
                    "description": "全国大学生数学建模竞赛校内选拔赛，三人组队参赛",
                    "category_id": cat_map["竞赛"],
                    "location": "理科楼301",
                    "start_time": datetime(2026, 5, 18, 8, 0),
                    "end_time": datetime(2026, 5, 18, 17, 0),
                    "publisher": "教务处",
                },
                {
                    "title": "摄影社外拍活动",
                    "description": "本周六校园摄影外拍，主题：初夏校园风光",
                    "category_id": cat_map["社团"],
                    "location": "校门口集合",
                    "start_time": datetime(2026, 5, 20, 9, 0),
                    "end_time": datetime(2026, 5, 20, 12, 0),
                    "publisher": "摄影社",
                },
                {
                    "title": "数据结构课程设计答辩",
                    "description": "课程设计项目答辩，需准备PPT和演示程序",
                    "category_id": cat_map["课程"],
                    "location": "教学楼B205",
                    "start_time": datetime(2026, 5, 22, 13, 30),
                    "end_time": datetime(2026, 5, 22, 17, 30),
                    "publisher": "王老师",
                },
                {
                    "title": "学生会例会",
                    "description": "讨论下月校园文化节筹备工作",
                    "category_id": cat_map["会议"],
                    "location": "学生活动中心201",
                    "start_time": datetime(2026, 5, 12, 18, 30),
                    "end_time": datetime(2026, 5, 12, 20, 0),
                    "publisher": "学生会",
                },
                {
                    "title": "创业经验分享会",
                    "description": "邀请校友分享创业经历，解答同学们的疑问",
                    "category_id": cat_map["讲座"],
                    "location": "创新创业中心",
                    "start_time": datetime(2026, 5, 25, 15, 0),
                    "end_time": datetime(2026, 5, 25, 17, 0),
                    "publisher": "就业指导中心",
                },
                {
                    "title": "英语四级模拟考试",
                    "description": "四级考前模拟测试，检验备考效果",
                    "category_id": cat_map["竞赛"],
                    "location": "外语楼101-103",
                    "start_time": datetime(2026, 5, 14, 9, 0),
                    "end_time": datetime(2026, 5, 14, 11, 30),
                    "publisher": "外语学院",
                },
                {
                    "title": "篮球社团训练",
                    "description": "常规训练，备战校际联赛",
                    "category_id": cat_map["社团"],
                    "location": "体育馆篮球场",
                    "start_time": datetime(2026, 5, 13, 16, 0),
                    "end_time": datetime(2026, 5, 13, 18, 0),
                    "publisher": "篮球社",
                },
                {
                    "title": "操作系统期中考试",
                    "description": "闭卷考试，范围：进程管理、内存管理",
                    "category_id": cat_map["课程"],
                    "location": "教学楼A102",
                    "start_time": datetime(2026, 5, 28, 9, 0),
                    "end_time": datetime(2026, 5, 28, 11, 0),
                    "publisher": "李老师",
                },
                {
                    "title": "校园志愿者招募",
                    "description": "暑期支教志愿者招募说明会",
                    "category_id": cat_map["其他"],
                    "location": "学生活动中心多功能厅",
                    "start_time": datetime(2026, 5, 16, 14, 0),
                    "end_time": datetime(2026, 5, 16, 15, 30),
                    "publisher": "青年志愿者协会",
                },
            ]

            for item in sample_activities:
                activity = Activity(**item)
                db.add(activity)
            db.commit()

    finally:
        db.close()


@app.get("/")
def root():
    """API根路径，返回系统信息"""
    return {"message": "校园活动日历系统API", "version": "1.0.0", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
