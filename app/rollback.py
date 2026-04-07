from fastapi import HTTPException
from app.pymongo_database import get_database
from app.schemas import RollBack
from app.users import rollback_amount


radix = get_database()
rollback = radix["rollback_transaction"]

def rollbackput(info: RollBack):
    rollback.insert_one(info.model_dump())
    success = rollback_amount(user_id=info.user_id, amount=info.amount)
    if not success:
        raise HTTPException(status_code=500, detail=f"CRITICAL: Refund failed for {info.user_id}, transaction {info.transaction_id}")
    return {"status": f"Refunded {info.amount} to {info.user_id}"}


    