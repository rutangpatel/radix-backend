from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request, Depends
from app.pymongo_database import get_database
from app.face import get_average_embeddings, get_embeddings
from app.schemas import FaceEmbeddings, FaceIdentifyResponse, TransactionModel, FacePayment
from app.users import check_user, get_current_user
from app.payment import paying
from app.rate_limiter import limiter
from datetime import datetime, timezone
import numpy as np
import cv2 as cv

router = APIRouter()

radix = get_database()
face_embeddings = radix["face_embeddings"]

@limiter.limit("5/minute")
@router.post("/enroll")
async def enrollment(request: Request, user: dict = Depends(get_current_user), images: list[UploadFile] = File(...)):
    try:
        user_id = user["user_id"]
        user = check_user(user_id)
        if not user:
            raise HTTPException(
                status_code = 404,
                detail = f"User not found"
            )

        existing = face_embeddings.find_one({"user_id": user_id})
        if existing:
            raise HTTPException(
                status_code = 409, 
                detail = "Embeddings already there"
            )
        
        image_byte_list = []
        for image in images:
            bytes = await image.read()
            arr = np.frombuffer(bytes, np.uint8)
            img = cv.imdecode(arr, cv.IMREAD_COLOR)
            if img is not None:
                image_byte_list.append(img)

        average_embeddings = get_average_embeddings(image_byte_list)
        doc = FaceEmbeddings(
            user_id = user_id,
            deepface_embeddings = average_embeddings,
            enrolled_at = datetime.now(timezone.utc)
        )
        face_embeddings.insert_one(doc.model_dump())
        return {
            "status": f"Face Enrolled Successfully for {user_id}"   
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Enrollment Failed: {str(e)}")

@limiter.limit("10/minute")
@router.post("/pay")
async def face_payment(request: Request, info: FacePayment = Depends(), image: UploadFile = File(...),  user: dict = Depends(get_current_user)):
    try:
        to_id = user["user_id"]
        result = await identify_image(image)
        if result["user_id"] is not None:
            from_id = result["user_id"]
        else:
            raise HTTPException(
                status_code = 404,
                detail = f"Face not recognised confidence = {result["confidence"]}"
            )
        transaction = TransactionModel(
            from_id = from_id,
            to_id = to_id,
            amount = info.amount,
            remark = info.remark
        )
        return await paying(transaction)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Face Payment Failed due to {str(e)}"
        )   

@limiter.limit("20/minute")
@router.get("/status")
async def status(request: Request, user : dict = Depends(get_current_user)):
    user_id = user["user_id"]
    existing = face_embeddings.find_one({"user_id": user_id})
    return {"enrolled": existing is not None}

@limiter.limit("10/minute")
@router.post("/identify", response_model = FaceIdentifyResponse)
async def indentification(request: Request,image: UploadFile = File(...)):
    try:
        return await identify_image(image)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Identification Failed due to {e}"
        )

@limiter.limit("5/minute")
@router.put("/reenroll")
async def reenrollment(request: Request, user: dict = Depends(get_current_user), images : list[UploadFile] = File(...)):
    try:
        user_id = user["user_id"]
        users = radix["user_info"].find_one({"user_id":user_id})
        if not users:
            raise HTTPException(
                status_code = 404,
                detail = f"User not found"
            )
        image_byte_list = []
        for image in images:
            bytes = await image.read()
            arr = np.frombuffer(bytes, np.uint8)
            img = cv.imdecode(arr, cv.IMREAD_COLOR)
            if img is not None:
                image_byte_list.append(img)

        average_embeddings = get_average_embeddings(image_byte_list)
        face_embeddings.update_one(
            {"user_id": user_id}, 
            {"$set": {
                "deepface_embeddings": average_embeddings,
                "enrolled_at": datetime.now(timezone.utc)
            }},
            upsert = True
        )
        return {"status": f"Face re-enrolled successfully for {user_id}"}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Re-enrollment failed: {str(e)}")


def search_face(embeddings):
    threshold = 0.8
    pipeline = [
        {
            "$vectorSearch":{
                "index": "deepface_embeddings",
                "queryVector": embeddings,
                "path":"deepface_embeddings",
                "numCandidates": 100,
                "limit":1
            }
        },
        {
            "$project":{
            "user_id": 1,
            "score": {"$meta":"vectorSearchScore"},
            "_id":0
            }
        }
    ]
    results = list(face_embeddings.aggregate(pipeline))
    if results:
        match = results[0]
        if match["score"] >= threshold:
            return {
                "user_id": match["user_id"],
                "confidence": match["score"]
            }
        else:
            return{
                "user_id": None,
                "confidence": match["score"]
            }

async def identify_image(image: UploadFile):
    image_bytes = await image.read()
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv.imdecode(arr, cv.IMREAD_COLOR)
    query_embedding = get_embeddings(img)

    result = search_face(query_embedding)
    return result

def delete_embeddings(user_id: str):
    try:
        data = face_embeddings.find_one({"user_id": user_id})

        if data is None:
            return
        else:
            result = face_embeddings.delete_one({"user_id": user_id})
            return result.deleted_count > 0
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code = 404,
            detail = "Try after sometime"
        )