from fastapi import HTTPException
from app.pymongo_database import get_database
from app.schemas import RollBack
from app.users import rollback_amount


radix = get_database()
rollback = radix["rollback_transaction"]



async def rollbackput(info: RollBack):
    try:
        rollback.insert_one(info.model_dump())
        rollback_amount(user_id = info.user_id, amount = info.amount)
        return {"status": f"We have refunded {info.amount} to {info.user_id} for {info.transaction_id}"}
    except:
        raise HTTPException(
            status_code = 400,
            detail = "Please try after sometime"
        )


    