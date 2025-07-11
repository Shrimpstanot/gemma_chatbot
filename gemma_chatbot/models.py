# models.py
from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import relationship 
from database import Base  

# -- Our three models --
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_admin = Column(Boolean, default=False, nullable=False)

    # This relationship links a User to their Conversations
    # 'back_populates' creates a two-way link
    # 'cascade' means if a user is deleted, their conversations are also deleted
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    
class Conversation(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="New Chat")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # This relationship links a Conversation back to its User
    user = relationship("User", back_populates="conversations")
    
    # This relationship links a Conversation to its Messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False) # Use Text for long messages
    file_path = Column(String, nullable=True) # Optional path to an uploaded file
    created_at = Column(DateTime, server_default=func.now())

    # This relationship links a Message back to its Conversation
    conversation = relationship("Conversation", back_populates="messages")