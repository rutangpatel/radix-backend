from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from app.pymongo_database import get_database
from pymongo import IndexModel, ASCENDING
from app.schemas import UserModel
from app.auth import get_current_user
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from datetime import datetime, timezone
from app.profile_photo import imagekit
import secrets

radix = get_database()
user_info = radix["user_info"]
index1 = IndexModel([("user_id", ASCENDING)], unique = True)
index2 = IndexModel([("mob_no", ASCENDING)], unique = True)
user_info.create_indexes([index1, index2])

router = APIRouter()
bcrypt_context = CryptContext(schemes = ["bcrypt"], deprecated = "auto")

@router.get("/")
def user():
    return {"data": "Radix User API's"}

@router.get("/balance")
def get_balance(user_id: str):
    try:
        data = user_info.find_one({"user_id":user_id})
        if not data:
            raise HTTPException(
                status_code = 404,
                detail = "You are not registered with us"
            )
        current_amount = data["amount"]

        return {"amount":current_amount}
    except:
        raise HTTPException(
            status_code = 404,
            detail = "Their was something wrong try again later"
        )

@router.get("/authenticated")
async def user(user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code = 401,
            detail = "Not Authenticated"
        )
    return {"user":user}

@router.post("/signup")
async def user_create(info: UserModel, name_in_id: bool = False):
    data = user_info.find_one({"mob_no":info.mob_no})
    if data is not None:
        raise HTTPException(
            status_code = 409,
            detail = "Your mobile number is already registered with us"
        )
    else:
        try:
            info.time_of_creation = datetime.now(timezone.utc)

            if name_in_id:
                initials = info.name.lower().replace(" ","")
                info.user_id = initials + "@radix"
            
            else:
                info.user_id = info.mob_no + "@radix"
            
            info.amount = secrets.randbelow(50000) + 50000
            hashed_password = bcrypt_context.hash(info.password)
            info.password = hashed_password
            user_info.insert_one(info.model_dump())

            return {"status": "You are now part of Radix",
                    "user_id": f"{info.user_id}",
                    "amount": f"{info.amount}"}

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail= f"Your account was not created due to {e}"
            )

    
@router.put("/profile_photo")
async def upload_photo(user_id:str, image : UploadFile = File(...)):
        try:
            image_data = await image.read()
            data = user_info.find_one({"user_id":user_id})
            if data:
                name = data["name"]
            response = imagekit.files.upload(
                file = image_data,
                file_name = name+".jpg"
            )
            user_info.update_one(
                {"user_id":data["user_id"]},
                {"$set":{"profile_photo":response.url}}
            )
            return {"status":"Your profile photo is successfully uploaded"}
        except:
            raise HTTPException(
                status_code = 404,
                detail = f"Their was something wrong"
            )
        
@router.put("/update")
def updation(user_id: str, to_mob_no: bool = False, to_name: bool = True):
    try:
        data = user_info.find_one({"user_id":user_id})
        if not data:
            return {"status":"Data not found"}
        new_id = None
        if to_mob_no:
            new_id = data["mob_no"] + "@radix"
        
        elif to_name:
            new_id = data["name"].lower().replace(' ','') + "@radix"
        

        user_info.update_one(
            {"user_id":user_id},
            {"$set":{"user_id":new_id}}
        )
        return {"status":f"Your id is successfully changed to {new_id}"}
    
    except:
        raise HTTPException(
            status_code=404,
            detail=f"We were not able to change your id please try later"
        )

@router.delete("/delete")
async def deletion(user_id:str):
    try:
        user_info.delete_one({"user_id":user_id})
        return {"status":"Your id was deleted successfully"}
    except:
        raise HTTPException(
            status_code = 404,
            detail = "Try after sometime"
        )
    

async def amount_change(user_id: str, amount:float, minus: bool):
    data = user_info.find_one({"user_id":user_id})
    if minus:
        remaining_balance = data["amount"] - amount
        user_info.update_one(
            {"user_id": user_id},
            {"$set" : {"amount": remaining_balance}}
        )
    else:
        remaining_balance = data["amount"] + amount
        user_info.update_one(
            {"user_id": user_id},
            {"$set" : {"amount": remaining_balance}}
        )
    return True
    
def check_user(user_id: str):
    data = user_info.find_one({"user_id":user_id})
    if data:
        return True
    else:
        return False
    
def find_user_mob_no(mob_no: str):
    data = user_info.find_one({"mob_no": mob_no})
    if data:
        return data["user_id"]
    else:
        return False