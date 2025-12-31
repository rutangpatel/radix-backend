from pydantic import BaseModel
from datetime import datetime

class TransactionModel(BaseModel):
    from_id: str
    to_id: str
    amount:float
    time: datetime | None = None
    remark: str | None = None
    

class UserModel(BaseModel):
    name: str
    mob_no: str
    bank: str
    time_of_creation: datetime | None = None
    id: str | None = None