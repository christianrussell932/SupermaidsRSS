from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Source(Base):
    """Model for social media sources (Facebook Groups, Nextdoor neighborhoods)"""
    __tablename__ = 'sources'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    url = Column(String(512), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'facebook' or 'nextdoor'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_scraped = Column(DateTime, nullable=True)
    
    # Relationships
    matches = relationship("Match", back_populates="source")
    
    def __repr__(self):
        return f"<Source(id={self.id}, name='{self.name}', type='{self.source_type}')>"


class Keyword(Base):
    """Model for keywords to monitor"""
    __tablename__ = 'keywords'
    
    id = Column(Integer, primary_key=True)
    text = Column(String(255), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    matches = relationship("Match", back_populates="keyword")
    
    def __repr__(self):
        return f"<Keyword(id={self.id}, text='{self.text}')>"


class Match(Base):
    """Model for keyword matches found in sources"""
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    keyword_id = Column(Integer, ForeignKey('keywords.id'), nullable=False)
    post_id = Column(String(255), nullable=True)  # Original post ID from the platform
    post_url = Column(String(512), nullable=False)
    post_text = Column(Text, nullable=False)
    post_author = Column(String(255), nullable=True)
    post_date = Column(DateTime, nullable=True)
    matched_text = Column(String(512), nullable=False)  # The specific text that matched
    is_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    source = relationship("Source", back_populates="matches")
    keyword = relationship("Keyword", back_populates="matches")
    
    def __repr__(self):
        return f"<Match(id={self.id}, source_id={self.source_id}, keyword_id={self.keyword_id})>"


class NotificationSetting(Base):
    """Model for notification settings"""
    __tablename__ = 'notification_settings'
    
    id = Column(Integer, primary_key=True)
    email_enabled = Column(Boolean, default=True)
    email_address = Column(String(255), nullable=True)
    slack_enabled = Column(Boolean, default=True)
    slack_webhook = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f"<NotificationSetting(id={self.id}, email_enabled={self.email_enabled}, slack_enabled={self.slack_enabled})>"
from flask_login import UserMixin

class User(Base, UserMixin):
    """Model for app users"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"

# Function to initialize the database
def init_db(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
