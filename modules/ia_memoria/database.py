import sqlite3
import os

# Compute the path to database.db at the project root directory
# (three levels up: database.py -> ia_memoria -> modules -> root)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATABASE_PATH = os.path.join(ROOT_DIR, 'database.db')

def get_db_connection(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes the database and seeds initial values if empty."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL,
            chave TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create eventos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            responsavel TEXT DEFAULT 'Família',
            cor TEXT DEFAULT '#5f27cd',
            categoria TEXT DEFAULT 'Familiar',
            google_event_id TEXT
        )
    ''')
    
    # Check if empty to seed initial values
    cursor.execute("SELECT COUNT(*) FROM memorias")
    count = cursor.fetchone()[0]
    
    if count == 0:
        initial_memories = [
            ('Senhas', 'wifi', 'A senha do Wi-Fi de visitas é **FamiliaFeliz2026!** e funciona nas redes 2.4Ghz e 5Ghz.'),
            ('Segurança', 'chave', 'As chaves reserva da casa e do carro estão guardadas na caixinha de madeira na gaveta do meio do aparador da entrada.'),
            ('Contatos', 'encanador', 'O contato do encanador Seu Mário é **(11) 98765-4321**. Ele atende emergências de final de semana.'),
            ('Ferramentas', 'ferramenta', 'A caixa de ferramentas vermelha está na segunda prateleira da estante de metal na garagem.'),
            ('Organização', 'natal', 'As caixas com decorações de Natal estão guardadas no sótão/maleiro do quarto de hóspedes, etiquetadas como "NATAL".'),
            ('Pets', 'vacina', 'A carteira de vacinação do Pipoca (o pet) está na pasta de documentos azul no armário do escritório.')
        ]
        
        cursor.executemany(
            "INSERT INTO memorias (categoria, chave, conteudo) VALUES (?, ?, ?)",
            initial_memories
        )
        conn.commit()
        print("Banco de dados modular inicializado e populado com memórias padrão!")
        
    # Check if empty to seed initial calendar events
    cursor.execute("SELECT COUNT(*) FROM eventos")
    count_eventos = cursor.fetchone()[0]
    
    if count_eventos == 0:
        initial_events = [
            ("Almoço de Domingo na Vó", "2026-06-14", "12:30", "Família", "#5f27cd", "Familiar"),
            ("Dentista Mariana", "2026-06-15", "14:00", "Mariana", "#00d2d3", "Saúde"),
            ("Reunião de Condomínio", "2026-06-17", "20:00", "Rodrigo", "#ff9f43", "Compromisso"),
            ("Vacina do Pipoca (Pet)", "2026-06-20", "09:00", "Família", "#54a0ff", "Pet"),
            ("Aniversário do Lucas", "2026-06-25", "18:00", "Lucas", "#ff4d4d", "Familiar")
        ]
        cursor.executemany(
            "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria) VALUES (?, ?, ?, ?, ?, ?)",
            initial_events
        )
        conn.commit()
        print("Tabela de eventos inicializada e populada com compromissos padrão!")
        
    conn.close()

def save_memory(categoria, chave, conteudo, db_path=None):
    """Saves or updates a memory in the database."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # Check if chave already exists (case insensitive) to update it, otherwise insert
    cursor.execute("SELECT id FROM memorias WHERE LOWER(chave) = ?", (chave.lower(),))
    row = cursor.fetchone()
    
    if row:
        cursor.execute(
            "UPDATE memorias SET categoria = ?, conteudo = ? WHERE id = ?",
            (categoria, conteudo, row['id'])
        )
    else:
        cursor.execute(
            "INSERT INTO memorias (categoria, chave, conteudo) VALUES (?, ?, ?)",
            (categoria, chave.lower(), conteudo)
        )
        
    conn.commit()
    conn.close()

def get_all_memories(db_path=None):
    """Fetches all memories from the database."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, categoria, chave, conteudo FROM memorias")
    rows = cursor.fetchall()
    memories = [dict(row) for row in rows]
    conn.close()
    return memories

def delete_memory(memory_id, db_path=None):
    """Deletes a memory by ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memorias WHERE id = ?", (memory_id,))
    conn.commit()
    conn.close()

def update_memory(memory_id, categoria, chave, conteudo, db_path=None):
    """Updates an existing memory in the database by its ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE memorias SET categoria = ?, chave = ?, conteudo = ? WHERE id = ?",
        (categoria, chave.lower(), conteudo, memory_id)
    )
    conn.commit()
    conn.close()


def get_all_events(db_path=None):
    """Fetches all events from the database."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, data, hora, responsavel, cor, categoria, google_event_id FROM eventos")
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events

def save_event(titulo, data, hora, responsavel='Família', cor='#5f27cd', categoria='Familiar', google_event_id=None, db_path=None):
    """Saves a new event in the database."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria, google_event_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (titulo, data, hora, responsavel, cor, categoria, google_event_id)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id

def delete_event(event_id, db_path=None):
    """Deletes an event by ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eventos WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def update_event_google_id(event_id, google_id, db_path=None):
    """Updates the Google Event ID of an event."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE eventos SET google_event_id = ? WHERE id = ?",
        (google_id, event_id)
    )
    conn.commit()
    conn.close()

def update_event(event_id, titulo, data, hora, responsavel='Família', cor='#5f27cd', categoria='Familiar', db_path=None):
    """Updates an existing event in the database by its ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE eventos SET titulo = ?, data = ?, hora = ?, responsavel = ?, cor = ?, categoria = ? WHERE id = ?",
        (titulo, data, hora, responsavel, cor, categoria, event_id)
    )
    conn.commit()
    conn.close()



