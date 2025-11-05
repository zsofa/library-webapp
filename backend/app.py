from flask import Flask, jsonify
from flask_cors import CORS

# Flask app példány
app = Flask(__name__)
CORS(app)  # engedi, hogy a frontend más portról hívja

# Egyszerű teszt endpoint, hogy él-e a backend
@app.get("/api/health")
def health():
    return jsonify({"status": "ok"}), 200


# csak közvetlen futtatáskor induljon el
if __name__ == "__main__":
    app.run(debug=True)
