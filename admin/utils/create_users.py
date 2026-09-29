from db import SessionLocal
from models.user import User
from utils.security import hash_password

db = SessionLocal()

users = [
    {"username": "", "password": ""},
]

for u in users:
    user = User(
        username=u["username"],
        password=hash_password(u["password"])
    )
    db.add(user)

db.commit()
db.close()

print("users created")