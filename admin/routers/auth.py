from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db import SessionLocal
from models.user import User
from utils.security import verify_password
from utils.jwt import create_access_token, create_refresh_token, decode_access_token,decode_refresh_token
from utils.redis import redis_client
import logging

logger = logging.getLogger("app")

router = APIRouter()


# =====================
# 请求模型
# =====================

class LoginRequest(BaseModel):
    username: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# =====================
# 登录
# =====================
@router.post("/login")
def login(data: LoginRequest):

    db = SessionLocal()

    try:

        # 1. 打印：开始查询
        logger.info("开始查询用户，用户名：%s", data.username)

        # 你原来的查询
        user = db.query(User).filter(User.username == data.username).first()

        # 2. 打印：查询结果
        if user:
            logger.info("查询到用户：%s", user.username)
        else:
            # 这里如果打印出来，就是用户不存在
            logger.warning("用户不存在：%s", data.username)
        
        if not user:
            raise HTTPException(status_code=400, detail="user not found")

        if not verify_password(data.password, user.password):
            raise HTTPException(status_code=400, detail="wrong password")

        # access token（短期）
        access_token = create_access_token({
            "sub": str(user.id),
            "type": "access"
        })

        # refresh token（长期）
        refresh_token = create_refresh_token({
            "sub": str(user.id),
            "type": "refresh"
        })

        # 存 Redis（只允许一个有效 refresh_token）
        redis_client.set(
            f"refresh_token:{str(user.id)}",
            refresh_token,
            ex=7 * 24 * 60 * 60
        )

        return {
            "code": 200,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    finally:
        db.close()


# =====================
# 刷新 access_token
# =====================
@router.post("/refresh")
def refresh(data: RefreshRequest):

    # 1. decode refresh token
    payload = decode_refresh_token(data.refresh_token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Wrong token type")

    user_id = str(payload.get("sub"))
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # 2. Redis check  安全获取并解码 Redis token
    saved_token = redis_client.get(f"refresh_token:{user_id}")
    if not saved_token:
        raise HTTPException(status_code=401, detail="Refresh token expired")

    # 统一解码：一行搞定，不会有未赋值风险
    saved_token = saved_token.decode() if isinstance(saved_token, bytes) else saved_token

    # 解码 bytes 类型
    if isinstance(saved_token, bytes):
        saved_token = saved_token.decode()

    # 校验 token 是否一致
    if saved_token != data.refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked")

    # 3. issue new access token
    new_access_token = create_access_token({
        "sub": user_id,
        "type": "access"
    })

    return {
        "code": 200,
        "access_token": new_access_token
    }

# =====================
# 退出登录（推荐标准版）
# =====================
@router.post("/logout")
def logout(request: Request):

    auth = request.headers.get("Authorization")

    if auth:
        token = auth.replace("Bearer ", "").strip()
        payload = decode_access_token(token)

        if payload and payload.get("sub"):
            user_id = payload["sub"]

            # 删除 Redis refresh_token（核心）
            redis_client.delete(f"refresh_token:{user_id}")

    return {
        "code": 200,
        "msg": "logout success"
    }