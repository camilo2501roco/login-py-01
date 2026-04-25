import os
from contextlib import asynccontextmanager

import dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from database.connection import connect_db, close_db
    await connect_db()
    yield
    await close_db()


app = FastAPI(
    title=os.getenv("APP_NAME", "Login Python API"),
    description="API de registro de usuarios con MongoDB Atlas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.user_routes import router as user_router

app.include_router(user_router, prefix="/api/users", tags=["Users"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Login Python API esta corriendo", "docs": "/docs"}
