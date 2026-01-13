from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import DatabaseError
from models import Base, UserSession, Keystroke, PerformanceMetrics, GameState, User, UserProgress, UserAnalysis
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_path='data/user_data.db'):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        
        try:
            # Attempt to connect and create tables
            Base.metadata.create_all(self.engine)
        except DatabaseError as e:
            print(f"--- DATABASE ERROR: {e} ---")
            print(f"The database file at '{self.db_path}' appears to be corrupt.")
            print("Attempting to recover by deleting the file and creating a new one.")
            
            # Dispose of the old engine's connection pool before deleting the file
            self.engine.dispose()
            
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            
            # Re-initialize and try again
            self.engine = create_engine(f'sqlite:///{self.db_path}')
            Base.metadata.create_all(self.engine)
            print("--- RECOVERY SUCCESSFUL: New database created. ---")
            
        self.Session = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.Session()
    
    def create_user_session(self):
        import uuid
        session_id = str(uuid.uuid4())
        db_session = self.get_session()
        user_session = UserSession(session_id=session_id)
        db_session.add(user_session)
        db_session.commit()
        db_session.close()
        return session_id
    
    def log_keystroke(self, session_id, key_data):
        db_session = self.get_session()
        keystroke = Keystroke(
            session_id=session_id,
            key_pressed=key_data['key_pressed'],
            expected_key=key_data['expected_key'],
            is_correct=key_data['is_correct'],
            time_since_last=key_data.get('time_since_last'),
            word_index=key_data.get('word_index'),
            character_index=key_data.get('character_index'),
            context=key_data.get('context'),
            hand_used=key_data.get('hand_used'),
            finger_used=key_data.get('finger_used')
        )
        db_session.add(keystroke)
        db_session.commit()
        db_session.close()
    
    def update_user_session(self, session_id, updates):
        db_session = self.get_session()
        session = db_session.query(UserSession).filter_by(session_id=session_id).first()
        if session:
            for key, value in updates.items():
                setattr(session, key, value)
            db_session.commit()
        db_session.close()
    
    def get_session_stats(self, session_id):
        db_session = self.get_session()
        session = db_session.query(UserSession).filter_by(session_id=session_id).first()
        db_session.close()
        return session
    
    def get_keystroke_history(self, session_id, limit=1000):
        db_session = self.get_session()
        keystrokes = db_session.query(Keystroke).filter_by(
            session_id=session_id
        ).order_by(Keystroke.timestamp.desc()).limit(limit).all()
        db_session.close()
        return keystrokes

    def create_user(self, username, password):
        db_session = self.get_session()
        try:
            if db_session.query(User).filter_by(username=username).first():
                return None  # User exists
            
            password_hash = generate_password_hash(password)
            new_user = User(username=username, password_hash=password_hash)
            db_session.add(new_user)
            db_session.flush()
            
            # Initialize progress
            progress = UserProgress(user_id=new_user.id)
            db_session.add(progress)
            
            db_session.commit()
            return new_user.id
        except Exception:
            db_session.rollback()
            return None
        finally:
            db_session.close()

    def verify_user(self, username, password):
        db_session = self.get_session()
        user = db_session.query(User).filter_by(username=username).first()
        db_session.close()
        
        if not user:
            return None
            
        if check_password_hash(user.password_hash, password):
            return user.id
        return None

    def get_user_progress(self, user_id):
        db_session = self.get_session()
        progress = db_session.query(UserProgress).filter_by(user_id=user_id).first()
        db_session.close()
        return progress

    def update_user_progress(self, user_id, score_delta=0, wpm=0, level=None):
        db_session = self.get_session()
        progress = db_session.query(UserProgress).filter_by(user_id=user_id).first()
        if progress:
            progress.total_score += score_delta
            if wpm > progress.max_wpm:
                progress.max_wpm = wpm
            if level:
                # Ensure we capture the highest level achieved
                progress.current_level = max(progress.current_level, level)
            progress.last_login = datetime.utcnow()
            db_session.commit()
        db_session.close()

    def get_user_analysis(self, user_id):
        db_session = self.get_session()
        analysis = db_session.query(UserAnalysis).filter_by(user_id=user_id).first()
        db_session.close()
        return analysis

    def update_user_analysis(self, user_id, data):
        db_session = self.get_session()
        analysis = db_session.query(UserAnalysis).filter_by(user_id=user_id).first()
        
        if not analysis:
            analysis = UserAnalysis(user_id=user_id)
            db_session.add(analysis)
        
        # Update fields
        for key, value in data.items():
            if hasattr(analysis, key):
                setattr(analysis, key, value)
        
        analysis.updated_at = datetime.utcnow()
        db_session.commit()
        db_session.close()