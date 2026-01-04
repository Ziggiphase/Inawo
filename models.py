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
    
    # Professional Profile
    category = Column(String(50)) 
    business_address = Column(String(255))
    
    # Bank Details
    bank_name = Column(String(100))
    account_number = Column(String(20))
    account_name = Column(String(100))
    
    # Inawo SaaS Features
    telegram_chat_id = Column(String(50), nullable=True) # For Vendor Alerts
    out_of_stock_items = Column(Text, nullable=True) # Comma-separated or bullet list
    knowledge_base_text = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    sales = relationship("Sale", back_populates="vendor")
    orders = relationship("Order", back_populates="vendor")
    messages = relationship("ChatMessage", back_populates="vendor")

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True)
    customer_number = Column(String(20), unique=True, nullable=False)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    
    # Profile & State
    customer_name = Column(String(100), nullable=True)
    delivery_address = Column(Text, nullable=True)
    is_ai_paused = Column(Boolean, default=False) # Human Take-over flag
    
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    sender = Column(String(20)) # customer number or 'AI'
    content = Column(Text)
    role = Column(String(20)) # 'user' or 'assistant'
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    vendor = relationship("Vendor", back_populates="messages")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    customer_number = Column(String(20))
    items = Column(Text) # Extracted by AI
    amount = Column(Float)
    status = Column(String(20), default="pending") # pending, paid, cancelled
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    vendor = relationship("Vendor", back_populates="orders")

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    amount = Column(Float)
    customer_name = Column(String(100))
    receipt_url = Column(String(255)) 
    status = Column(String(20), default="Pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    vendor = relationship("Vendor", back_populates="sales")
