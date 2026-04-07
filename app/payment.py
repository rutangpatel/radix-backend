from fastapi import APIRouter, HTTPException, Request, Depends
from app.schemas import TransactionModel, TransactionModelMobNo, RollBack, PinPayment
from datetime import datetime, timedelta, timezone
from app.pymongo_database import get_database
from pymongo import IndexModel, ASCENDING
from app.users import fetch_balance, amount_change, check_user, find_user_mob_no, verify_pin, get_next_transaction_id, get_user_profie, get_current_user
from app.rollback import rollbackput
from app.rate_limiter import limiter

router = APIRouter()

radix = get_database()
transactions = radix["transactions"]
index1 = IndexModel([("user_id")])
index2 = IndexModel([("transaction_id", ASCENDING)], unique = True)
category_index = transactions.create_indexes([index1, index2])


@router.get("/")
def home():
    return {"data":"Radix Transaction API's"}

@limiter.limit("15/minute")
@router.get("/history")
async def history(request : Request, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)
    start_dt = datetime(now.year, now.month, 1)
    end_dt = now
    ist_offset = timedelta(hours = 5, minutes = 30)
    
    records = transactions.find(
        {
            "$and":[
                {"time" : {"$gte":start_dt, "$lt":end_dt}},
                {
                    "$or":[
                        {"from_id":user_id},
                        {"to_id":user_id}
                    ]
                }
            ]

        }
    ).sort("time",-1)

    data = []
    for r in records:
        remark = r.get("remark")
        if remark is None:
            data.append(
                {
                    "transaction_id": r["transaction_id"],
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "amount": r["amount"],
                    "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M"),
                    "profile_photo" : get_user_profie(r["from_id"] if r["from_id"] != user_id else r["to_id"])
                }
            )
        else:
            data.append({
                "transaction_id": r["transaction_id"],
                "from_id": r["from_id"],
                "to_id": r["to_id"],
                "amount": r["amount"],
                "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M"),
                "remark": remark,
                "profile_photo" : get_user_profie(r["from_id"] if r["from_id"] != user_id else r["to_id"])
            })
    return data

@limiter.limit("15/minute")
@router.get("/check_activity")
async def check_activity(request: Request, user: dict = Depends(get_current_user)):
    user_id = user["user_id"]
    now = datetime.now(timezone.utc)
    start_dt = datetime(now.year, now.month, 1)
    end_dt = now
    ist_offset = timedelta(hours = 5, minutes = 30)

    records = transactions.find(
        {
            "$and": [
                {"time":{"$gte": start_dt, "$lt": end_dt}},
                {"$or": [
                    {"from_id": user_id},
                    {"to_id": user_id}
                ]}
            ]
        }
    ).limit(3).sort("time", -1)
    data = []
    for r in records:
        remark = r.get("remark")
        if remark is None:
            data.append(
                {
                    "transaction_id": r["transaction_id"],
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "amount": r["amount"],
                    "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M"),
                    "profile_photo" : get_user_profie(r["from_id"] if r["from_id"] != user_id else r["to_id"])
                }
            )
        else:
            data.append({
                "transaction_id": r["transaction_id"],
                "from_id": r["from_id"],
                "to_id": r["to_id"],
                "amount": r["amount"],
                "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M"),
                "remark": remark,
                "profile_photo" : get_user_profie(r["from_id"] if r["from_id"] != user_id else r["to_id"])
            })
    return data

@limiter.limit("3/30 seconds")
@router.post("/payment")
async def paying_pin(request: Request, info: PinPayment, user: dict = Depends(get_current_user)):
    try:
        from_id = user["user_id"]
        pin_valid = verify_pin(user_id=from_id, pin=info.pin)
        if not pin_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid PIN"
            )

        transaction = TransactionModel(
            from_id=from_id,
            to_id=info.to_id,
            amount=info.amount,
            remark=info.remark
        )
        return await paying(transaction)

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PIN payment failed: {str(e)}"
        )

@limiter.limit("3/30 seconds")
@router.post("/payment_using_mob_no")
async def paying_mob_no(request: Request, info: TransactionModelMobNo, user: dict = Depends(get_current_user)):
    try:
        from_id = user["user_id"]
        pin_valid = verify_pin(user_id=from_id, pin=info.pin)
        if not pin_valid:
            raise HTTPException(
                status_code=401,
                detail="Invalid PIN"
            )

        to_id_mob_no = find_user_mob_no(info.mob_no)
        if not to_id_mob_no:                          
            raise HTTPException(
                status_code=404,
                detail="No Radix account found for this mobile number"
            )
        model = TransactionModel(
            from_id = from_id,
            to_id = to_id_mob_no,
            amount = info.amount,
            remark = info.remark
        )
        return await paying(model)
    except HTTPException as e:
        raise e
    except:
        raise HTTPException(
            status_code = 404,
            detail = "Some Error has occured"
        )
    
async def paying(info: TransactionModel):
    try:
        if info.to_id == info.from_id:
            raise HTTPException(status_code=400, detail="You cannot send money to yourself")

        if not check_user(info.to_id) or not check_user(info.from_id):
            raise HTTPException(status_code=404, detail="Receiver not found")

        info.time = datetime.now(timezone.utc)
        info.transaction_id = get_next_transaction_id()

        check_1 = await amount_change(user_id=info.from_id, amount=info.amount, minus=True)
        if not check_1:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        check_2 = await amount_change(user_id=info.to_id, amount=info.amount, minus=False)
        if not check_2:
            model = RollBack(
                user_id=info.from_id,
                amount=info.amount,
                transaction_id=info.transaction_id,
                time=info.time
            )
            rollbackput(model)
            raise HTTPException(status_code=500, detail="Money deducted but not received by user")

        transactions.insert_one(info.model_dump())
        return {
            "status": f"Payment Successful to {info.to_id} for {info.amount}",
            "transaction_id": info.transaction_id
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")