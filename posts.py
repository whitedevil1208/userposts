import os
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
    relationship,
)
from dotenv import load_dotenv

# ─── Load env vars ─────────────────────────────────────────────────────────────
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgres://user:pass@host:5432/db

# ─── Database setup ────────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# ─── Models ────────────────────────────────────────────────────────────────────
class UserPost(Base):
    __tablename__ = "userposts"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    content = Column(String(256), nullable=False)
    media_url = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    # when a post is deleted, its mappings are deleted too
    mappings = relationship(
        "UserPostMapping",
        back_populates="post",
        cascade="all, delete-orphan"
    )


class UserPostMapping(Base):
    __tablename__ = "userpostsmapping"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    post_id = Column(String, ForeignKey("userposts.id"), nullable=False)
    comments = Column(String(256), nullable=True)
    liked = Column(Boolean, default=False)
    disliked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("UserPost", back_populates="mappings")


# ─── Schemas ───────────────────────────────────────────────────────────────────
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


# ─── App init ───────────────────────────────────────────────────────────────────
app = FastAPI()
Base.metadata.create_all(bind=engine)


# ─── Dependency ────────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.post("/posts/")
def create_post(post: UserPostCreate, db: Session = Depends(get_db)):
    if db.query(UserPost).filter_by(id=post.id).first():
        raise HTTPException(400, "Post with this ID already exists")

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
        mappings = [
            {
                "id": m.id,
                "post_id": m.post_id,
                "comments": m.comments,
                "like": str(m.liked).lower(),
                "dislike": m.disliked
            }
            for m in post.mappings
        ]
        data.append({
            "id": post.id,
            "userId": post.user_id,
            "content": post.content,
            "imageUrl": post.media_url,
            "userPostmapping": mappings,
            "createdAt": post.created_at.isoformat() + "Z"
        })

    return {
        "status": "published",
        "message": "Posts fetched successfully.",
        "data": data
    }


@app.post("/posts/response/")
def add_post_response(response: UserPostMappingCreate, db: Session = Depends(get_db)):
    post = db.query(UserPost).filter_by(id=response.post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")

    db_map = UserPostMapping(
        post_id=response.post_id,
        user_id=response.user_id,
        comments=response.comments,
        liked=response.liked,
        disliked=response.disliked
    )
    db.add(db_map)
    db.commit()
    db.refresh(db_map)

    return {
        "status": "published",
        "message": "User response added successfully.",
        "data": [
            {
                "id": db_map.id,
                "post_id": db_map.post_id,
                "comments": db_map.comments,
                "like": str(db_map.liked).lower(),
                "dislike": db_map.disliked
            }
        ]
    }


@app.delete("/posts/{post_id}")
def delete_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(UserPost).filter_by(id=post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")

    db.delete(post)
    db.commit()
    return {
        "status": "deleted",
        "message": "Post deleted successfully."
    }
