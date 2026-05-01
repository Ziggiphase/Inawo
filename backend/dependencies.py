from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from database import get_db
from models import Business
from security import decode_access_token

# oauth2_scheme points to the login logic to allow FastAPI's built-in 'Authorize' button to work
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_business(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Business:
    """
    Middleware dependency to protect routes. 
    It extracts the JWT, validates it, and returns the Business object.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Decode the token using our security helper
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # 2. Extract the business ID from the payload
    raw_id = payload.get("id")
    if raw_id is None:
        raise credentials_exception
        
    try:
        # Cast to integer to match the SQLAlchemy Column type in models.py
        business_id = int(raw_id)
    except (ValueError, TypeError):
        raise credentials_exception
        
    # 3. Verify the business exists in the database
    business = db.query(Business).filter(Business.id == business_id).first()
    if business is None:
        raise credentials_exception
        
    return business
