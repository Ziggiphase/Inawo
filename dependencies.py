from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor
from security import decode_access_token

# This tells FastAPI to look for the token in the 'Authorization: Bearer <token>' header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_vendor(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Decode the token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # 2. Get the vendor ID from the token payload (we stored 'id' during login)
    vendor_id: str = payload.get("id")
    if vendor_id is None:
        raise credentials_exception
        
    # 3. Verify the vendor exists in the database
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if vendor is None:
        raise credentials_exception
        
    return vendor
