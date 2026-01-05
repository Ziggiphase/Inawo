from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor
from security import hash_password, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(tags=["Authentication"])

# Expanded schema to prevent 422 Unprocessable Content errors
class VendorSignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str
    category: str = "General"
    bank_name: str = None
    account_number: str = None
    account_name: str = None

@router.post("/signup")
def signup(vendor: VendorSignupSchema, db: Session = Depends(get_db)):
    # 1. Check if vendor exists
    existing = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Create new vendor with all fields
    new_vendor = Vendor(
        email=vendor.email,
        business_name=vendor.business_name,
        phone_number=vendor.phone_number,
        category=vendor.category,
        bank_name=vendor.bank_name,
        account_number=vendor.account_number,
        account_name=vendor.account_name,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    return {"status": "success", "vendor_id": new_vendor.id}

@router.post("/login")
def login(vendor: VendorSignupSchema, db: Session = Depends(get_db)):
    # Note: Login only needs email/password, but we use the same schema for simplicity
    db_vendor = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if not db_vendor or not verify_password(vendor.password, db_vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate JWT Token
    token = create_access_token(data={"sub": db_vendor.email, "id": db_vendor.id})
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "business_name": db_vendor.business_name,
        "vendor_id": db_vendor.id
    }
