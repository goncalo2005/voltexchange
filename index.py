from dotenv import load_dotenv
import os
load_dotenv()

from flask import Flask, jsonify, request
import db
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'volt_secret')

# Decorator para proteger rotas (exigido para o CP2)
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token: return jsonify({"error": "Token em falta"}), 401
        try:
            data = jwt.decode(token.split(" ")[1], app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
        except:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.login(data.get('email'), data.get('password'))
    if user:
        token = jwt.encode({
            'user_id': user['utilizadorid'],
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, app.config['SECRET_KEY'])
        return jsonify({"token": token, "user": user['nome']})
    return jsonify({"error": "Credenciais inválidas"}), 401

@app.route('/api/meters/readings', methods=['POST'])
@auth_required
def add_reading():
    res = db.add_reading(request.get_json(), request.user_id)
    return jsonify(res) if res else (jsonify({"error": "Falha"}), 400)

@app.route('/api/admin/anomalies', methods=['GET'])
@auth_required
def get_anomalies():
    return jsonify(db.get_anomalies())

@app.route('/api/market/match', methods=['POST'])
def force_match():
    # Endpoint obrigatório para o docente testar a lógica manual
    if db.run_matching_engine():
        return jsonify({"message": "Matching executado"})
    return jsonify({"error": "Falha no motor"}), 500

if __name__ == "__main__":
    app.run(debug=True)