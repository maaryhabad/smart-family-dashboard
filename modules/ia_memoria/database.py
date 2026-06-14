import sqlite3
import os
import datetime

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
            google_event_id TEXT,
            localizacao TEXT,
            recorrencia TEXT
        )
    ''')
    
    # Check if localizacao and recorrencia columns exist, add if not
    cursor.execute("PRAGMA table_info(eventos)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'localizacao' not in columns:
        cursor.execute("ALTER TABLE eventos ADD COLUMN localizacao TEXT")
    if 'recorrencia' not in columns:
        cursor.execute("ALTER TABLE eventos ADD COLUMN recorrencia TEXT")
        
    # Create table usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            avatar TEXT,
            classe TEXT,
            nivel INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            xp_to_next_level INTEGER DEFAULT 100,
            gold INTEGER DEFAULT 0
        )
    ''')
    
    # Create table tarefas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tarefas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_nome TEXT NOT NULL,
            titulo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            dificuldade TEXT NOT NULL,
            reward_xp INTEGER NOT NULL,
            reward_gold INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            data TEXT NOT NULL,
            hora TEXT NOT NULL,
            evento_calendario_id INTEGER
        )
    ''')
    
    # Create table recompensas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recompensas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_nome TEXT NOT NULL,
            titulo TEXT NOT NULL,
            custo INTEGER NOT NULL,
            icone TEXT NOT NULL,
            resgatado INTEGER DEFAULT 0
        )
    ''')
    
    # Create table eventos_deletados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos_deletados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_event_id TEXT UNIQUE NOT NULL
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
        
    # Seed profiles
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    user_count = cursor.fetchone()[0]
    if user_count == 0:
        initial_users = [
            ('Mari', '👩‍💻', 'Guardiã da Organização', 1, 0, 100, 0),
            ('Cassi', '👨‍💻', 'Guerreiro da Limpeza', 1, 0, 100, 0),
            ('Isa', '👧', 'Pequena Aprendiz', 1, 0, 100, 0)
        ]
        cursor.executemany(
            "INSERT INTO usuarios (nome, avatar, classe, nivel, xp, xp_to_next_level, gold) VALUES (?, ?, ?, ?, ?, ?, ?)",
            initial_users
        )
        conn.commit()
        print("Perfis de usuários semeados!")
        
    # Seed rewards
    cursor.execute("SELECT COUNT(*) FROM recompensas")
    rewards_count = cursor.fetchone()[0]
    if rewards_count == 0:
        initial_rewards = [
            ('Mari', 'Momento SPA em casa', 30, '🧖‍♀️'),
            ('Mari', 'Escolher o restaurante do jantar de sexta', 20, '🍕'),
            ('Mari', '1 hora de leitura ininterrupta', 25, '📚'),
            ('Mari', 'Café da manhã na cama preparado pelo Cassi', 40, '☕'),
            ('Cassi', '1 hora de videogame sem interrupções', 30, '🎮'),
            ('Cassi', 'Escolher o filme do final de semana', 15, '🍿'),
            ('Cassi', 'Dormir até mais tarde no domingo', 25, '😴'),
            ('Cassi', 'Escolher a cerveja artesanal do churrasco', 40, '🍺'),
            ('Isa', '30 min de tela (desenho/tablet)', 15, '📱'),
            ('Isa', 'Escolher a historinha de dormir', 5, '📖'),
            ('Isa', 'Brincar de massinha com papai/mamãe', 10, '🎨'),
            ('Isa', 'Passeio no parque no fim de semana', 35, '🛝')
        ]
        cursor.executemany(
            "INSERT INTO recompensas (usuario_nome, titulo, custo, icone) VALUES (?, ?, ?, ?)",
            initial_rewards
        )
        conn.commit()
        print("Recompensas semeadas!")
        
    # Seed tasks
    cursor.execute("SELECT COUNT(*) FROM tarefas")
    tasks_count = cursor.fetchone()[0]
    if tasks_count == 0:
        conn.close()
        seed_tasks(target_path)
    else:
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
    cursor.execute("SELECT id, titulo, data, hora, responsavel, cor, categoria, google_event_id, localizacao, recorrencia FROM eventos")
    rows = cursor.fetchall()
    events = [dict(row) for row in rows]
    conn.close()
    return events

