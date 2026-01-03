from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor
from security import hash_password, verify_password, create_access_token
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])

class VendorSignup(BaseModel):
    email: str
    password: str
    business_name: str

@router.post("/signup")
def signup(vendor: VendorSignup, db: Session = Depends(get_db)):
    # Check if vendor already exists
    existing = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_vendor = Vendor(
        email=vendor.email,
        business_name=vendor.business_name,
        password_hash=hash_password(vendor.password)
    )
    db.add(new_vendor)
    db.commit()
    db.refresh(new_vendor)
    return {"message": "Vendor created successfully", "vendor_id": new_vendor.id}

@router.post("/login")
def login(vendor: VendorSignup, db: Session = Depends(get_db)):
    db_vendor = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if not db_vendor or not verify_password(vendor.password, db_vendor.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(data={"sub": db_vendor.email, "id": db_vendor.id})
    return {"access_token": token, "token_type": "bearer", "business_name": db_vendor.business_name}
