from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
import bcrypt
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from starlette import status
from app.pymongo_database import get_database
from app.schemas import Token, DBUserModel
from dotenv import load_dotenv
import os
from pymongo import IndexModel, ASCENDING

router = APIRouter()
load_dotenv()

radix = get_database()
user_info = radix['user_info']
blacklist = radix["token_blacklist"]
blacklist_index1 = IndexModel([("token", ASCENDING)], unique=True)
blacklist_index2 = IndexModel([("exp", ASCENDING)], expireAfterSeconds=0)
blacklist.create_indexes([blacklist_index1, blacklist_index2])  

secret_key = os.getenv("SECRET_KEY")
algorithm = "HS256"

oauth2_bearer = OAuth2PasswordBearer(tokenUrl = "v1/auth/token")

def blacklist_token(token: str, exp: datetime):
    blacklist.insert_one({"token": token, "exp": exp})

def create_access_token(user_id, name, expiry_delta):
    encode = {"sub": user_id, "name": name}
    expires = datetime.now(timezone.utc) + expiry_delta
    encode.update({"exp": expires})
    return jwt.encode(encode, algorithm = algorithm, key = secret_key)


def authenticate_user(username: str, password: str):
    user = user_info.find_one({"user_id": username})
    if not user:
        return False
    if not bcrypt.checkpw(password.encode('utf-8'), user["password"].encode("utf-8")):
        return False
    return user

async def get_current_user(token:str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, secret_key, algorithms = [algorithm])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code = 401,
                detail = "Could not Validate User"
            )
        
        if blacklist.find_one({"token": token}):
            raise HTTPException(status_code = 401, detail = "Token has been invalidated. Please login again")

        return {"user_id": user_id, "token": token, "exp": payload.get("exp")}
    except JWTError:
        raise HTTPException(
            status_code = 401,
            detail = "Could not Validate User"
        )


@router.post("/token") 
async def login_for_access(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    user = authenticate_user(username = form_data.username, password = form_data.password)
    if not user:
        raise HTTPException(
            status_code = 401,
            detail = "Unauthorized user, check your password or username. Sign Up if not already"
        )
    token = create_access_token(user["user_id"], name = user["name"], expiry_delta = timedelta(hours = 12))
    return {"access_token": token, "token_type": "bearer"}


    



