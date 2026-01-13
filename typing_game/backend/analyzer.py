from sqlalchemy import func, and_
from datetime import datetime, timedelta
import numpy as np
from collections import Counter, defaultdict
from models import Keystroke

class TypingAnalyzer:
    def __init__(self, db_manager):
        self.db = db_manager
        # Finger mapping for QWERTY keyboard
        self.finger_map = {
            'q': ('left', 'pinky'), 'a': ('left', 'ring'), 'z': ('left', 'middle'),
            'w': ('left', 'ring'), 's': ('left', 'middle'), 'x': ('left', 'index'),
            'e': ('left', 'middle'), 'd': ('left', 'index'), 'c': ('left', 'index'),
            'r': ('left', 'index'), 'f': ('left', 'index'), 'v': ('left', 'index'),
            't': ('left', 'index'), 'g': ('left', 'index'), 'b': ('left', 'index'),
            'y': ('right', 'index'), 'h': ('right', 'index'), 'n': ('right', 'index'),
            'u': ('right', 'index'), 'j': ('right', 'index'), 'm': ('right', 'index'),
            'i': ('right', 'middle'), 'k': ('right', 'middle'), ',': ('right', 'middle'),
            'o': ('right', 'ring'), 'l': ('right', 'ring'), '.': ('right', 'ring'),
            'p': ('right', 'pinky'), ';': ('right', 'pinky'), '/': ('right', 'pinky'),
            ' ': ('both', 'thumb')
        }
    
    def analyze_session(self, session_id, recent_only=True):
        """Comprehensive analysis of user's typing performance"""
        db_session = self.db.get_session()
        
        # Build query for keystrokes
        query = db_session.query(Keystroke).filter_by(session_id=session_id)
        
        if recent_only:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            query = query.filter(Keystroke.timestamp >= cutoff)
        
        keystrokes = query.all()
        db_session.close()
        
        if not keystrokes:
            return self.get_default_analysis()
        
        # Calculate metrics
        analysis = {
            'overall': self._calculate_overall_metrics(keystrokes),
            'key_level': self._analyze_key_performance(keystrokes),
            'bigram_level': self._analyze_bigram_performance(keystrokes),
            'finger_level': self._analyze_finger_performance(keystrokes),
            'hand_level': self._analyze_hand_performance(keystrokes),
            'temporal_patterns': self._analyze_temporal_patterns(keystrokes)
        }
        
        # Generate actionable insights
        analysis['insights'] = self._generate_insights(analysis)
        analysis['focus_areas'] = self._identify_focus_areas(analysis)
        analysis['mastered_items'] = self._identify_mastered_items(analysis)
        
        # --- MACHINE LEARNING SECTION ---
        # 1. Predictive Modeling (Regression)
        analysis['ml_prediction'] = self._predict_future_performance(keystrokes)
        
        return analysis
    
    def _calculate_overall_metrics(self, keystrokes):
        """Calculate overall typing metrics"""
        total = len(keystrokes)
        correct = sum(1 for k in keystrokes if k.is_correct)
        errors = total - correct
        accuracy = correct / total if total > 0 else 0
        
        # Calculate speed (excluding first keystroke)
        times = [k.time_since_last for k in keystrokes[1:] if k.time_since_last]
        avg_speed = np.mean(times) if times else 0
        wpm = (60 / (avg_speed * 5)) if avg_speed > 0 else 0  # 5 chars per word avg
        
        # Error consistency
        error_sequences = []
        current_seq = 0
        for k in keystrokes:
            if not k.is_correct:
                current_seq += 1
            else:
                if current_seq > 0:
                    error_sequences.append(current_seq)
                    current_seq = 0
        
        return {
            'total_keystrokes': total,
            'accuracy': accuracy,
            'error_rate': errors / total if total > 0 else 0,
            'avg_speed_ms': avg_speed * 1000 if avg_speed else 0,
            'wpm': wpm,
            'max_error_streak': max(error_sequences) if error_sequences else 0,
            'common_error_patterns': self._find_error_patterns(keystrokes)
        }
    
    def _analyze_key_performance(self, keystrokes):
        """Analyze performance for individual keys"""
        key_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'times': []})
        
        for k in keystrokes:
            if k.key_pressed.lower() == k.expected_key.lower():
                key = k.expected_key.lower()
            else:
                key = k.expected_key.lower()  # Track expected key even if wrong
            
            stats = key_stats[key]
            stats['total'] += 1
            if k.is_correct:
                stats['correct'] += 1
            if k.time_since_last:
                stats['times'].append(k.time_since_last)
        
        # Calculate metrics per key
        results = {}
        for key, stats in key_stats.items():
            if stats['total'] >= 3:  # Only analyze keys with enough samples
                accuracy = stats['correct'] / stats['total']
                avg_time = np.mean(stats['times']) * 1000 if stats['times'] else 0
                std_time = np.std(stats['times']) * 1000 if len(stats['times']) > 1 else 0
                
                results[key] = {
                    'accuracy': accuracy,
                    'error_rate': 1 - accuracy,
                    'avg_time_ms': avg_time,
                    'time_consistency': std_time,
                    'sample_size': stats['total']
                }
        
        return dict(sorted(results.items(), 
                          key=lambda x: x[1]['error_rate'], 
                          reverse=True)[:10])  # Top 10 problematic keys
    
    def _analyze_bigram_performance(self, keystrokes):
        """Analyze performance for character pairs"""
        bigram_stats = defaultdict(lambda: {'total': 0, 'times': []})
        
        # Group keystrokes by context
        for i in range(1, len(keystrokes)):
            prev = keystrokes[i-1]
            curr = keystrokes[i]
            
            if prev.is_correct and curr.is_correct:
                bigram = f"{prev.expected_key.lower()}{curr.expected_key.lower()}"
                if curr.time_since_last:
                    bigram_stats[bigram]['total'] += 1
                    bigram_stats[bigram]['times'].append(curr.time_since_last)
        
        # Calculate metrics per bigram
        results = {}
        for bigram, stats in bigram_stats.items():
            if stats['total'] >= 5:  # Only analyze bigrams with enough samples
                avg_time = np.mean(stats['times']) * 1000
                percentile_90 = np.percentile(stats['times'], 90) * 1000
                
                results[bigram] = {
                    'avg_transition_time_ms': avg_time,
                    'slow_transition_threshold': percentile_90,
                    'sample_size': stats['total']
                }
        
        return dict(sorted(results.items(), 
                          key=lambda x: x[1]['avg_transition_time_ms'], 
                          reverse=True)[:15])  # Top 15 slow bigrams
    
    def _analyze_finger_performance(self, keystrokes):
        """Analyze performance by finger"""
        finger_stats = defaultdict(lambda: {'total': 0, 'correct': 0, 'times': []})
        
        for k in keystrokes:
            finger_info = self.finger_map.get(k.expected_key.lower(), ('unknown', 'unknown'))
            finger = finger_info[1]
            
            stats = finger_stats[finger]
            stats['total'] += 1
            if k.is_correct:
                stats['correct'] += 1
            if k.time_since_last:
                stats['times'].append(k.time_since_last)
        
        results = {}
        for finger, stats in finger_stats.items():
            if stats['total'] >= 5:
                accuracy = stats['correct'] / stats['total']
                avg_time = np.mean(stats['times']) * 1000 if stats['times'] else 0
                
                results[finger] = {
                    'accuracy': accuracy,
                    'avg_time_ms': avg_time,
                    'sample_size': stats['total']
                }
        
        return results
    
    def _analyze_hand_performance(self, keystrokes):
        """Analyze performance by hand"""
        hand_stats = {'left': {'total': 0, 'correct': 0, 'times': []},
                     'right': {'total': 0, 'correct': 0, 'times': []},
                     'both': {'total': 0, 'correct': 0, 'times': []}}
        
        for k in keystrokes:
            hand = self.finger_map.get(k.expected_key.lower(), ('unknown', 'unknown'))[0]
            
            stats = hand_stats.get(hand)
            if stats:
                stats['total'] += 1
                if k.is_correct:
                    stats['correct'] += 1
                if k.time_since_last:
                    stats['times'].append(k.time_since_last)

        results = {}
        for hand, stats in hand_stats.items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total']
                avg_time = np.mean(stats['times']) * 1000 if stats['times'] else 0
                
                results[hand] = {
                    'accuracy': accuracy,
                    'avg_time_ms': avg_time,
                    'sample_size': stats['total']
                }
        
        return results
    
    def _analyze_temporal_patterns(self, keystrokes):
        """Analyze how performance changes over time"""
        if len(keystrokes) < 10:
            return {}
        
        # Split into chunks
        chunk_size = max(10, len(keystrokes) // 5)
        chunks = []
        
        for i in range(0, len(keystrokes), chunk_size):
            chunk = keystrokes[i:i+chunk_size]
            if len(chunk) >= 5:
                accuracy = sum(1 for k in chunk if k.is_correct) / len(chunk)
                times = [k.time_since_last for k in chunk[1:] if k.time_since_last]
                avg_speed = np.mean(times) * 1000 if times else 0
                chunks.append({
                    'chunk_index': i // chunk_size,
                    'accuracy': accuracy,
                    'avg_speed_ms': avg_speed,
                    'error_rate': 1 - accuracy
                })
        
        # Calculate trends
        if len(chunks) >= 2:
            accuracy_trend = chunks[-1]['accuracy'] - chunks[0]['accuracy']
            speed_trend = chunks[-1]['avg_speed_ms'] - chunks[0]['avg_speed_ms']
        else:
            accuracy_trend = speed_trend = 0
        
        return {
            'chunks': chunks,
            'accuracy_trend': accuracy_trend,
            'speed_trend': speed_trend,
            'fatigue_indicator': self._detect_fatigue(chunks)
        }

    def _predict_future_performance(self, keystrokes):
        """
        Uses Linear Regression (ML) to predict future WPM based on current session trend.
        """
        if len(keystrokes) < 30:
            return None
            
        # Create time series of speeds (WPM)
        window_size = 10
        speeds = []
        indices = []
        
        # Calculate rolling WPM
        for i in range(0, len(keystrokes) - window_size, 5):
            chunk = keystrokes[i:i+window_size]
            times = [k.time_since_last for k in chunk if k.time_since_last]
            if times:
                avg_time = np.mean(times)
                # WPM = (60 / (avg_time_per_char * 5 chars/word))
                wpm = (60 / (avg_time * 5)) if avg_time > 0 else 0
                speeds.append(wpm)
                indices.append(i)
                
        if len(speeds) < 3:
            return None
            
        try:
            # Simple Linear Regression (Polyfit degree 1)
            # y = mx + c
            slope, intercept = np.polyfit(indices, speeds, 1)
            
            # Predict WPM for the next 50 keystrokes
            next_index = indices[-1] + 50
            predicted_wpm = (slope * next_index) + intercept
            
            return {
                'current_wpm_trend': round(slope * 100, 2), # Change per 100 keystrokes
                'predicted_next_wpm': round(predicted_wpm, 1),
                'confidence': 'High' if len(speeds) > 10 else 'Low'
            }
        except Exception:
            return None

    def _extract_biometric_features(self, keystrokes):
        """
        Extracts a 'Keystroke Dynamics' vector for User Verification (Classification).
        This vector would be the input (X) for a Random Forest or Neural Network.
        """
        # 1. Flight Time Latency (H-H)
        flight_times = [k.time_since_last for k in keystrokes if k.time_since_last]
        
        # 2. Key-Specific Latencies (e.g., how fast they type 'th')
        # This creates a unique 'fingerprint' of the user
        return {
            'mean_flight': np.mean(flight_times) if flight_times else 0,
            'std_flight': np.std(flight_times) if flight_times else 0,
            'median_flight': np.median(flight_times) if flight_times else 0
        }
    
    def _detect_fatigue(self, chunks):
        """Detect signs of fatigue"""
        if len(chunks) < 3:
            return 'insufficient_data'
        
        last_three = chunks[-3:]
        accuracy_declining = all(
            last_three[i]['accuracy'] > last_three[i+1]['accuracy'] 
            for i in range(len(last_three)-1)
        )
        speed_declining = all(
            last_three[i]['avg_speed_ms'] < last_three[i+1]['avg_speed_ms']
            for i in range(len(last_three)-1)
        )
        
        if accuracy_declining and speed_declining:
            return 'high_fatigue'
        elif accuracy_declining or speed_declining:
            return 'moderate_fatigue'
        else:
            return 'no_fatigue'
    
    def _find_error_patterns(self, keystrokes):
        """Identify common error patterns"""
        error_contexts = []
        
        for i in range(1, len(keystrokes)):
            if not keystrokes[i].is_correct:
                # Look at previous 2 characters
                context = ""
                if i >= 2:
                    context += keystrokes[i-2].expected_key.lower()
                if i >= 1:
                    context += keystrokes[i-1].expected_key.lower()
                context += keystrokes[i].expected_key.lower()
                error_contexts.append(context)
        
        # Count occurrences
        counter = Counter(error_contexts)
        return [{'pattern': pat, 'count': cnt} 
                for pat, cnt in counter.most_common(5) if cnt >= 2]
    
    def _generate_insights(self, analysis):
        """Generate actionable insights from analysis"""
        insights = []
        
        # Key-level insights
        for key, stats in analysis['key_level'].items():
            if stats['error_rate'] > 0.3:
                insights.append(f"Key '{key}' has high error rate ({stats['error_rate']:.1%})")
            if stats['avg_time_ms'] > 300:
                insights.append(f"Key '{key}' is consistently slow ({stats['avg_time_ms']:.0f}ms avg)")
        
        # Bigram insights
        for bigram, stats in analysis['bigram_level'].items():
            if stats['avg_transition_time_ms'] > 400:
                insights.append(f"Transition '{bigram}' is slow ({stats['avg_transition_time_ms']:.0f}ms)")
        
        # Finger insights
        worst_finger = min(analysis['finger_level'].items(), 
                          key=lambda x: x[1]['accuracy'])
        best_finger = max(analysis['finger_level'].items(), 
                         key=lambda x: x[1]['accuracy'])
        
        if worst_finger[1]['accuracy'] < 0.85:
            insights.append(f"{worst_finger[0].title()} finger has low accuracy ({worst_finger[1]['accuracy']:.1%})")
        
        # Hand imbalance
        if 'left' in analysis['hand_level'] and 'right' in analysis['hand_level']:
            left_acc = analysis['hand_level']['left']['accuracy']
            right_acc = analysis['hand_level']['right']['accuracy']
            if abs(left_acc - right_acc) > 0.15:
                insights.append(f"Hand imbalance: Left {left_acc:.1%} vs Right {right_acc:.1%}")
        
        # Temporal insights
        if analysis['temporal_patterns'].get('fatigue_indicator') in ['moderate_fatigue', 'high_fatigue']:
            insights.append("Performance declining - consider taking a break")
        
        return insights[:5]  # Top 5 insights
    
    def _identify_focus_areas(self, analysis):
        """Identify what the user should focus on"""
        focus_areas = []
        
        # High-error keys
        high_error_keys = [(k, s) for k, s in analysis['key_level'].items() 
                          if s['error_rate'] > 0.2]
        if high_error_keys:
            focus_areas.append({
                'type': 'high_error_keys',
                'items': [k for k, _ in high_error_keys[:3]],
                'priority': 'high'
            })
        
        # Slow bigrams
        slow_bigrams = [(b, s) for b, s in analysis['bigram_level'].items() 
                       if s['avg_transition_time_ms'] > 350]
        if slow_bigrams:
            focus_areas.append({
                'type': 'slow_transitions',
                'items': [b for b, _ in slow_bigrams[:3]],
                'priority': 'medium'
            })
        
        # Weak fingers
        weak_fingers = [(f, s) for f, s in analysis['finger_level'].items() 
                       if s['accuracy'] < 0.9]
        if weak_fingers:
            focus_areas.append({
                'type': 'weak_fingers',
                'items': [f for f, _ in weak_fingers],
                'priority': 'medium'
            })
        
        return focus_areas
    
    def _identify_mastered_items(self, analysis):
        """Identify what the user has mastered"""
        mastered = []
        
        # High-accuracy keys
        accurate_keys = [(k, s) for k, s in analysis['key_level'].items() 
                        if s['error_rate'] < 0.05 and s['sample_size'] >= 10]
        if accurate_keys:
            mastered.append({
                'type': 'mastered_keys',
                'items': [k for k, _ in accurate_keys[:5]]
            })
        
        # Fast bigrams
        fast_bigrams = [(b, s) for b, s in analysis['bigram_level'].items() 
                       if s['avg_transition_time_ms'] < 200 and s['sample_size'] >= 10]
        if fast_bigrams:
            mastered.append({
                'type': 'fast_transitions',
                'items': [b for b, _ in fast_bigrams[:5]]
            })
        
        return mastered
    
    def get_default_analysis(self):
        """Return default analysis for new users"""
        return {
            'overall': {
                'total_keystrokes': 0,
                'accuracy': 0,
                'error_rate': 0,
                'avg_speed_ms': 0,
                'wpm': 0,
                'max_error_streak': 0,
                'common_error_patterns': []
            },
            'key_level': {},
            'bigram_level': {},
            'finger_level': {},
            'hand_level': {},
            'temporal_patterns': {},
            'insights': ["Welcome! Start typing to get personalized feedback."],
            'focus_areas': [],
            'mastered_items': []
        }

    def build_analysis_snapshot(self, analysis_result):
        """Convert a session analysis into a persistent user snapshot"""
        overall = analysis_result.get('overall', {})
        accuracy = overall.get('accuracy', 0)
        wpm = overall.get('wpm', 0)
        
        # Determine Tier (The "Coach" Logic)
        if accuracy < 0.90:
            tier = 'foundational'
        elif accuracy < 0.96:
            tier = 'controlled'
        else:
            tier = 'performance'
            
        # Extract weaknesses
        weak_keys = [k for k, v in analysis_result.get('key_level', {}).items() 
                    if v['error_rate'] > 0.1] # >10% error rate
                    
        weak_fingers = [f for f, v in analysis_result.get('finger_level', {}).items() 
                       if v['accuracy'] < 0.9]
                       
        slow_bigrams = [b for b, v in analysis_result.get('bigram_level', {}).items() 
                       if v['avg_transition_time_ms'] > 300]
        
        return {
            'tier': tier,
            'weak_keys': weak_keys[:5],      # Top 5
            'weak_fingers': weak_fingers,
            'slow_bigrams': slow_bigrams[:5], # Top 5
            'accuracy_avg': accuracy * 100,
            'wpm_avg': wpm
        }