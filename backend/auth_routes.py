from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Business
from security import hash_password, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

router = APIRouter(tags=["Authentication"])

class BusinessSignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str
    category: str = "General"
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None

class BusinessLoginSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(business: BusinessSignupSchema, db: Session = Depends(get_db)):
    existing = db.query(Business).filter(Business.email == business.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_business = Business(
        email=business.email,
        business_name=business.business_name,
        phone_number=business.phone_number,
        category=business.category,
        bank_name=business.bank_name,
        account_number=business.account_number,
        account_name=business.account_name,
        password_hash=hash_password(business.password)
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return {"status": "success", "business_id": new_business.id}

@router.post("/login")
def login(login_data: BusinessLoginSchema, db: Session = Depends(get_db)):
    db_business = db.query(Business).filter(Business.email == login_data.email).first()
    
    if not db_business or not verify_password(login_data.password, db_business.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token(data={"sub": db_business.email, "id": db_business.id})
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "business_name": db_business.business_name,
        "business_id": db_business.id
    }
