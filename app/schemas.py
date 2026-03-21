from pydantic import BaseModel, Field
from datetime import datetime
from typing import List

class TransactionModel(BaseModel):
    from_id: str
    to_id: str
    transaction_id: str | None = None
    amount:float
    time: datetime | None = None
    remark: str | None = None

class TransactionModelMobNo(BaseModel):
    from_id: str
    mob_no: str
    amount: float
    remark: str | None = None
class DBUserModel(BaseModel):
    user_id: str
    hashed_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class UserModel(BaseModel):
    name: str
    mob_no: str
    password: str = Field(max_length = 30, min_length = 8)
    pin: str = Field(max_length = 4 , min_length = 4)
    amount: float | None = None
    time_of_creation: datetime | None = None
    user_id: str | None = None
    profile_photo : str | None = None

class RollBack(BaseModel):
    user_id: str
    amount: float
    transaction_id: str
    time: datetime | None = None

class PalmEmbeddingModel(BaseModel):
    user_id: str
    embedding: List[float]
    enrolled_at: datetime | None = None

class PalmIdentifyResponse(BaseModel):
    matched: bool
    user_id: str | None = None
    confidence: float

class PalmPayment(BaseModel):
    amount: float
    remark: str | None = None

class PinPayment(BaseModel):
    from_id: str
    to_id: str
    amount: float
    pin: str = Field(min_length=4, max_length=4)
    remark: str | None = None