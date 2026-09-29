from fastapi import APIRouter, Request
from db import SessionLocal
from models.user import User

router = APIRouter(prefix="/user")


@router.get("/")
def get_users(request: Request):
    print("当前用户:", request.state.user)

    db = SessionLocal()

    try:
        users = db.query(User).all()

        return [
            {"id": u.id, "username": u.username}
            for u in users
        ]

    finally:
        db.close()