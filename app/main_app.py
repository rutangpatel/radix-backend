from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.payment import router as payment_router
from app.users import router as users_router
from app.auth import router as auth_router
from app.face_router import router as face_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # your Vite dev server
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payment_router, prefix = "/v2/transaction", tags = ["Payment"])
app.include_router(users_router, prefix = "/v1/users", tags = ["Users"])
app.include_router(auth_router, prefix = "/v1/auth", tags = ["Authentication"])
app.include_router(face_router, prefix = "/v1/face", tags = ["Face"])

@app.get("/")
def root():
    return {"data":"Welcome to Radix API"}