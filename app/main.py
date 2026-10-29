
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Visitor Management System API",
    description="Backend API for managing visitors and appointments.",
    version="1.0.0",
)

# Allow the React frontend to communicate with this backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
