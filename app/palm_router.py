from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from app.pymongo_database import get_database
from app.schemas import PalmEmbeddingModel, PalmIdentifyResponse, PalmPayment, TransactionModel
from app.palm import get_embedding, get_averaged_embedding
from app.payment import paying
from app.auth import get_current_user
from app.users import check_user
from datetime import datetime, timezone

router = APIRouter()

radix = get_database()
palm_embeddings = radix["palm_embeddings"]


# ── Enroll ──────────────────────────────────────────────────
@router.post("/enroll")
async def enroll_palm(
    user_id: str,
    images: list[UploadFile] = File(...)
):
    try:
        # Validate user exists
        user_id = user_id.strip().lower()
        print(user_id)
        user = check_user(user_id = user_id)
        if not user:
            raise HTTPException(
                status_code = 404,
                detail = "User not found. Register first via /users/signup"
            )

        # Check already enrolled
        existing = palm_embeddings.find_one({"user_id": user_id})
        if existing:
            raise HTTPException(
                status_code = 409,
                detail = "Palm already enrolled. Use /palm/re-enroll to update"
            )

        # Read all uploaded images
        image_bytes_list = []
        for img in images:
            data = await img.read()
            image_bytes_list.append(data)

        # Get averaged embedding (3-5 images recommended)
        avg_embedding = get_averaged_embedding(image_bytes_list)  # (1, 512)

        # Store in MongoDB
        doc = PalmEmbeddingModel(
            user_id = user_id,
            embedding = avg_embedding.flatten().tolist(),  # list of 512 floats
            enrolled_at = datetime.now(timezone.utc)
        )
        palm_embeddings.insert_one(doc.model_dump())

        return {
            "status": f"Palm enrolled successfully for {user_id}",
            "images_used": len(image_bytes_list)
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Enrollment failed: {str(e)}")


# ── Identify ────────────────────────────────────────────────
@router.post("/identify", response_model = PalmIdentifyResponse)
async def identify_palm(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
        query_embedding = get_embedding(image_bytes)  # (1, 512)

        result = search_palm(query_embedding)
        return result

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Identification failed: {str(e)}")


# ── Pay ─────────────────────────────────────────────────────
@router.post("/pay")
async def palm_pay(
    to_id: str = Form(...),
    amount: float = Form(...),
    remark: str = Form(None),   # optional
    image: UploadFile = File(...)
):
    try:
        image_bytes = await image.read()
        query_embedding = get_embedding(image_bytes)
        result = search_palm(query_embedding)

        if not result["matched"]:
            raise HTTPException(
                status_code=401,
                detail=f"Palm not recognised. Confidence: {result['confidence']:.2f}"
            )

        from_id = result["user_id"]

        transaction = TransactionModel(
            from_id=from_id,
            to_id=to_id,
            amount=amount,
            remark=remark
        )
        return await paying(transaction)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Palm payment failed: {str(e)}")

@router.get("/status")
async def palm_status(user_id: str):
    """
    Returns whether a user has an enrolled palm embedding.
    Called by the frontend on SecurityView mount.
    """
    user_id = user_id.strip().lower()
    existing = palm_embeddings.find_one({"user_id": user_id})
    return {"enrolled": existing is not None}

@router.put("/re-enroll")
async def re_enroll_palm(
    user_id: str = Form(...),
    images: list[UploadFile] = File(...)
):
    try:
        user_id = user_id.strip().lower()
        user = radix["user_info"].find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code = 404, detail = "User not found")

        image_bytes_list = [await img.read() for img in images]
        avg_embedding = get_averaged_embedding(image_bytes_list)

        palm_embeddings.update_one(
            {"user_id": user_id},
            {"$set": {
                "embedding": avg_embedding.flatten().tolist(),
                "enrolled_at": datetime.now(timezone.utc)
            }},
            upsert = True   # creates doc if somehow missing
        )

        return {"status": f"Palm re-enrolled successfully for {user_id}"}

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code = 500, detail = f"Re-enrollment failed: {str(e)}")


# ── Helper: MongoDB vector search ───────────────────────────
def search_palm(query_embedding) -> dict:
    THRESHOLD = 0.40

    # Debug — check embedding shape coming in
    print(f">>> query shape: {query_embedding.shape}")
    print(f">>> first 5 values: {query_embedding.flatten()[:5]}")
    print(f">>> total enrolled docs: {palm_embeddings.count_documents({})}")

    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "queryVector": query_embedding.flatten().tolist(),
                "path": "embedding",
                "numCandidates": 100,
                "limit": 1
            }
        },
        {
            "$project": {
                "user_id": 1,
                "score": {"$meta": "vectorSearchScore"},
                "_id": 0
            }
        }
    ]

    results = list(palm_embeddings.aggregate(pipeline))

    if not results:
        return {"matched": False, "user_id": None, "confidence": 0.0}

    top = results[0]
    confidence = top["score"]
    matched = confidence >= THRESHOLD

    return {
        "matched": matched,
        "user_id": top["user_id"] if matched else None,
        "confidence": float(confidence)
    }