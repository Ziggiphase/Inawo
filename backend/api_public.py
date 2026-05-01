from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Business, Product

router = APIRouter(prefix="/api/public", tags=["Public Marketplace"])

@router.get("/business/{business_id}")
async def get_business_profile(business_id: int, db: Session = Depends(get_db)):
    """
    Public endpoint for customers to view a business's storefront and catalog.
    """
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    products = db.query(Product).filter(Product.business_id == business_id).all()
    
    return {
        "id": business.id,
        "name": business.business_name,
        "category": business.category,
        "rating": business.average_rating,
        "description": "Welcome to our official Inawo storefront. You can view our products below or chat with our 24/7 AI agent on WhatsApp.",
        "brand_color": business.brand_color or "#111111",
        "products": [{"id": p.id, "name": p.name, "price": p.price, "description": p.description} for p in products]
    }

@router.get("/businesses")
async def get_all_businesses(db: Session = Depends(get_db)):
    """
    Public endpoint to list all businesses for the explore marketplace.
    """
    businesses = db.query(Business).all()
    return [
        {
            "id": b.id,
            "name": b.business_name,
            "category": b.category,
            "rating": b.average_rating,
            "brand_color": b.brand_color or "#111111"
        } for b in businesses
    ]
