from fastapi import FastAPI
from app.payment import router as payment_router
from app.users import router as users_router
from app.auth import router as auth_router

app = FastAPI()

app.include_router(payment_router, prefix = "/transaction", tags = ["Payment"])
app.include_router(users_router, prefix = "/users", tags = ["Users"])
app.include_router(auth_router, prefix = "/auth", tags = ["Authentication"])

@app.get("/")
def root():
    return {"data":"Welcome to Radix API"}