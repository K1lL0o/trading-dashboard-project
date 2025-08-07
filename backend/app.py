# In backend/app.py (Diagnostic Version)

from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def index():
    # If this works, you will see this message when you visit your Render URL.
    return "<h1>Minimal Flask App is Running! The core setup is correct.</h1>"

# This block is needed if you ever switch the start command to 'python app.py'
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)