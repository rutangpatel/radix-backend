from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.payment import router as payment_router
from app.users import router as users_router
from app.auth import router as auth_router
from app.face_router import router as face_router
from app.rate_limiter import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
@limiter.limit("5/minute")
def root(request: Request):
    return {"data":"Welcome to Radix API"}