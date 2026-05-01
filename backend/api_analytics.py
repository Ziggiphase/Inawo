from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from database import get_db
from models import Business, ChatSession, ChatMessage, Order, Product, SenderRole
from dependencies import get_current_business

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_metrics(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Fetches the comprehensive metrics required for the Next.js Dashboard.
    """
    # 1. AI Performance & Handoffs
    total_sessions = db.query(ChatSession).filter(ChatSession.business_id == current_business.id).count()
    
    # How many sessions had at least one message from the business owner? (Human Handoff)
    handoff_sessions = db.query(ChatSession).join(ChatMessage).filter(
        ChatSession.business_id == current_business.id,
        ChatMessage.sender_role == SenderRole.BUSINESS_OWNER.value
    ).distinct().count()
    
    handoff_rate = round((handoff_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # 2. Sales & Revenue
    total_orders = db.query(Order).filter(Order.business_id == current_business.id, Order.status == "paid").count()
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.business_id == current_business.id, 
        Order.status == "paid"
    ).scalar() or 0.0
    
    conversion_rate = round((total_orders / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # 3. Product Analytics (Top 3 inquired products)
    top_products = db.query(Product).filter(
        Product.business_id == current_business.id
    ).order_by(Product.inquiry_count.desc()).limit(3).all()
    
    product_stats = [{"name": p.name, "inquiries": p.inquiry_count} for p in top_products]

    return {
        "ai_performance": {
            "total_conversations": total_sessions,
            "handoff_rate": f"{handoff_rate}%",
            "active_chats": db.query(ChatSession).filter(ChatSession.business_id == current_business.id, ChatSession.is_ai_paused == False).count()
        },
        "sales": {
            "total_revenue": total_revenue,
            "conversion_rate": f"{conversion_rate}%",
            "orders_processed": total_orders
        },
        "reputation": {
            "average_rating": current_business.average_rating
        },
        "product_insights": product_stats,
        "is_ai_active": current_business.is_ai_active
    }

@router.post("/toggle-ai")
async def toggle_ai_status(
    active: bool,
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    The master kill-switch for human handoff. When active is False, 
    webhooks will route messages to the dashboard instead of LangGraph.
    """
    current_business.is_ai_active = active
    db.commit()
    return {"status": "success", "is_ai_active": current_business.is_ai_active}

@router.get("/orders")
async def get_business_orders(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """Fetches all orders for the business."""
    orders = db.query(Order).filter(Order.business_id == current_business.id).order_by(Order.created_at.desc()).all()
    return [{
        "id": o.id,
        "customer_phone": o.customer_phone,
        "items": o.items,
        "total_amount": o.total_amount,
        "status": o.status,
        "created_at": o.created_at
    } for o in orders]

@router.get("/chats")
async def get_business_chats(
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """Fetches active chat sessions."""
    sessions = db.query(ChatSession).filter(ChatSession.business_id == current_business.id).order_by(ChatSession.created_at.desc()).all()
    return [{
        "id": s.id,
        "customer_phone": s.customer_phone,
        "is_ai_paused": s.is_ai_paused
    } for s in sessions]
