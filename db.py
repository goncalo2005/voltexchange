import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_connection():
    # As variáveis de ambiente devem ser configuradas no teu PC ou na Cloud (Vercel/Render)
    return psycopg2.connect(
        host=os.environ.get("DATABASE_HOST"), 
        database=os.environ.get("DATABASE_NAME"), 
        user=os.environ.get("DATABASE_USER"), 
        password=os.environ.get("DATABASE_PASSWORD"),
        sslmode='require' # Importante para ligações à escola/cloud
    )

# --- AUTENTICAÇÃO ---
def login(email, password):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                
                cur.execute("SELECT * FROM Utilizadores WHERE Email = %s AND PasswordHash = crypt(%s, PasswordHash)", [email, password])
                return cur.fetchone()
    except Exception as e:
        print(f"Erro no login: {e}")
        return None

# --- LEITURAS (Trigger de Anomalias corre automaticamente na BD) ---
def add_reading(data, user_id):
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Primeiro, verificamos se o contador pertence ao utilizador
                cur.execute("SELECT ContadorID FROM Contadores WHERE UtilizadorID = %s LIMIT 1", [user_id])
                contador = cur.fetchone()
                
                if not contador: return None

                cur.execute("""
                    INSERT INTO Leituras (ContadorID, DataHora, KWh_Leitura, DadosAudit) 
                    VALUES (%s, %s, %s, %s) RETURNING *
                """, [contador['contadorid'], data['datahora'], data['kwh'], data['dados_audit']])
                conn.commit()
                return cur.fetchone()
    except Exception as e:
        print(f"Erro ao inserir leitura: {e}")
        return None

# --- MERCADO & MATCHING ---
def execute_direct_purchase(oferta_id, comprador_id):
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Chama a Stored Procedure que criámos na BD
                cur.execute("CALL sp_ExecutarCompraDireta(%s, %s)", [oferta_id, comprador_id])
                conn.commit()
                return True
    except Exception as e:
        print(f"Erro na compra: {e}")
        return False

def run_matching_engine():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
               
                cur.execute("CALL sp_MatchingEngine()")
                conn.commit()
                return True
    except Exception as e:
        print(f"Erro no matching: {e}")
        return False

# --- ADMIN: LISTAR ANOMALIAS (JSONB Otimizado) ---
def get_anomalies():
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Query JSONB otimizada para o GIN Index
                cur.execute("""
                    SELECT c.NumeroSerie, l.* FROM Leituras l
                    JOIN Contadores c ON l.ContadorID = c.ContadorID
                    WHERE l.DadosAudit->>'erro_codigo' IS NOT NULL 
                       OR (l.DadosAudit->>'temperatura')::int > 80
                """)
                return cur.fetchall()
    except Exception as e:
        return []