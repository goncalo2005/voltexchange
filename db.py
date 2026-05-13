import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DATABASE_HOST"), 
        database=os.environ.get("DATABASE_NAME"), 
        user=os.environ.get("DATABASE_USER"), 
        password=os.environ.get("DATABASE_PASSWORD"),
        sslmode='require'
    )

def login(email, password):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Usa crypt para validar o hash da password [cite: 10, 30]
                cur.execute("SELECT UtilizadorID, Nome, Email, Saldo FROM Utilizadores WHERE Email = %s AND PasswordHash = crypt(%s, PasswordHash)", [email, password])
                return cur.fetchone()
    except Exception as e:
        print(f"Erro no login: {e}")
        return None

def add_reading(data, user_id):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Procurar o ContadorID do utilizador
                cur.execute("SELECT ContadorID FROM Contadores WHERE UtilizadorID = %s LIMIT 1", [user_id])
                contador = cur.fetchone()
                if not contador: return None

                # 2. Inserir respeitando as colunas exatas: ContadorID, DataHora, KWh_Leitura, DadosAudit [cite: 41]
                # Criamos um JSON com temperatura/voltagem para o DadosAudit 
                audit_data = {
                    "temperatura": data.get("temperatura", 25),
                    "voltagem": data.get("voltagem", 230),
                    "erro_codigo": data.get("erro_codigo")
                }
                
                import json
                cur.execute("""
                    INSERT INTO Leituras (ContadorID, DataHora, KWh_Leitura, DadosAudit) 
                    VALUES (%s, %s, %s, %s) RETURNING *
                """, [
                    contador['contadorid'], 
                    datetime.now(), 
                    data.get('valor_kwh'), 
                    json.dumps(audit_data)
                ])
                conn.commit()
                return cur.fetchone()
    except Exception as e:
        print(f"Erro SQL: {e}")
        return None

def get_anomalies():
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Query JSONB otimizada pedida pelo professor [cite: 32, 27]
                cur.execute("""
                    SELECT c.NumeroSerie, l.* FROM Leituras l
                    JOIN Contadores c ON l.ContadorID = c.ContadorID
                    WHERE (l.DadosAudit->>'temperatura')::int > 80 
                       OR l.DadosAudit->>'erro_codigo' IS NOT NULL
                """)
                return cur.fetchall()
    except Exception as e:
        return []

def run_matching_engine():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("CALL sp_MatchingEngine()")
                conn.commit()
                return True
    except Exception as e:
        return False
