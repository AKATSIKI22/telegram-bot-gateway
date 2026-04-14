import sqlite3
import secrets

def init_db():
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    
    # Заявки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT,
            phone TEXT,
            inn TEXT,
            income REAL,
            term INTEGER,
            amount REAL,
            payment REAL,
            session_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Сессии авторизации
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS auth_sessions (
            session_id TEXT PRIMARY KEY,
            phone TEXT,
            sms_code TEXT,
            pin_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def generate_session_id():
    return secrets.token_hex(8)

def save_application(data):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO applications (fullname, phone, inn, income, term, amount, payment, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (data['fullname'], data['phone'], data['inn'], data['income'], 
          data['term'], data['amount'], data['payment'], data['session_id']))
    conn.commit()
    conn.close()

def get_application(session_id):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM applications WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def save_auth_session(session_id, phone, sms_code, pin_code):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO auth_sessions (session_id, phone, sms_code, pin_code)
        VALUES (?, ?, ?, ?)
    ''', (session_id, phone, sms_code, pin_code))
    conn.commit()
    conn.close()

def get_auth_session(session_id):
    conn = sqlite3.connect('applications.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM auth_sessions WHERE session_id = ?', (session_id,))
    row = cursor.fetchone()
    conn.close()
    return row
