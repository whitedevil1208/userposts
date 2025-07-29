from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()

# ---------- DATABASE CONFIG ----------
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# ---------- DATABASE MODELS ----------
class UserPost(Base):
    __tablename__ = "userposts"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    content = Column(String(256), nullable=False)
    media_url = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    mappings = relationship("UserPostMapping", back_populates="post")


class UserPostMapping(Base):
    __tablename__ = "userpostsmapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    post_id = Column(String, ForeignKey("userposts.id"))
    comments = Column(String(256), nullable=True)
    liked = Column(Boolean, default=False)
    disliked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("UserPost", back_populates="mappings")


# ---------- SCHEMAS ----------
class UserPostCreate(BaseModel):
    id: str
    user_id: str
    content: str
    media_url: Optional[str] = None


class UserPostMappingCreate(BaseModel):
    post_id: str
    user_id: str
    comments: Optional[str] = None
    liked: bool = False
    disliked: bool = False


# ---------- FASTAPI INIT ----------
app = FastAPI()
Base.metadata.create_all(bind=engine)


# ---------- DEPENDENCY ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ROUTES ----------
@app.post("/posts/")
def create_post(post: UserPostCreate, db: Session = Depends(get_db)):
    if db.query(UserPost).filter(UserPost.id == post.id).first():
        raise HTTPException(status_code=400, detail="Post with this ID already exists")

    db_post = UserPost(
        id=post.id,
        user_id=post.user_id,
        content=post.content,
        media_url=post.media_url
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)

    return {
        "status": "published",
        "message": "Post created successfully.",
        "data": [
            {
                "id": db_post.id,
                "userId": db_post.user_id,
                "content": db_post.content,
                "imageUrl": db_post.media_url,
                "userPostmapping": [],
                "createdAt": db_post.created_at.isoformat() + "Z"
            }
        ]
    }


@app.get("/posts/")
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(UserPost).all()
    data = []

    for post in posts:
        mappings = []
        for m in post.mappings:
            mappings.append({
                "id": m.id,
                "post_id": m.post_id,
                "comments": m.comments,
                "like": str(m.liked).lower(),
                "dislike": m.disliked
            })

        data.append({
            "id": post.id,
            "userId": post.user_id,
            "content": post.content,
            "imageUrl": post.media_url,
            "userPostmapping": mappings,
            "createdAt": post.created_at.isoformat() + "Z" if post.created_at else None
        })

    return {
        "status": "published",
        "message": "Posts fetched successfully.",
        "data": data
    }


@app.post("/posts/response/")
def add_post_response(response: UserPostMappingCreate, db: Session = Depends(get_db)):
    post = db.query(UserPost).filter(UserPost.id == response.post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db_mapping = UserPostMapping(
        post_id=response.post_id,
        user_id=response.user_id,
        comments=response.comments,
        liked=response.liked,
        disliked=response.disliked
    )
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)

    return {
        "status": "published",
        "message": "User response added successfully.",
        "data": [
            {
                "id": db_mapping.id,
                "post_id": db_mapping.post_id,
                "comments": db_mapping.comments,
                "like": str(db_mapping.liked).lower(),
                "dislike": db_mapping.disliked
            }
        ]
    }
