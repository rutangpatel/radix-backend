from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Form, Request
from app.pymongo_database import get_database
from pymongo import IndexModel, ASCENDING
from app.schemas import UserModel, ForgotPassword
from app.auth import get_current_user, blacklist_token
from passlib.context import CryptContext
from app.rate_limiter import limiter
from datetime import datetime, timezone
from app.profile_photo import imagekit, delete
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

@limiter.limit("15/minute")
@router.get("/balance")
def get_balance(request : Request, user: dict = Depends(get_current_user)):
    try:
        return fetch_balance(user_id = user["user_id"])
    except HTTPException as he:
        raise he
    except:
        raise HTTPException(
            status_code = 404,
            detail = "Their was something wrong try again later"
        )

@limiter.limit("3/minute")
@router.get("/authenticated")
async def user(request: Request, user: dict = Depends(get_current_user)):
    if user is None:
        raise HTTPException(
            status_code = 401,
            detail = "Not Authenticated"
        )
    return {"user":user}

@limiter.limit("65/minute")
@router.get("/photo")
def get_user_profie(request: Request, user_id: str):
    return get_user_profile_data(user_id)


@limiter.limit("3/minute")
@router.post("/signup")
async def user_create(request: Request, info: UserModel, name_in_id: bool = False):
    data = user_info.find_one({"mob_no": info.mob_no})
    if data is not None:
        raise HTTPException(
            status_code=409,
            detail="Your mobile number is already registered with us"
        )
    else:
        try:
            # Validate PIN is digits only
            if not info.pin.isdigit():
                raise HTTPException(
                    status_code=400,
                    detail="PIN must contain only digits"
                )

            info.time_of_creation = datetime.now(timezone.utc)

            if name_in_id:
                initials = info.name.lower().replace(" ", "")
                info.user_id = initials + "@radix"
            else:
                info.user_id = info.mob_no + "@radix"

            info.amount = secrets.randbelow(50000) + 50000

            # Hash password
            hashed_password = bcrypt_context.hash(info.password)
            info.password = hashed_password

            # Hash PIN
            hashed_pin = bcrypt_context.hash(info.pin)
            info.pin = hashed_pin

            user_info.insert_one(info.model_dump())

            return {
                "status": "You are now part of Radix",
                "user_id": f"{info.user_id}",
                "amount": f"{info.amount}"
            }

        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Your account was not created due to {e}"
            )

@limiter.limit("5/minute")  
@router.put("/profile_photo")
async def upload_photo(request: Request, user : dict = Depends(get_current_user), image : UploadFile = File(...)):
        try:
            user_id = user["user_id"]
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
                {"$set":{"profile_photo":response.url, "profile_photo_id": response.file_id}}
            )
            return {"status":"Your profile photo is successfully uploaded"}
        except:
            raise HTTPException(
                status_code = 404,
                detail = f"Their was something wrong"
            )
        
@limiter.limit("5/minute")
@router.put("/update")
def updation(request: Request, user: dict = Depends(get_current_user), to_mob_no: bool = False, to_name: bool = True):
    try:
        user_id = user["user_id"]
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
        blacklist_token(user["token"], datetime.fromtimestamp(user["exp"], tz = timezone.utc))
        return {"status":f"Your id is successfully changed to {new_id}. Please login again"}
    
    except:
        raise HTTPException(
            status_code=404,
            detail=f"We were not able to change your id please try later"
        )

@limiter.limit("5/minute")
@router.delete("/delete")
async def deletion(request: Request, user : dict = Depends(get_current_user)):
    from app.face_router import delete_embeddings
    try:
        user_id = user["user_id"]
        data = user_info.find_one({"user_id": user_id})
        if not data:
            raise HTTPException(
                status_code = 404,
                detail = "User not found"
            )
        file_id = data.get("profile_photo_id")
        if file_id:
            delete(file_id)
        delete_embeddings(user_id = user_id)
        blacklist_token(user["token"], datetime.fromtimestamp(user["exp"], tz = timezone.utc))
        user_info.delete_one({"user_id":user_id})
        return {"status":"Your account was deleted successfully"}
    except HTTPException as he:
        raise he
    except:
        raise HTTPException(
            status_code = 404,
            detail = "Try after sometime"
        )

@limiter.limit("3/minute")
@router.post("/forgot-password")
async def forgot_password(request: Request, info: ForgotPassword):
    try:
        if not info.new_password.isalnum():
            raise HTTPException(status_code=400, detail="Invalid password format")

        user = user_info.find_one({"user_id": info.user_id, "mob_no": info.mob_no})
        if not user:
            raise HTTPException(status_code=404, detail="No account found with this user_id and mobile number")

        hashed_password = bcrypt_context.hash(info.new_password)
        user_info.update_one(
            {"user_id": info.user_id},
            {
                "$set": {"password": hashed_password}
            }
        )
        return {"status": "Password updated successfully. Please login again."}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")


@limiter.limit("5/minute")
@router.put("/forgot-pin")
async def forgot_pin(request: Request, user: dict = Depends(get_current_user), 
                     new_pin: str = Form(...), 
                     old_pin: str = Form(None),      
                     password: str = Form(None)):    
    try:
        user_id = user["user_id"]
        
        if not old_pin and not password:
            raise HTTPException(status_code=400, detail="Provide either old PIN or password")

        db_user = user_info.find_one({"user_id": user_id})
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        if old_pin:
            if not bcrypt_context.verify(old_pin, db_user["pin"]):
                raise HTTPException(status_code=401, detail="Old PIN is incorrect")
        elif password:
            if not bcrypt_context.verify(password, db_user["password"]):
                raise HTTPException(status_code=401, detail="Incorrect password")

        if not new_pin.isdigit() or len(new_pin) != 4:
            raise HTTPException(status_code=400, detail="New PIN must be exactly 4 digits")

        hashed_new_pin = bcrypt_context.hash(new_pin)
        user_info.update_one({"user_id": user_id}, {"$set": {"pin": hashed_new_pin}})
        return {"status": "PIN updated successfully"}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update PIN: {str(e)}")


def verify_pin(user_id: str, pin: str) -> bool:
    user = user_info.find_one({"user_id": user_id})
    if not user:
        return False
    stored_pin = user.get("pin")
    if not stored_pin:
        return False
    return bcrypt_context.verify(pin, stored_pin)
    

async def amount_change(user_id: str, amount:float, minus: bool):
    delta = -amount if minus else amount
    query = {"user_id": user_id}
    if minus:
        query["amount"] = {"$gte": amount}
    result = user_info.update_one(
        query,
        {"$inc": {"amount": delta}}
    )
    return result.modified_count == 1
    
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
    
def rollback_amount(user_id: str, amount: float):
    try:
        result = user_info.update_one(
            {"user_id": user_id},
            {"$inc": {"amount": amount}}
        )
        return result.modified_count == 1
    except:
        return False

def get_next_transaction_id() -> str:
    result = radix["counters"].find_one_and_update(
        {"_id": "transaction_id"},
        {"$inc": {"seq": 1}},        
        return_document=True         
    )
    return str(result["seq"])        

def fetch_balance(user_id: str):
    data = user_info.find_one({"user_id": user_id})
    if not data:
        raise HTTPException(
            status_code = 404, 
            detail = "User not registered with us"
        )
    return {"amount": data["amount"]}

def get_user_profile_data(user_id: str):
    result = user_info.find_one({"user_id": user_id})
    if result is None:
        return None
    else:
        if result["profile_photo"]:
            return result["profile_photo"]
        else:
            return result["name"]