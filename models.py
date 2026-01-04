from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

class Vendor(Base):
    __tablename__ = 'vendors'
    id = Column(Integer, primary_key=True)
    business_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    phone_number = Column(String(20)) # Critical for Nigerian commerce
    password_hash = Column(String(200), nullable=False)
    
    # Professional Profile
    category = Column(String(50)) # e.g., Fashion, Electronics, Catering
    business_address = Column(String(255))
    
    # Enhanced Bank Details for trust
    bank_name = Column(String(100))
    account_number = Column(String(20))
    account_name = Column(String(100)) # Must match business/personal name
    
    # KYC (Can be made mandatory at MVP stage)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    knowledge_base = relationship("KnowledgeBase", back_populates="vendor", uselist=False)
    sales = relationship("Sale", back_populates="vendor")
    knowledge_base_text = Column(Text, nullable=True)

class KnowledgeBase(Base):
    __tablename__ = 'knowledge_bases'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    content = Column(Text)  # This is where the PDF/Excel text lives
    vendor = relationship("Vendor", back_populates="knowledge_base")

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(String, primary_key=True) # Thread_ID (Telegram Chat ID)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    is_manual_mode = Column(Boolean, default=False) # <--- The "AI Awareness" flag
    customer_name = Column(String(100))

class Sale(Base):
    __tablename__ = 'sales'
    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey('vendors.id'))
    amount = Column(Float)
    customer_name = Column(String(100))
    receipt_url = Column(String(255)) # Link to the uploaded image
    status = Column(String(20), default="Pending") # Pending, Confirmed, Rejected
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    vendor = relationship("Vendor", back_populates="sales")
