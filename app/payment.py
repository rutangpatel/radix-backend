from fastapi import APIRouter, HTTPException
from app.schemas import TransactionModel
from datetime import datetime, timedelta, timezone
from app.pymongo_database import get_database
from pymongo import IndexModel, ASCENDING
from app.users import get_balance, amount_change, check_user
import uuid

router = APIRouter()

radix = get_database()
transactions = radix["transactions"]
index1 = IndexModel([("id",ASCENDING)], unique = True)
index2 = IndexModel([("mob_no",ASCENDING)], unique = True)
category_index = transactions.create_indexes([index1, index2])


@router.get("/transaction")
def home():
    return {"data":"Radix Transaction API's"}

@router.get("/transaction/history")
async def history(user_id: str, start_date : str | None = None, end_date : str | None = None):
    now = datetime.now(timezone.utc)
    if start_date is None:
        start_dt = datetime(now.year, now.month, 1)
    else:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        except:
            raise HTTPException(
                status_code = 400,
                error = "Please enter date in the valid format(yyyy-mm-dd)"
            )

    if end_date is None:
        end_dt = now
    else:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except:
            raise HTTPException(
                status_code = 400,
                error = "Please enter date in the valid format(yyyy-mm-dd)"
            )

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
                    "from_id": r["from_id"],
                    "to_id": r["to_id"],
                    "amount": r["amount"],
                    "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M")
                }
            )
        else:
            data.append({
                "from_id": r["from_id"],
                "to_id": r["to_id"],
                "amount": r["amount"],
                "time": (r["time"] + ist_offset).strftime("%d-%m-%Y %H:%M"),
                "remark": remark
            })
    return data

@router.post("/transaction/payment")
async def paying(info: TransactionModel):
    try:
        to_id_exist = await check_user(user_id = info.to_id)
        from_id_exist = await check_user(user_id = info.from_id)
        
        if to_id_exist and from_id_exist:
            
            info.time = datetime.now(timezone.utc)
            info.transaction_id = uuid.uuid4().hex

            from_balance = (await get_balance(user_id = info.from_id))["amount"] 
            if from_balance >= info.amount:
                check_1 = await amount_change(user_id = info.from_id, amount = info.amount, minus = True)
                if check_1:
                    check_2 = await amount_change(user_id = info.to_id, amount = info.amount, minus = False)  
                    if check_2:
                        transactions.insert_one(info.model_dump())
                        return {"status": f"Payment Successful to {info.to_id} for {info.amount}"}
                    else:
                        raise HTTPException(
                            status_code = 500,
                            detail = "Money was deducted but not recieved to the user"
                        )
                else:
                    raise HTTPException(
                        status_code = 500,
                        detail = "Failed To do the transaction"
                    )
                
            else:
                raise HTTPException(
                    status_code = 404,
                    detail = "You do not have enough balance"
                )
        else:
            raise HTTPException(
                status_code = 404,
                detail = "Reciever Not Found"
            )
    
    except HTTPException as he:
        raise he

    except Exception as e:
        raise HTTPException(
            status_code = 500,
            detail = f"Payment failed: {str(e)}"
        )