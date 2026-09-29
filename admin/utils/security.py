from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 加密
def hash_password(password: str):
    return pwd_context.hash(password)

# 校验
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)