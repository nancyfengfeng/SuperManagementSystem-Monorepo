from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.index import api_router
from middlewares.auth import AuthMiddleware

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    force=True,  
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("app")

app = FastAPI()

# JWT
app.add_middleware(AuthMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)