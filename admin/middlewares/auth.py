from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.jwt import decode_access_token
import logging
logger = logging.getLogger("app")

PUBLIC_PATHS = {
    "/api/login",
    "/api/refresh",
    "/login",
    "/refresh",
}

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path.rstrip("/")

        # 🚀 1. 放行 CORS 预检请求
        if request.method == "OPTIONS":
            return await call_next(request)

        # 🚀 2. 白名单（必须最先）
        if path in PUBLIC_PATHS:
            logger.info(f"PUBLIC PATH ALLOWED: {path}")
            return await call_next(request)

        # 🚀 3. 获取 token
        auth = request.headers.get("Authorization")

        if not auth:
            return JSONResponse(
                status_code=401,
                content={"detail": "Not logged in"}
            )

        # 🚀 4. 提取 token
        if not auth.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid Authorization format"}
            )

        token = auth.replace("Bearer ", "").strip()

        # 🚀 5. 解析 JWT
        payload = decode_access_token(token)

        if not payload:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token"}
            )

        # 🚀 6. token 类型检查
        if payload.get("type") != "access":
            return JSONResponse(
                status_code=401,
                content={"detail": "Wrong token type"}
            )

        # 🚀 7. user_id
        user_id = payload.get("sub")

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token payload"}
            )

        # 🚀 8. 注入用户
        request.state.user = int(user_id)

        return await call_next(request)