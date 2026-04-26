import os
import socket
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# --- APP CONFIGURATION ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev_project_secret_123'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Database Configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'chat.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- EXTENSION INITIALIZATION ---
db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- DATABASE MODELS ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    room = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Presence Tracking: Use sets to prevent duplicates (Solves the 'qwerty' ghost issue)
active_users = {}

with app.app_context():
    db.create_all()

# --- ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form.get('username')
        session['room'] = request.form.get('room')
        return redirect(url_for('chat'))
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Load last 50 messages for this room
    messages = Message.query.filter_by(room=session['room'])\
                      .order_by(Message.timestamp.asc())\
                      .limit(50).all()
    
    return render_template('chat.html', 
                           username=session['username'], 
                           room=session['room'], 
                           messages=messages)

# --- SOCKET.IO EVENTS ---
@socketio.on('join')
def handle_join(data):
    username = data.get('username')
    room = data.get('room')
    join_room(room)
    
    if room not in active_users:
        active_users[room] = set()
    
    # Add to set (sets automatically ignore duplicates)
    active_users[room].add(username)
    
    emit('status', {'msg': f"{username} joined the chat."}, room=room)
    emit('presence_update', {'users': list(active_users[room])}, room=room)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    username = data['username']
    msg_content = data['message']
    
    # Save to Database
    new_msg = Message(username=username, room=room, content=msg_content)
    db.session.add(new_msg)
    db.session.commit()
    
    emit('message', {
        'username': username,
        'message': msg_content,
        'timestamp': datetime.now().strftime('%H:%M')
    }, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    username = session.get('username')
    room = session.get('room')
    
    if room in active_users and username in active_users[room]:
        active_users[room].remove(username)
        emit('status', {'msg': f"{username} has left."}, room=room)
        emit('presence_update', {'users': list(active_users[room])}, room=room)

if __name__ == '__main__':
    print("\n>>> STARTING SERVER ON PORT 5004...")
    # This will fail and show an error if port 5004 is occupied
    socketio.run(app, debug=True, port=5004)
