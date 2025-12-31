from fastapi import APIRouter, File, UploadFile, HTTPException
from app.pymongo_database import get_database
from app.schemas import UserModel
from datetime import datetime, timezone

radix = get_database()
user_info = radix["user_info"]
user_info.create_index([("id",1), ("mob_no",1)], unique = True)

router = APIRouter()

@router.get("/user")
def user():
    return {"data": "Radix User API's"}

@router.post("/user/creation")
async def user_create(info: UserModel, name_in_id: bool = False):
    data = user_info.find({"mob_no":info.mob_no})
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
                info.id = initials + "@radix"
            
            else:
                info.id = info.mob_no + "@radix"
            
            user_info.insert_one(info.model_dump)

            return {"status": "You are now part of Radix",
                    "id": f"{info.id}"}

        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail= f"Your account was not created due to {e}"
            )

    
        
@router.put("/user/update")
def updation(user_id: str, to_mob_no: bool = False, to_name: bool = True):
    try:
        data = user_info.find_one({"id":user_id})
        if not data:
            return {"status":"Data not found"}
        new_id = None
        if to_mob_no:
            new_id = data["mob_no"] + "@radix"
        
        elif to_name:
            new_id = data["name"].lower().replace(' ','') + "@radix"
        

        user_info.update_one(
            {"id":user_id},
            {"$set":{"id":new_id}}
        )
        return {"status":f"Your id is successfully changed to {new_id}"}
    
    except:
        raise HTTPException(
            status_code=404,
            detail=f"We were not able to change your id please try later"
        )

