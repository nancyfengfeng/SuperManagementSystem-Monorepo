from jose import jwt, JWTError
from datetime import datetime, timedelta

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS,REFRESH_TOKEN_EXPIRE_DAYS


# =========================
# 生成 token
# =========================
def create_access_token(data: dict):
    to_encode = data.copy()

    expire = datetime.utcnow() + timedelta(
        days=ACCESS_TOKEN_EXPIRE_DAYS
    )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# =========================
# 更新 token
# =========================
def create_refresh_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# =========================
# 解析 token
# =========================
def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("✅ JWT payload:", payload)
        return payload
    except JWTError as e:
        print("❌ JWT ERROR:", str(e))  # ⭐关键
        return None
    except Exception as e:
        print("❌ UNKNOWN ERROR:", str(e))
        return None


def decode_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None