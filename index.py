from flask import Flask, jsonify, request
from flask_cors import CORS
import db
import jwt
import os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'volt_secret')

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header: return jsonify({"error": "Token em falta"}), 401
        try:
            token = auth_header.split(" ")[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
        except:
            return jsonify({"error": "Token inválido"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    user = db.login(data.get('email'), data.get('password'))
    if user:
        token = jwt.encode({
            'user_id': user['utilizadorid'],
            'exp': datetime.utcnow() + timedelta(hours=2)
        }, app.config['SECRET_KEY'])
        return jsonify({"token": token, "user": user['nome']})
    return jsonify({"error": "Credenciais inválidas"}), 401

@app.route('/api/meters/readings', methods=['POST'])
@auth_required
def add_reading():
    res = db.add_reading(request.get_json(), request.user_id)
    return jsonify(res), 201 if res else (jsonify({"error": "Falha na inserção"}), 400)

@app.route('/api/admin/anomalies', methods=['GET'])
@auth_required
def get_anomalies():
    return jsonify(db.get_anomalies())

@app.route('/api/market/match', methods=['POST'])
def force_match():
    if db.run_matching_engine():
        return jsonify({"message": "Matching executado"})
    return jsonify({"error": "Falha no motor"}), 500

@app.route('/api/market/buy', methods=['POST'])
@auth_required
def buy_energy():
    data = request.get_json()
    oferta_id = data.get('oferta_id')
    comprador_id = request.user_id # Usa o ID do utilizador autenticado pelo Token

    if db.execute_direct_purchase(oferta_id, comprador_id):
        return jsonify({"message": "Compra efetuada com sucesso (ACID)"}), 200
    return jsonify({"error": "Falha na transação. Verifique o saldo ou estado da oferta."}), 400

if __name__ == "__main__":
    app.run(debug=True)
