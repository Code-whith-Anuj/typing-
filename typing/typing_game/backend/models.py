from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, backref
import json

Base = declarative_base()

class UserSession(Base):
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    total_words = Column(Integer, default=0)
    total_characters = Column(Integer, default=0)
    total_errors = Column(Integer, default=0)
    total_time_seconds = Column(Float, default=0.0)
    current_level = Column(Integer, default=1)
    current_score = Column(Integer, default=0)
    highest_streak = Column(Integer, default=0)
    unlocked_levels = Column(JSON, default=lambda: [1])  # JSON array of unlocked levels

class Keystroke(Base):
    __tablename__ = 'keystrokes'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    key_pressed = Column(String(1), nullable=False)
    expected_key = Column(String(1), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    time_since_last = Column(Float)  # Seconds since last keystroke
    word_index = Column(Integer)
    character_index = Column(Integer)
    context = Column(String(10))  # Previous 2 chars + current char
    hand_used = Column(String(10))  # 'left', 'right', or 'both'
    finger_used = Column(String(10))  # Which finger was used

class PerformanceMetrics(Base):
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    metric_date = Column(DateTime, default=datetime.utcnow)
    metric_type = Column(String(50), nullable=False)  # 'key_accuracy', 'bigram_speed', etc.
    metric_name = Column(String(10), nullable=False)  # e.g., 'e', 'er', 'th'
    metric_value = Column(Float, nullable=False)
    sample_size = Column(Integer, default=0)

class GameState(Base):
    __tablename__ = 'game_states'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)
    state_type = Column(String(50), nullable=False)  # 'focus_areas', 'mastered_items', 'difficulty_profile'
    state_data = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProgress(Base):
    __tablename__ = 'user_progress'
    
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    current_level = Column(Integer, default=1)
    total_score = Column(Integer, default=0)
    max_wpm = Column(Float, default=0.0)
    last_login = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref=backref("progress", uselist=False))

class UserAnalysis(Base):
    __tablename__ = 'user_analysis'
    
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    tier = Column(String(20), default='foundation')
    weak_keys = Column(JSON, default=list)
    weak_fingers = Column(JSON, default=list)
    slow_bigrams = Column(JSON, default=list)
    accuracy_avg = Column(Float, default=0.0)
    wpm_avg = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", backref=backref("analysis", uselist=False))