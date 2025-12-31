from fastapi import FastAPI
from app.payment import router as payment_router
from app.users import router as users_router

app = FastAPI()

app.include_router(payment_router, tags = ["Payment"])
app.include_router(users_router, tags = ["Users"])

@app.get("/")
def root():
    return {"data":"Welcome to Radix API"}