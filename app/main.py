
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models
from app.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables that do not exist yet.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Visitor Management System API",
    description="Backend API for managing visitors and appointments.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/")
def home():
    return {
        "message": "Visitor Management System API is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Visitor Management System",
    }
