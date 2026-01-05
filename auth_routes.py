from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor
from security import hash_password, verify_password, create_access_token
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(tags=["Authentication"])

# Schema for Signup (All fields required)
class VendorSignupSchema(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    business_name: str
    phone_number: str
    category: str = "General"
    bank_name: str = None
    account_number: str = None
    account_name: str = None

# NEW: Schema for Login (Only email and password)
class VendorLoginSchema(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(vendor: VendorSignupSchema, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
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
def login(login_data: VendorLoginSchema, db: Session = Depends(get_db)): # Updated to use LoginSchema
    db_vendor = db.query(Vendor).filter(Vendor.email == login_data.email).first()
    
    # Verify user exists and password matches
    if not db_vendor or not verify_password(login_data.password, db_vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate JWT Token
    token = create_access_token(data={"sub": db_vendor.email, "id": db_vendor.id})
    return {
        "access_token": token, 
        "token_type": "bearer", 
        "business_name": db_vendor.business_name,
        "vendor_id": db_vendor.id
    }
