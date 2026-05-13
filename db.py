import os
import psycopg2
import json
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
                # O PostgreSQL devolve nomes de colunas em minúsculas por padrão no RealDictCursor
                cur.execute("SELECT utilizadorid, nome, email, saldo FROM Utilizadores WHERE Email = %s AND PasswordHash = crypt(%s, PasswordHash)", [email, password])
                return cur.fetchone()
    except Exception as e:
        print(f"Erro no login: {e}")
        return None

def add_reading(data, user_id):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Procurar o ContadorID associado ao UtilizadorID 
                cur.execute("SELECT contadorid FROM Contadores WHERE utilizadorid = %s LIMIT 1", [user_id])
                contador = cur.fetchone()
                if not contador: return None

                # 2. Criar o objeto JSONB para o campo DadosAudit [cite: 27, 41]
                audit_data = {
                    "temperatura": data.get("temperatura", 25),
                    "voltagem": data.get("voltagem", 230),
                    "erro_codigo": data.get("erro_codigo")
                }
                
                # 3. Inserir na tabela Leituras respeitando o particionamento [cite: 26, 41]
                cur.execute("""
                    INSERT INTO Leituras (ContadorID, DataHora, KWh_Leitura, DadosAudit) 
                    VALUES (%s, %s, %s, %s) RETURNING *
                """, [
                    contador['contadorid'], 
                    datetime.now(), 
                    data.get('kwh_leitura'), 
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
                # Query JSONB otimizada conforme requisito 3.3 [cite: 27, 28, 32]
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
                # Chama a Procedure obrigatória sp_MatchingEngine [cite: 17, 35]
                cur.execute("CALL sp_MatchingEngine()")
                conn.commit()
                return True
    except Exception as e:
        return False