def save_event(titulo, data, hora, responsavel='Família', cor='#5f27cd', categoria='Familiar', google_event_id=None, localizacao=None, recorrencia=None, db_path=None):
    """Saves a new event in the database."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria, google_event_id, localizacao, recorrencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (titulo, data, hora, responsavel, cor, categoria, google_event_id, localizacao, recorrencia)
    )
    conn.commit()
    event_id = cursor.lastrowid
    conn.close()
    return event_id

def delete_event(event_id, db_path=None):
    """Deletes an event by ID and records its google_event_id if present for deletion synchronization."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # Record google_event_id if it exists before deleting
    cursor.execute("SELECT google_event_id FROM eventos WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    if row and row['google_event_id']:
        g_id = row['google_event_id']
        cursor.execute("INSERT OR IGNORE INTO eventos_deletados (google_event_id) VALUES (?)", (g_id,))
        
    cursor.execute("DELETE FROM eventos WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

def get_deleted_event_google_ids(db_path=None):
    """Fetches all google_event_ids that were deleted locally."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT google_event_id FROM eventos_deletados")
    rows = cursor.fetchall()
    ids = [row['google_event_id'] for row in rows]
    conn.close()
    return ids

def remove_deleted_event_google_id(google_event_id, db_path=None):
    """Removes a google_event_id from the deleted list once synced."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM eventos_deletados WHERE google_event_id = ?", (google_event_id,))
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

def update_event(event_id, titulo, data, hora, responsavel='Família', cor='#5f27cd', categoria='Familiar', localizacao=None, recorrencia=None, db_path=None):
    """Updates an existing event in the database by its ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE eventos SET titulo = ?, data = ?, hora = ?, responsavel = ?, cor = ?, categoria = ?, localizacao = ?, recorrencia = ? WHERE id = ?",
        (titulo, data, hora, responsavel, cor, categoria, localizacao, recorrencia, event_id)
    )
    conn.commit()
    conn.close()
def seed_tasks(db_path=None):
    import datetime
    import random
    target_path = db_path if db_path else DATABASE_PATH
    
    # We will generate tasks for the week of June 14, 2026 (Sunday) to June 20, 2026 (Saturday)
    start_date = datetime.date(2026, 6, 14)
    
    # 1. Isa's tasks - directly assigned to Isa
    isa_templates = [
        # (title, category, difficulty, xp, gold, default_time, days, {day_of_week: time_override})
        ('Verificar água dos gatos', 'Pets', 'Fácil', 10, 1, '19:30', [2, 0], {0: '10:00'}),
        ('Tirar o lixo do banheiro', 'Limpeza', 'Difícil', 25, 5, '19:30', [3, 6], {6: '13:00'}),
        ('Encher a garrafa de água da Isa do quarto', 'Organização', 'Médio', 15, 3, '20:00', [0, 1, 2, 3, 4, 5, 6], {}),
        ('Banho', 'Geral', 'Fácil', 10, 1, '20:15', [0, 1, 2, 3, 4, 5, 6], {}),
        ('Banho e lavar cabelo', 'Geral', 'Fácil', 10, 1, '20:15', [0, 2, 4, 6], {}),
        ('Sapatos na sapateira', 'Organização', 'Fácil', 10, 1, '19:45', [0, 1, 2, 3, 4, 5, 6], {}),
        ('Roupa suja no cesto', 'Organização', 'Fácil', 10, 1, '20:30', [0, 1, 2, 3, 4, 5, 6], {}),
        ('Escovar os dentes', 'Geral', 'Fácil', 10, 1, '21:00', [0, 1, 2, 3, 4, 5, 6], {}),
        ('Guardar brinquedos', 'Infantil', 'Difícil', 25, 5, '17:00', [6, 0], {}),
        ('Preparar a mochila', 'Infantil', 'Fácil', 10, 1, '20:45', [1, 2, 3, 4, 5], {})
    ]
    
    # 2. Cassi/Mari shared tasks - to be split 50/50 randomly
    shared_templates = [
        # (title, category, difficulty, xp, gold, default_time, days, {day_of_week: time_override})
        ('Verificar ração dos gatos', 'Pets', 'Fácil', 10, 1, '08:00', [1, 4], {}),
        ('Lavar lençóis e toalhas', 'Limpeza', 'Médio', 15, 5, '09:00', [0], {}),
        ('Arrumar a sala', 'Organização', 'Ultra', 40, 10, '14:00', [6], {}),
        ('Arrumar quarto', 'Organização', 'Ultra', 40, 10, '10:00', [6], {}),
        ('Lavar banheiro', 'Limpeza', 'Ultra', 40, 10, '11:00', [6], {}),
        ('Arrumar sala de jogos', 'Organização', 'Ultra', 40, 10, '15:00', [6], {}),
        ('Limpar quarto da Isa', 'Limpeza', 'Médio', 15, 5, '16:00', [6], {}),
        ('Lavar roupa', 'Limpeza', 'Fácil', 10, 3, '08:30', [1], {}),
        ('Dobrar roupa', 'Limpeza', 'Médio', 15, 5, '19:30', [1], {}),
        ('Guardar roupa', 'Limpeza', 'Fácil', 10, 3, '20:00', [1], {}),
        ('Tirar o lixo', 'Organização', 'Fácil', 10, 3, '19:30', [5], {}),
        ('Limpar a areia dos gatos', 'Pets', 'Difícil', 25, 5, '19:30', [0, 2, 4, 6], {0: '10:00', 2: '08:30', 6: '10:00'}),
        ('Pia da cozinha', 'Limpeza', 'Fácil', 10, 1, '20:30', [0, 1, 2, 3, 4, 5, 6], {}),
        ('15 minutos apagando foco de bagunça', 'Organização', 'Médio', 15, 3, '19:45', [0, 1, 2, 3, 4, 5, 6], {})
    ]
    
    user_colors = {
        'Mari': '#ff7675',
        'Cassi': '#54a0ff',
        'Isa': '#1dd1a1'
    }
    
    # Generate all Isa instances
    for offset in range(7):
        current_date = start_date + datetime.timedelta(days=offset)
        date_str = current_date.strftime('%Y-%m-%d')
        day_of_week = (offset + 0) % 7 # Sunday is 0
        
        for title, category, difficulty, xp, gold, time_str, days, overrides in isa_templates:
            if day_of_week in days:
                t_str = overrides.get(day_of_week, time_str)
                # Save calendar event
                color = user_colors['Isa']
                event_id = save_event(
                    titulo=f"Tarefa Isa: {title}",
                    data=date_str,
                    hora=t_str,
                    responsavel='Isa',
                    cor=color,
                    categoria=category,
                    db_path=target_path
                )
                
                # Insert task
                conn = get_db_connection(target_path)
                cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
                cursor.execute('''
                    INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                ''', ('Isa', title, category, difficulty, xp, gold, date_str, t_str, event_id))
                conn.commit()
                conn.close()
                
    # Generate all Cassi/Mari shared instances
    shared_instances = []
    for offset in range(7):
        current_date = start_date + datetime.timedelta(days=offset)
        date_str = current_date.strftime('%Y-%m-%d')
        day_of_week = (offset + 0) % 7 # Sunday is 0
        
        for title, category, difficulty, xp, gold, time_str, days, overrides in shared_templates:
            if day_of_week in days:
                t_str = overrides.get(day_of_week, time_str)
                shared_instances.append({
                    'titulo': title,
                    'categoria': category,
                    'dificuldade': difficulty,
                    'reward_xp': xp,
                    'reward_gold': gold,
                    'data': date_str,
                    'hora': t_str
                })
                
    # Shuffle and split 50/50 randomly
    random.shuffle(shared_instances)
    mid = len(shared_instances) // 2
    for idx, inst in enumerate(shared_instances):
        user = 'Cassi' if idx < mid else 'Mari'
        color = user_colors[user]
        event_id = save_event(
            titulo=f"Tarefa {user}: {inst['titulo']}",
            data=inst['data'],
            hora=inst['hora'],
            responsavel=user,
            cor=color,
            categoria=inst['categoria'],
            db_path=target_path
        )
        
        conn = get_db_connection(target_path)
        cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
        cursor.execute('''
            INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        ''', (user, inst['titulo'], inst['categoria'], inst['dificuldade'], inst['reward_xp'], inst['reward_gold'], inst['data'], inst['hora'], event_id))
        conn.commit()
        conn.close()

def get_all_users(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, avatar, classe, nivel, xp, xp_to_next_level, gold FROM usuarios")
    rows = cursor.fetchall()
    users = [dict(row) for row in rows]
    conn.close()
    return users

def get_user_by_name(nome, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, avatar, classe, nivel, xp, xp_to_next_level, gold FROM usuarios WHERE LOWER(nome) = ?", (nome.lower(),))
    row = cursor.fetchone()
    user = dict(row) if row else None
    conn.close()
    return user

def update_user_stats(nome, xp, gold, nivel, xp_to_next_level, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE usuarios SET xp = ?, gold = ?, nivel = ?, xp_to_next_level = ? WHERE LOWER(nome) = ?",
        (xp, gold, nivel, xp_to_next_level, nome.lower())
    )
    conn.commit()
    conn.close()

def get_tasks_for_user(usuario_nome, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
    cursor.execute(
        "SELECT id, usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id FROM tarefas WHERE LOWER(usuario_nome) = ?",
        (usuario_nome.lower(),)
    )
    rows = cursor.fetchall()
    tasks = []
    import datetime
    today = datetime.date.today()
    for row in rows:
        t = dict(row)
        if not t['completed']:
            try:
                task_date = datetime.datetime.strptime(t['data'], '%Y-%m-%d').date()
                days_overdue = (today - task_date).days
                if days_overdue > 0:
                    t['reward_xp'] += days_overdue * 2
                    t['reward_gold'] += days_overdue * 1
                    t['overdue_days'] = days_overdue
            except Exception:
                pass
        tasks.append(t)
    conn.close()
    return tasks

def get_all_tasks(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.conn.cursor() if hasattr(conn, 'conn') else conn.cursor()
    cursor.execute("SELECT id, usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id FROM tarefas")
    rows = cursor.fetchall()
    tasks = []
    import datetime
    today = datetime.date.today()
    for row in rows:
        t = dict(row)
        if not t['completed']:
            try:
                task_date = datetime.datetime.strptime(t['data'], '%Y-%m-%d').date()
                days_overdue = (today - task_date).days
                if days_overdue > 0:
                    t['reward_xp'] += days_overdue * 2
                    t['reward_gold'] += days_overdue * 1
                    t['overdue_days'] = days_overdue
            except Exception:
                pass
        tasks.append(t)
    conn.close()
    return tasks

def save_task(usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, evento_calendario_id=None, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    
    # If no calendar event id is provided, create it first
    if not evento_calendario_id:
        user_colors = {
            'Mari': '#ff7675',
            'Cassi': '#54a0ff',
            'Isa': '#1dd1a1'
        }
        color = user_colors.get(usuario_nome, '#5f27cd')
        evento_calendario_id = save_event(
            titulo=f"Tarefa {usuario_nome}: {titulo}",
            data=data,
            hora=hora,
            responsavel=usuario_nome,
            cor=color,
            categoria=categoria,
            db_path=target_path
        )
        
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
        VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
    ''', (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, evento_calendario_id))
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    return task_id

def complete_task_in_db(task_id, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, usuario_nome, titulo, reward_xp, reward_gold, completed, data, evento_calendario_id FROM tarefas WHERE id = ?",
        (task_id,)
    )
    task = cursor.fetchone()
    if not task:
        conn.close()
        return False, None, False
        
    if task['completed']:
        conn.close()
        return False, dict(task), False
        
    # Mark task completed
    cursor.execute("UPDATE tarefas SET completed = 1 WHERE id = ?", (task_id,))
    conn.commit()
    
    # Fetch user to update stats
    user_nome = task['usuario_nome']
    cursor.execute("SELECT id, nome, avatar, classe, nivel, xp, xp_to_next_level, gold FROM usuarios WHERE LOWER(nome) = ?", (user_nome.lower(),))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return True, dict(task), False
        
    # Calculate rewards including dynamic rollover bonus
    reward_xp = task['reward_xp']
    reward_gold = task['reward_gold']
    try:
        import datetime
        task_date = datetime.datetime.strptime(task['data'], '%Y-%m-%d').date()
        today = datetime.date.today()
        days_overdue = (today - task_date).days
        if days_overdue > 0:
            reward_xp += days_overdue * 2
            reward_gold += days_overdue * 1
    except Exception:
        pass
        
    xp = user_row['xp'] + reward_xp
    gold = user_row['gold'] + reward_gold
    nivel = user_row['nivel']
    xp_to_next = user_row['xp_to_next_level']
    leveled_up = False
    
    while xp >= xp_to_next:
        xp -= xp_to_next
        nivel += 1
        xp_to_next = int(xp_to_next * 1.2)
        leveled_up = True
        
    cursor.execute(
        "UPDATE usuarios SET xp = ?, gold = ?, nivel = ?, xp_to_next_level = ? WHERE id = ?",
        (xp, gold, nivel, xp_to_next, user_row['id'])
    )
    conn.commit()
    
    # Update calendar event with checkmark
    g_id = task['evento_calendario_id']
    if g_id:
        cursor.execute("SELECT titulo FROM eventos WHERE id = ?", (g_id,))
        event = cursor.fetchone()
        if event:
            curr_title = event['titulo']
            if not curr_title.startswith('✅'):
                new_title = f"✅ {curr_title}"
                cursor.execute("UPDATE eventos SET titulo = ? WHERE id = ?", (new_title, g_id))
                conn.commit()
                
    conn.close()
    return True, get_user_by_name(user_nome, target_path), leveled_up

def reset_tasks_db(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # Get all active tasks to delete their associated calendar events
    cursor.execute("SELECT evento_calendario_id FROM tarefas WHERE evento_calendario_id IS NOT NULL")
    event_ids = [row[0] for row in cursor.fetchall()]
    
    # Delete from eventos
    for e_id in event_ids:
        cursor.execute("DELETE FROM eventos WHERE id = ?", (e_id,))
        
    # Delete all from tarefas
    cursor.execute("DELETE FROM tarefas")
    
    # Reset user stats to level 1, 0 XP, 0 Gold
    cursor.execute("UPDATE usuarios SET xp = 0, gold = 0, nivel = 1, xp_to_next_level = 100")
    
    conn.commit()
    conn.close()
    
    # Re-seed tasks
    seed_tasks(target_path)
    return True

def get_rewards_for_user(usuario_nome, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, usuario_nome, titulo, custo, icone, resgatado FROM recompensas WHERE LOWER(usuario_nome) = ?",
        (usuario_nome.lower(),)
    )
    rows = cursor.fetchall()
    rewards = [dict(row) for row in rows]
    conn.close()
    return rewards

def get_all_rewards(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, usuario_nome, titulo, custo, icone, resgatado FROM recompensas")
    rows = cursor.fetchall()
    rewards = [dict(row) for row in rows]
    conn.close()
    return rewards

def save_reward(usuario_nome, titulo, custo, icone, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO recompensas (usuario_nome, titulo, custo, icone, resgatado) VALUES (?, ?, ?, ?, 0)",
        (usuario_nome, titulo, custo, icone)
    )
    conn.commit()
    reward_id = cursor.lastrowid
    conn.close()
    return reward_id

def redeem_reward_in_db(reward_id, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT id, usuario_nome, titulo, custo, resgatado FROM recompensas WHERE id = ?",
        (reward_id,)
    )
    rew = cursor.fetchone()
    if not rew:
        conn.close()
        return False, "Recompensa não encontrada.", None
        
    if rew['resgatado']:
        conn.close()
        return False, "Recompensa já resgatada anteriormente.", None
        
    user_nome = rew['usuario_nome']
    cursor.execute("SELECT id, gold FROM usuarios WHERE LOWER(nome) = ?", (user_nome.lower(),))
    user_row = cursor.fetchone()
    if not user_row:
        conn.close()
        return False, "Usuário não encontrado.", None
        
    if user_row['gold'] < rew['custo']:
        conn.close()
        return False, f"Ouro insuficiente. Custo: {rew['custo']}, Disponível: {user_row['gold']}.", None
        
    # Deduct gold and mark redeemed
    new_gold = user_row['gold'] - rew['custo']
    cursor.execute("UPDATE usuarios SET gold = ? WHERE id = ?", (new_gold, user_row['id']))
    cursor.execute("UPDATE recompensas SET resgatado = 1 WHERE id = ?", (reward_id,))
    conn.commit()
    conn.close()
    
    return True, "Recompensa resgatada com sucesso!", get_user_by_name(user_nome, target_path)

def update_task_in_db(task_id, usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, db_path=None):
    """Updates an existing task in the database and updates its associated calendar event if linked."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # 1. Fetch old task details to check if there is an associated calendar event
    cursor.execute("SELECT evento_calendario_id FROM tarefas WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    evt_id = row['evento_calendario_id'] if row else None
    
    # 2. Update task details in DB
    cursor.execute('''
        UPDATE tarefas 
        SET usuario_nome = ?, titulo = ?, categoria = ?, dificuldade = ?, reward_xp = ?, reward_gold = ?, data = ?, hora = ?
        WHERE id = ?
    ''', (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, task_id))
    
    # 3. Update the associated calendar event if linked
    if evt_id:
        user_colors = {
            'Mari': '#ff7675',
            'Cassi': '#54a0ff',
            'Isa': '#1dd1a1'
        }
        color = user_colors.get(usuario_nome, '#5f27cd')
        cursor.execute('''
            UPDATE eventos
            SET titulo = ?, data = ?, hora = ?, responsavel = ?, cor = ?, categoria = ?
            WHERE id = ?
        ''', (f"Tarefa {usuario_nome}: {titulo}", data, hora, usuario_nome, color, categoria, evt_id))
        
    conn.commit()
    conn.close()
    return True

def delete_task_in_db(task_id, db_path=None):
    """Deletes a task by ID and removes its corresponding calendar event if linked."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    
    # 1. Fetch event ID
    cursor.execute("SELECT evento_calendario_id FROM tarefas WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    evt_id = row['evento_calendario_id'] if row else None
    
    # 2. Delete from tarefas
    cursor.execute("DELETE FROM tarefas WHERE id = ?", (task_id,))
    
    # 3. Delete associated event
    if evt_id:
        # Record google_event_id if it exists before deleting for sync
        cursor.execute("SELECT google_event_id FROM eventos WHERE id = ?", (evt_id,))
        evt_row = cursor.fetchone()
        if evt_row and evt_row['google_event_id']:
            g_id = evt_row['google_event_id']
            cursor.execute("INSERT OR IGNORE INTO eventos_deletados (google_event_id) VALUES (?)", (g_id,))
            
        cursor.execute("DELETE FROM eventos WHERE id = ?", (evt_id,))
        
    conn.commit()
    conn.close()
    return True

