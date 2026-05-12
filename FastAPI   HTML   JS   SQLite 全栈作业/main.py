from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
from pydantic import BaseModel
from typing import Optional

# ==================== 数据库配置 ====================
DATABASE_URL = "sqlite:///./student.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ==================== 数据库模型 ====================

class Student(Base):
    __tablename__ = "student"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    age = Column(Integer, default=18)

class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)

class SC(Base):
    __tablename__ = "sc"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("course.id"), nullable=False)
    student = relationship("Student")
    course = relationship("Course")

# 创建所有表（如果不存在则创建）
Base.metadata.create_all(bind=engine)

# ==================== Pydantic 请求体 ====================

class StudentCreate(BaseModel):
    name: str
    age: Optional[int] = 18

class CourseCreate(BaseModel):
    name: str

class SCCreate(BaseModel):
    student_id: int
    course_id: int

# ==================== FastAPI 应用 ====================

app = FastAPI(title="学生选课管理系统")

# ==================== 数据库依赖 ====================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== 页面路由 ====================

@app.get("/")
def root():
    return FileResponse("static/student.html")

@app.get("/student")
def student_page():
    return FileResponse("static/student.html")

@app.get("/course")
def course_page():
    return FileResponse("static/course.html")

@app.get("/sc")
def sc_page():
    return FileResponse("static/sc.html")

# ==================== 学生接口 ====================

@app.get("/api/students")
def get_students(db: Session = Depends(get_db)):
    return db.query(Student).all()

@app.post("/api/students")
def create_student(student: StudentCreate, db: Session = Depends(get_db)):
    db_student = Student(name=student.name, age=student.age)
    db.add(db_student)
    db.commit()
    db.refresh(db_student)
    return db_student

@app.delete("/api/students/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 先删除该学生的所有选课记录
    db.query(SC).filter(SC.student_id == student_id).delete()
    db.delete(student)
    db.commit()
    return {"message": "学生已删除"}

# ==================== 课程接口 ====================

@app.get("/api/courses")
def get_courses(db: Session = Depends(get_db)):
    return db.query(Course).all()

@app.post("/api/courses")
def create_course(course: CourseCreate, db: Session = Depends(get_db)):
    db_course = Course(name=course.name)
    db.add(db_course)
    db.commit()
    db.refresh(db_course)
    return db_course

@app.delete("/api/courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    # 先删除该课程的所有选课记录
    db.query(SC).filter(SC.course_id == course_id).delete()
    db.delete(course)
    db.commit()
    return {"message": "课程已删除"}

# ==================== 选课接口 ====================

@app.get("/api/sc")
def get_sc(db: Session = Depends(get_db)):
    records = db.query(SC).all()
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "student_id": r.student_id,
            "course_id": r.course_id,
            "student_name": r.student.name if r.student else "未知",
            "course_name": r.course.name if r.course else "未知"
        })
    return result

@app.post("/api/sc")
def create_sc(sc: SCCreate, db: Session = Depends(get_db)):
    # 检查学生是否存在
    student = db.query(Student).filter(Student.id == sc.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 检查课程是否存在
    course = db.query(Course).filter(Course.id == sc.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    db_sc = SC(student_id=sc.student_id, course_id=sc.course_id)
    db.add(db_sc)
    db.commit()
    db.refresh(db_sc)
    return {"id": db_sc.id, "student_id": db_sc.student_id, "course_id": db_sc.course_id}

@app.delete("/api/sc/{sc_id}")
def delete_sc(sc_id: int, db: Session = Depends(get_db)):
    sc = db.query(SC).filter(SC.id == sc_id).first()
    if not sc:
        raise HTTPException(status_code=404, detail="选课记录不存在")
    db.delete(sc)
    db.commit()
    return {"message": "选课记录已删除"}

# 挂载静态文件（必须放在最后）
app.mount("/static", StaticFiles(directory="static", html=True), name="static")