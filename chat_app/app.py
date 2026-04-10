from flask import Flask, render_template, request
from flask_socketio import SocketIO, send

app = Flask(__name__, template_folder='templates')
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

# Handle messages
@socketio.on('message')
def handle_message(msg):
    print("Message:", msg)
    send(msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002)
    import os
print(os.listdir('templates'))