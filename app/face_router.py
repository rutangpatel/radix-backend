from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from app.pymongo_database import get_database
from app.face import get_average_embeddings, get_embeddings
from app.schemas import FaceEmbeddings, FaceIdentifyResponse, TransactionModel
from app.users import check_user
from app.payment import paying
from datetime import datetime, timezone
import numpy as np
import cv2 as cv

router = APIRouter()

radix = get_database()
face_embeddings = radix["face_embeddings"]

@router.post("/enroll")
async def enrollment(user_id: str, images: list[UploadFile] = File(...)):
    try:
        user_id = user_id.strip().lower()
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

@router.post("/pay")
async def face_payment(to_id: str, amount: float, remark: str = Form(None), image: UploadFile = File(...)):
    try:
        result = await indentification(image)
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
            amount = amount,
            remark = remark
        )
        return await paying(transaction)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Face Payment Failed due to {str(e)}"
        )   

@router.get("/status")
async def status(user_id: str):
    user_id = user_id.lower().strip()
    existing = face_embeddings.find_one({"user_id": user_id})
    return {"enrolled": existing is not None}

@router.post("/identify", response_model = FaceIdentifyResponse)
async def indentification(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv.imdecode(arr, cv.IMREAD_COLOR)
        query_embedding = get_embeddings(img)

        result = search_face(query_embedding)
        return result
    
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Identification Failed due to {e}"
        )

@router.put("/reenroll")
async def reenrollment(user_id: str = Form(...), images : list[UploadFile] = File(...)):
    try:
        user_id = user_id.strip().lower()
        user = radix["user_info"].find_one({"user_id":user_id})
        if not user:
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
                "deepface_embedding": average_embeddings,
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