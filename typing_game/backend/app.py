from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sys
import os
import webbrowser
from threading import Timer
from database import DatabaseManager
from analyzer import TypingAnalyzer
from text_generator import AdaptiveTextGenerator
from game_engine import GameEngine

app = Flask(__name__, static_folder='../frontend')
# Determine the correct path for frontend files (works for source and EXE)
if getattr(sys, 'frozen', False):
    FRONTEND_FOLDER = os.path.join(sys._MEIPASS, 'frontend')
else:
    FRONTEND_FOLDER = '../frontend'

app = Flask(__name__, static_folder=FRONTEND_FOLDER)
app.secret_key = os.environ.get('SECRET_KEY', 'dev_secret_key_change_in_prod')
CORS(app, supports_credentials=True)

# Initialize components  
db_manager = DatabaseManager()
analyzer = TypingAnalyzer(db_manager)
text_generator = AdaptiveTextGenerator()
game_engine = GameEngine(db_manager, analyzer, text_generator)

@app.route('/api/start_session', methods=['POST'])
def start_session():
    user_id = session.get('user_id')

    session_id = db_manager.create_user_session()
    game_data = game_engine.start_session(session_id, user_id)
    session['active_session_id'] = session_id
    return jsonify(game_data)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing credentials'}), 400
        
    user_id = db_manager.create_user(data['username'], data['password'])
    if not user_id:
        return jsonify({'error': 'Username already exists'}), 409
        
    session['user_id'] = user_id
    return jsonify({'status': 'ok', 'user_id': user_id})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Missing credentials'}), 400
        
    user_id = db_manager.verify_user(data['username'], data['password'])
    if not user_id:
        return jsonify({'error': 'Invalid credentials'}), 401
        
    session['user_id'] = user_id
    progress = db_manager.get_user_progress(user_id)
    return jsonify({
        'status': 'ok',
        'user_id': user_id,
        'level': progress.current_level if progress else 1,
        'total_score': progress.total_score if progress else 0
    })

@app.route('/api/set_mode', methods=['POST'])
def set_mode():
    data = request.get_json()
    learn_mode = bool(data.get('learn_mode', True))
    active_session_id = session.get('active_session_id')

    # FIX: Only apply mode to the current user's active session

    # Auto-recover session if missing (e.g. server restart)
    if active_session_id and active_session_id not in game_engine.active_sessions:
        user_id = session.get('user_id')
        game_engine.start_session(active_session_id, user_id)

    if active_session_id and active_session_id in game_engine.active_sessions:
        game_engine.active_sessions[active_session_id]['learn_mode'] = learn_mode
    else:
        return jsonify({'error': 'No active session found'}), 404

    return jsonify({'status': 'ok', 'learn_mode': learn_mode})

@app.route('/api/save_progress', methods=['POST'])
def save_progress():
    user_id = session.get('user_id'),
    if not user_id:
        return jsonify({'error': 'Login required'}), 401

    game_engine.force_save_user(user_id)
    return jsonify({'message': 'Progress saved successfully'})

@app.route('/api/keystroke', methods=['POST'])
def process_keystroke():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400
        
    session_id = data.get('session_id')
    key = data.get('key')
    timestamp = data.get('timestamp')
    
    if not session_id or not key:
        return jsonify({'error': 'Missing session_id or key'}), 400
    
    # FIX: Prevent IDOR by verifying session ownership
    active_id = session.get('active_session_id') 
    if not active_id or str(active_id) != str(session_id):
        return jsonify({'error': 'Unauthorized access to session'}), 403

    result = game_engine.process_keystroke(session_id, key, timestamp)
    
    # Auto-recover session if it was lost (e.g. server restart)
    if result.get('error') == 'Session not found':
        user_id = session.get('user_id')
        game_engine.start_session(session_id, user_id)
        result = game_engine.process_keystroke(session_id, key, timestamp)

    # Log completion to verify the "Frontend decides WHEN" flow
    if result.get('is_complete'):
        app.logger.info(f"Session {session_id} completed text. Waiting for frontend to fetch new text.")

    return jsonify(result)

@app.route('/api/stats/<string:session_id>')
def get_stats(session_id):
    active_id = session.get('active_session_id')
    if not active_id or str(active_id) != str(session_id):
        return jsonify({'error': 'Unauthorized'}), 403
    stats = game_engine._get_session_stats(session_id)
    return jsonify(stats)

@app.route('/api/analysis/<string:session_id>')
def get_analysis(session_id):
    active_id = session.get('active_session_id')
    if not active_id or str(active_id) != str(session_id):
        return jsonify({'error': 'Unauthorized'}), 403
    analysis = game_engine.get_analysis(session_id)
    return jsonify(analysis)

@app.route('/api/new_text/<string:session_id>')
def get_new_text(session_id):
    # FIX: Verify ownership before generating text
    active_id = session.get('active_session_id')
    if not active_id or str(active_id) != str(session_id):
        return jsonify({'error': 'Unauthorized'}), 403

    # Auto-recover session if missing from memory but valid in cookie
    if session_id not in game_engine.active_sessions:
        user_id = session.get('user_id')
        game_engine.start_session(session_id, user_id)

    if session_id in game_engine.active_sessions:
        app.logger.info(f"Frontend requested new text for session {session_id}")
        game_engine.generate_new_text(session_id)
        state = game_engine.active_sessions[session_id]
        return jsonify({'text': state['current_text']})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/api/history/<string:session_id>')
def get_history(session_id):
    active_id = session.get('active_session_id')
    if not active_id or str(active_id) != str(session_id):
        return jsonify({'error': 'Unauthorized'}), 403
    keystrokes = db_manager.get_keystroke_history(session_id, limit=100)
    history = [{
        'key': k.key_pressed,
        'expected': k.expected_key,
        'correct': k.is_correct,
        'time': k.time_since_last,
        'timestamp': k.timestamp.isoformat()
    } for k in keystrokes]
    return jsonify(history)

@app.route('/')
def serve_index():
    return send_from_directory('../frontend', 'index.html')
    return send_from_directory(FRONTEND_FOLDER, 'index.html')

@app.route('/login')
def serve_login():
    return send_from_directory('../frontend', 'login.html')
    return send_from_directory(FRONTEND_FOLDER, 'login.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend', path)
    return send_from_directory(FRONTEND_FOLDER, path)

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)

    def open_browser():
        webbrowser.open('http://127.0.0.1:5000/')

    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        Timer(1.5, open_browser).start()

    app.run(debug=False, port=5000)