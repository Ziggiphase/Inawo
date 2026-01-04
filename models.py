from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Vendor(Base):
    __tablename__ = 'vendors'
    id = Column(Integer, primary_key=True)
    business_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone_number = Column(String(20))
    password_hash = Column(String(200), nullable=False)
    
    # Professional Profile & Inventory
    category = Column(String(50)) 
    business_address = Column(String(255))
    out_of_stock_items = Column(Text, nullable=True) # New: Stored as comma-separated text
    knowledge_base_text = Column(Text, nullable=True)
    
    # Notification & Identity
    telegram_chat_id = Column(String(50), nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    orders = relationship("Order", back_populates="vendor")
    messages = relationship("ChatMessage", back_populates="vendor")

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True)
    customer_number = Column(String(20), unique=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    
    # AI Control & State
    is_ai_paused = Column(Boolean, default=False)
    customer_name = Column(String(100), nullable=True)
    delivery_address = Column(Text, nullable=True)
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    sender = Column(String(20)) 
    content = Column(Text)
    role = Column(String(20)) # 'user' or 'assistant'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    vendor = relationship("Vendor", back_populates="messages")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    customer_number = Column(String(20))
    items = Column(Text)
    amount = Column(Float)
    status = Column(String(20), default="pending") # pending, paid
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    vendor = relationship("Vendor", back_populates="orders")
