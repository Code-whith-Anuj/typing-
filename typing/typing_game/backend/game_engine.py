import time
import random
from datetime import datetime

LEVEL_SCORE_STEP = 1000

class GameEngine:
    def __init__(self, db_manager, analyzer, text_generator):
        self.db = db_manager
        self.analyzer = analyzer
        self.text_generator = text_generator
        self.active_sessions = {}  # session_id -> game state
    
    def start_session(self, session_id, user_id):
        """Initialize a new game session"""
        # FIX #2: Mandatory user_id and Type Check
        user_id = int(user_id)

        if session_id not in self.active_sessions:
            # FIX #3: Load full user state from DB
            progress = self.db.get_user_progress(user_id)
            if not progress:
                raise Exception("User progress not found")

            # FIX: Load persistent analysis snapshot (The "Identity")
            user_analysis = self.db.get_user_analysis(user_id)
            
            mastered_items = []
            if user_analysis:
                # Restore state from DB
                mode = user_analysis.tier
                focus_areas = []
                
                # Reconstruct focus areas from snapshot
                if user_analysis.weak_keys:
                    focus_areas.append({'type': 'high_error_keys', 'items': user_analysis.weak_keys})
                if user_analysis.weak_fingers:
                    focus_areas.append({'type': 'weak_fingers', 'items': user_analysis.weak_fingers})
                
                print(f"✅ RESTORED USER STATE: Tier={mode}, WeakKeys={user_analysis.weak_keys}")
            else:
                # New user or no analysis yet
                print("⚠️ NO ANALYSIS FOUND, STARTING FRESH")
                mode = 'controlled'
                focus_areas = []
                
                # Create default snapshot
                self.db.update_user_analysis(user_id, {
                    'tier': 'controlled',
                    'accuracy_avg': 100.0
                })
            
            # Generate initial text
            initial_text = self.text_generator.generate_text(
                mode=mode,
                length_words=12,
                focus_areas=focus_areas,
                mastered_items=mastered_items
            )
            
            # Prepare initial analysis state from persistence
            initial_analysis = self.analyzer.get_default_analysis()
            if user_analysis:
                # Reconstruct focus areas for the frontend display
                restored_focus = []
                if user_analysis.weak_keys:
                    restored_focus.append({'type': 'high_error_keys', 'items': user_analysis.weak_keys, 'priority': 'high'})
                if user_analysis.weak_fingers:
                    restored_focus.append({'type': 'weak_fingers', 'items': user_analysis.weak_fingers, 'priority': 'medium'})
                if user_analysis.slow_bigrams:
                    restored_focus.append({'type': 'slow_transitions', 'items': user_analysis.slow_bigrams, 'priority': 'medium'})
                
                initial_analysis['focus_areas'] = restored_focus
                initial_analysis['overall']['accuracy'] = user_analysis.accuracy_avg / 100.0
                initial_analysis['overall']['wpm'] = user_analysis.wpm_avg
                initial_analysis['insights'] = ["Welcome back! We've restored your training profile."]
            
            # Initialize game state
            self.active_sessions[session_id] = {
                'current_text': initial_text,
                'user_id': user_id,
                'level': progress.current_level,
                'current_position': 0,
                'start_time': time.time(),
                'errors': 0,
                'correct_streak': 0,
                'max_streak': 0,
                'combo_multiplier': 1,
                'score': progress.total_score, # Start with total score
                'last_persisted_score': progress.total_score, # Track for delta updates
                'text_history': [],
                'tier': mode,
                'last_analysis': initial_analysis,
                'last_analysis_time': time.time(),
                'typed_chars': [],
                'current_word_index': 0,
                'current_char_index': 0
            }
            
            self.db.update_user_session(session_id, {'current_level': progress.current_level})
            
            return {
                'text': initial_text,
                'session_id': session_id,
                'position': 0,
                'stats': self._get_session_stats(session_id),
                'level': progress.current_level,
                'total_score': progress.total_score
            }
    
    def process_keystroke(self, session_id, key_pressed, timestamp=None):
        """Process a single keystroke"""
        if session_id not in self.active_sessions:
            return {'error': 'Session not found'}
        
        state = self.active_sessions[session_id]
        
        if timestamp is None:
            timestamp = time.time()
        
        # Calculate time since last keystroke
        if 'last_keystroke_time' in state:
            time_since_last = timestamp - state['last_keystroke_time']
        else:
            time_since_last = None
        
        # Get expected character
        expected_char = state['current_text'][state['current_position']] if state['current_position'] < len(state['current_text']) else ''
        
        # Determine correctness
        is_correct = (key_pressed == expected_char)
        
        # Update game state
        state['current_position'] += 1  # Always advance position to stay in sync with frontend
        
        if is_correct:
            state['correct_streak'] += 1
            state['max_streak'] = max(state['max_streak'], state['correct_streak'])
            
            # Calculate score for this keystroke
            char_score = self._calculate_char_score(time_since_last, state['combo_multiplier'])
            state['score'] += char_score
            
            # Update combo multiplier
            if state['correct_streak'] >= 10:
                state['combo_multiplier'] = min(3, state['combo_multiplier'] + 0.1)
        else:
            state['errors'] += 1
            state['correct_streak'] = 0
            state['combo_multiplier'] = max(1, state['combo_multiplier'] - 0.2)
        
        # Store keystroke data
        keystroke_data = {
            'key_pressed': key_pressed,
            'expected_key': expected_char,
            'is_correct': is_correct,
            'time_since_last': time_since_last,
            'word_index': state['current_word_index'],
            'character_index': state['current_char_index'],
            'context': self._get_context(state['current_text'], state['current_position']),
            'hand_used': self.analyzer.finger_map.get(expected_char.lower(), ('unknown', 'unknown'))[0],
            'finger_used': self.analyzer.finger_map.get(expected_char.lower(), ('unknown', 'unknown'))[1]
        }
        
        self.db.log_keystroke(session_id, keystroke_data)
        state['typed_chars'].append(keystroke_data)
        state['last_keystroke_time'] = timestamp
        
        # Update character/word indices
        if expected_char == ' ' or state['current_position'] >= len(state['current_text']):
            state['current_word_index'] += 1
            state['current_char_index'] = 0
        else:
            state['current_char_index'] += 1
        
        # Check if text is complete
        is_complete = state['current_position'] >= len(state['current_text'])
        
        new_text = None
        current_pos_for_response = state['current_position']
        
        # Update persistent user progress on completion
        if is_complete:
            self._persist_user(state, wpm=self._calculate_wpm(state))
            # Generate new text immediately for seamless play
            self._on_text_complete(session_id)
            new_text = state['current_text']

        # Update database with session stats
        self._update_session_stats(session_id)
        
        return {
            'correct': is_correct,
            'position': current_pos_for_response,
            'streak': state['correct_streak'],
            'max_streak': state['max_streak'],
            'combo_multiplier': state['combo_multiplier'],
            'score': state['score'],
            'errors': state['errors'],
            'is_complete': is_complete,
            'expected_char': expected_char,
            'time_since_last_ms': time_since_last * 1000 if time_since_last else None,
            'new_text': new_text
        }
    
    def _calculate_wpm(self, state):
        elapsed = (time.time() - state['start_time']) / 60
        return (state['current_position'] / 5) / elapsed if elapsed > 0 else 0

    def _calculate_char_score(self, time_since_last, combo_multiplier):
        """Calculate score for a correctly typed character"""
        if time_since_last is None:
            base_score = 10
        else:
            # Faster typing = higher score, but with diminishing returns
            if time_since_last < 0.05:  # 50ms
                base_score = 20
            elif time_since_last < 0.1:  # 100ms
                base_score = 15
            elif time_since_last < 0.2:  # 200ms
                base_score = 12
            elif time_since_last < 0.3:  # 300ms
                base_score = 8
            else:
                base_score = 5
        
        return int(base_score * combo_multiplier)
    
    def _get_context(self, text, position):
        """Get context (previous 2 chars + current char)"""
        start = max(0, position - 2)
        end = min(len(text), position + 1)
        return text[start:end]
    
    def _on_text_complete(self, session_id):
        """Handles text completion exactly once"""
        self.generate_new_text(session_id)

    def generate_new_text(self, session_id):
        """Generate new adaptive text"""
        state = self.active_sessions[session_id]
        
        # Safety lock to prevent double generation
        if state.get("generating"):
            return
        state["generating"] = True
        
        # Analyze recent performance
        current_time = time.time()
        
        # Update analysis at checkpoints (every 30s or after text completion)
        if current_time - state['last_analysis_time'] > 30 or len(state['typed_chars']) > 50:
            # 1. Analyze current session
            session_analysis = self.analyzer.analyze_session(session_id, recent_only=False)
            
            # 2. Build stable snapshot
            snapshot = self.analyzer.build_analysis_snapshot(session_analysis)
            
            # 3. Update persistent DB state
            self.db.update_user_analysis(state['user_id'], snapshot)
            
            # 4. Update local state
            state['tier'] = snapshot['tier']
            state['last_analysis'] = session_analysis
            state['last_analysis_time'] = current_time
            
            print(f"🔄 UPDATED ANALYSIS: Tier={snapshot['tier']}, Acc={snapshot['accuracy_avg']:.1f}%")

        # Prepare focus areas for generator
        user_analysis = self.db.get_user_analysis(state['user_id'])
        focus_areas = []
        if user_analysis and user_analysis.weak_keys:
            focus_areas.append({'type': 'high_error_keys', 'items': user_analysis.weak_keys})
        
        # Adjust length based on performance
        if user_analysis and user_analysis.wpm_avg > 60:  # Fast typist
            length = random.randint(15, 20)
        elif user_analysis and user_analysis.wpm_avg > 30:  # Medium typist
            length = random.randint(12, 18)
        else:  # Slow typist
            length = random.randint(8, 15)
        
        new_text = self.text_generator.generate_text(
            mode=state['tier'],
            length_words=length,
            focus_areas=focus_areas,
            mastered_items=[]
        )
        
        # Save old text to history
        state['text_history'].append({
            'text': state['current_text'],
            'score': state['score'],
            'errors': state['errors'],
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Reset for new text
        state['current_text'] = new_text
        state['current_position'] = 0
        state['typed_chars'] = []
        state['current_word_index'] = 0
        state['current_char_index'] = 0
        
        state["generating"] = False
    
    def _update_session_stats(self, session_id):
        """Update session statistics in database"""
        state = self.active_sessions[session_id]
        
        updates = {
            'total_words': state['current_word_index'],
            'total_characters': state['current_position'],
            'total_errors': state['errors'],
            'total_time_seconds': time.time() - state['start_time'],
            'current_score': state['score'],
            'highest_streak': state['max_streak']
        }
        
        # FIX: Level logic based on TOTAL score
        new_level = 1 + (state['score'] // LEVEL_SCORE_STEP)

        if new_level > state['level']:
            state['level'] = new_level
            updates['current_level'] = new_level
            
            # Update persistent user progress immediately
            self._persist_user(state)
        
        self.db.update_user_session(session_id, updates)
    
    def _persist_user(self, state, wpm=0):
        """Helper to save user progress with correct score delta"""
        current_total = state['score']
        last_saved = state.get('last_persisted_score', 0)
        delta = current_total - last_saved
        
        if delta > 0 or wpm > 0 or state['level'] > 0:
            self.db.update_user_progress(
                user_id=state['user_id'],
                level=state['level'],
                score_delta=delta,
                wpm=wpm
            )
            # Update the checkpoint
            state['last_persisted_score'] = current_total

    def force_save_user(self, user_id):
        """Force save user progress from active session"""
        print("🔥 FORCE SAVE CALLED FOR USER:", user_id)
        # Find active session for this user
        for session in self.active_sessions.values():
            print("SESSION USER:", session.get("user_id"))
            if session.get('user_id') == int(user_id):
                print("🔥 SAVING LEVEL:", session.get("level"))
                print("✅ MATCHED SESSION, SAVING")
                self._persist_user(session)
                return
        print("❌ NO ACTIVE SESSION FOUND")

    def _get_session_stats(self, session_id):
        """Get current session statistics"""
        if session_id in self.active_sessions:
            state = self.active_sessions[session_id]
            db_stats = self.db.get_session_stats(session_id)
            
            elapsed = time.time() - state['start_time']
            wpm = (state['current_position'] / 5) / (elapsed / 60) if elapsed > 0 else 0
            accuracy = (state['current_position'] - state['errors']) / state['current_position'] if state['current_position'] > 0 else 0
            
            return {
                'score': state['score'],
                'streak': state['correct_streak'],
                'max_streak': state['max_streak'],
                'combo_multiplier': state['combo_multiplier'],
                'errors': state['errors'],
                'wpm': wpm,
                'accuracy': accuracy,
                'level': db_stats.current_level if db_stats else 1,
                'unlocked_levels': db_stats.unlocked_levels if db_stats else [1]
            }
        return {}
    
    def get_analysis(self, session_id):
        """Get current analysis for the session"""
        if session_id in self.active_sessions:
            state = self.active_sessions[session_id]
            return state.get('last_analysis', self.analyzer.get_default_analysis())
        return self.analyzer.get_default_analysis()