from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Text, DateTime, JSON, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone
import enum

Base = declarative_base()

class RaterType(enum.Enum):
    CUSTOMER = "customer"
    BUSINESS = "business"

class SenderRole(enum.Enum):
    USER = "user"
    AI = "ai"
    BUSINESS_OWNER = "business_owner" # Crucial for tracking Human Handoff!

class Customer(Base):
    __tablename__ = 'customers'
    id = Column(Integer, primary_key=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone_number = Column(String(20), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    
    # Platform Analytics
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    average_rating = Column(Float, default=5.0) # Updated via Rating system
    
    # Relationships
    orders = relationship("Order", back_populates="customer")
    given_ratings = relationship("Rating", foreign_keys='Rating.customer_id', back_populates="customer")

class Business(Base):
    __tablename__ = 'businesses' # Formerly Vendors
    id = Column(Integer, primary_key=True)
    business_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    phone_number = Column(String(20))
    password_hash = Column(String(255), nullable=False)
    
    # Premium Profile & Marketplace Discovery Info
    description = Column(Text, nullable=True)
    category = Column(String(100), index=True) 
    business_address = Column(String(255))
    logo_url = Column(String(255), nullable=True)
    banner_url = Column(String(255), nullable=True)
    brand_color = Column(String(7), default="#000000") # For customized public profiles
    
    # Financial Details
    bank_name = Column(String(100), nullable=True)
    account_number = Column(String(20), nullable=True)
    account_name = Column(String(150), nullable=True)
    
    # AI Knowledge & Settings
    knowledge_base_text = Column(Text, nullable=True) # Raw extracted text from PDFs/Excels
    is_ai_active = Column(Boolean, default=True) # Global kill switch
    
    # Integrations
    telegram_chat_id = Column(String(50), nullable=True)
    whatsapp_number = Column(String(20), nullable=True)
    
    # Analytics & Reputation
    is_verified = Column(Boolean, default=False)
    average_rating = Column(Float, default=5.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    products = relationship("Product", back_populates="business")
    orders = relationship("Order", back_populates="business")
    chat_sessions = relationship("ChatSession", back_populates="business")

class Product(Base):
    """Structured data extracted from uploaded catalogs to track exact product inquiries."""
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    is_in_stock = Column(Boolean, default=True)
    
    # Analytics
    inquiry_count = Column(Integer, default=0) # Tracks how many times AI was asked about this
    
    business = relationship("Business", back_populates="products")

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    
    # Can be a guest phone number OR a registered customer ID
    customer_phone = Column(String(20), nullable=False)
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    
    # Core Feature: Human Handoff Status
    is_ai_paused = Column(Boolean, default=False) 
    platform = Column(String(20), default="whatsapp") # whatsapp or telegram
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    business = relationship("Business", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = 'chat_messages'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'))
    
    # By tracking sender role exactly, we can generate Analytics on "AI vs Human resolution times"
    sender_role = Column(String(50)) # USER, AI, or BUSINESS_OWNER
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    session = relationship("ChatSession", back_populates="messages")

class Order(Base):
    __tablename__ = 'orders'
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'), nullable=True)
    customer_phone = Column(String(20)) # Fallback for guest checkouts
    
    items = Column(JSON) # Structured cart data
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="pending") # pending, paid, completed, cancelled
    receipt_url = Column(String(255), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    business = relationship("Business", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")

class Rating(Base):
    """Mutual rating system between Business and Customer."""
    __tablename__ = 'ratings'
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=True)
    business_id = Column(Integer, ForeignKey('businesses.id'))
    customer_id = Column(Integer, ForeignKey('customers.id'))
    
    rater_type = Column(String(20)) # CUSTOMER or BUSINESS (Who is giving the rating?)
    score = Column(Integer, nullable=False) # 1 to 5
    review_text = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    customer = relationship("Customer", back_populates="given_ratings")
