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

def map_expense_category(cat):
    mapping = {
        "habitação": "Habitação (Aluguel/Contas)",
        "habitacao": "Habitação (Aluguel/Contas)",
        "educação": "Educação",
        "educacao": "Educação",
        "alimentação": "Alimentação e Supermercado",
        "alimentacao": "Alimentação e Supermercado",
        "saúde": "Saúde e Planos",
        "saude": "Saúde e Planos",
        "transporte": "Transporte/Combustível",
        "lazer": "Lazer e Streaming",
        "outros": "Outros"
    }
    return mapping.get(cat.lower(), "Outros") if cat else "Outros"

def get_vencimento_date(dia_vencimento):
    import datetime
    import calendar
    today = datetime.date.today()
    try:
        dt = datetime.date(today.year, today.month, int(dia_vencimento))
    except ValueError:
        last_day = calendar.monthrange(today.year, today.month)[1]
        dt = datetime.date(today.year, today.month, min(int(dia_vencimento), last_day))
    return dt.strftime('%d/%m/%Y')

def init_db(db_path=None):
    """Initializes the database and seeds initial values if empty."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()
        
        # Create table memorias
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

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS despesas_recorrentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            valor REAL NOT NULL,
            categoria TEXT,
            dia_vencimento INTEGER,
            tipo TEXT, -- 'Recorrente' ou 'Parcelado'
            total_parcelas INTEGER DEFAULT 1,
            parcela_atual INTEGER DEFAULT 1,
            data_inicio DATE
        )
    ''')
        try:
            cursor.execute("ALTER TABLE despesas_recorrentes ADD COLUMN pago INTEGER DEFAULT 0")
            conn.commit()
        except Exception:
            pass

        # Create table transacoes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                categoria TEXT NOT NULL,
                data TEXT NOT NULL,
                responsavel TEXT NOT NULL
            )
        ''')

        # Check if new columns exist in transacoes, add if not
        try:
            cursor.execute("PRAGMA table_info(transacoes)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'pago' not in columns:
                cursor.execute("ALTER TABLE transacoes ADD COLUMN pago INTEGER DEFAULT 1")
            if 'despesa_recorrente_id' not in columns:
                cursor.execute("ALTER TABLE transacoes ADD COLUMN despesa_recorrente_id INTEGER")
            conn.commit()
        except Exception:
            pass

        # Sync existing recurring expenses that do not have a transaction in transacoes
        try:
            cursor.execute("SELECT id, descricao, valor, categoria, dia_vencimento, pago FROM despesas_recorrentes")
            despesas_list = cursor.fetchall()
            for d in despesas_list:
                cursor.execute("SELECT id FROM transacoes WHERE despesa_recorrente_id = ?", (d['id'],))
                tx_exists = cursor.fetchone()
                if not tx_exists:
                    tx_desc = f"Despesa: {d['descricao']}"
                    tx_valor = -abs(d['valor'])
                    tx_cat = map_expense_category(d['categoria'])
                    tx_date = get_vencimento_date(d['dia_vencimento'])
                    cursor.execute('''
                        INSERT INTO transacoes (descricao, valor, categoria, data, responsavel, pago, despesa_recorrente_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (tx_desc, tx_valor, tx_cat, tx_date, "Família", d['pago'], d['id']))
            conn.commit()
        except Exception as e:
            print(f"Error syncing existing despesas to transacoes: {e}")

        cursor.execute("SELECT COUNT(*) FROM transacoes")
        trans_count = cursor.fetchone()[0]
        if trans_count == 0:
            initial_transactions = [
                ("Supermercado Carrefour", -450.20, "Alimentação", "10/06/2026", "Mariana"),
                ("Salário Mensal", 12500.00, "Receita", "05/06/2026", "Empresa"),
                ("Conta de Energia (Enel)", -280.30, "Habitação", "03/06/2026", "Rodrigo"),
                ("Mensalidade Faculdade (Mariana)", -950.00, "Educação", "03/06/2026", "Mariana"),
                ("Netflix Mensal", -55.90, "Lazer", "01/06/2026", "Família")
            ]
            cursor.executemany(
                "INSERT INTO transacoes (descricao, valor, categoria, data, responsavel) VALUES (?, ?, ?, ?, ?)",
                initial_transactions
            )
        
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
            print("Recompensas semeadas!")
            
        # Seed tasks
        cursor.execute("SELECT COUNT(*) FROM tarefas")
        tasks_count = cursor.fetchone()[0]
        if tasks_count == 0:
            seed_tasks(conn=conn)
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
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

def save_event(titulo, data, hora, responsavel='Família', cor='#5f27cd', categoria='Familiar', google_event_id=None, localizacao=None, recorrencia=None, db_path=None, conn=None):
    """Saves a new event in the database."""
    target_path = db_path if db_path else DATABASE_PATH
    should_close = False
    if conn is None:
        conn = get_db_connection(target_path)
        should_close = True
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria, google_event_id, localizacao, recorrencia) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (titulo, data, hora, responsavel, cor, categoria, google_event_id, localizacao, recorrencia)
    )
    if should_close:
        conn.commit()
    event_id = cursor.lastrowid
    if should_close:
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

def seed_tasks(db_path=None, conn=None):
    import datetime
    import random
    target_path = db_path if db_path else DATABASE_PATH
    
    should_close = False
    if conn is None:
        conn = get_db_connection(target_path)
        should_close = True
        conn.execute("BEGIN IMMEDIATE")
        
    cursor = conn.cursor()
    
    # We will generate tasks for the week of June 15, 2026 (Monday) to June 21, 2026 (Sunday)
    start_date = datetime.date(2026, 6, 15)
    
    # 1. Isa's tasks - directly assigned to Isa
    isa_templates = [
        # (title, category, difficulty, xp, gold, default_time, days, {day_of_week: time_override}, recurrence)
        ('Verificar água dos gatos', 'Pets', 'Fácil', 10, 1, '19:30', [2, 0], {0: '10:00'}, None),
        ('Tirar o lixo do banheiro', 'Limpeza', 'Difícil', 25, 5, '19:30', [3, 6], {6: '13:00'}, None),
        ('Encher a garrafa de água da Isa do quarto', 'Organização', 'Médio', 15, 3, '20:00', [0, 2, 4, 6], {}, None),
        ('Banho', 'Geral', 'Fácil', 10, 1, '20:15', [1, 3, 5], {}, None),
        ('Banho e lavar cabelo', 'Geral', 'Fácil', 10, 1, '20:15', [0, 2, 4, 6], {}, None),
        ('Sapatos na sapateira', 'Organização', 'Fácil', 10, 1, '19:45', [0, 1, 2, 3, 4, 5, 6], {}, None),
        ('Roupa suja no cesto', 'Organização', 'Fácil', 10, 1, '20:30', [0, 1, 2, 3, 4, 5, 6], {}, None),
        ('Escovar os dentes', 'Geral', 'Fácil', 10, 1, '21:00', [0, 1, 2, 3, 4, 5, 6], {}, None),
        ('Guardar brinquedos', 'Infantil', 'Difícil', 25, 5, '17:00', [6, 0], {}, None),
        ('Preparar a mochila', 'Infantil', 'Fácil', 10, 1, '20:45', [1, 2, 3, 4, 5], {}, None),
        ('Preparar a roupa da escola', 'Infantil', 'Fácil', 10, 1, '20:45', [1, 2, 3, 4, 5], {}, None)
    ]
    
    # 2. Cassi/Mari shared tasks - to be split 50/50 randomly (excluding daily clutter focus)
    shared_templates = [
        # (title, category, difficulty, xp, gold, default_time, days, {day_of_week: time_override})
        ('Verificar ração dos gatos', 'Pets', 'Fácil', 10, 1, '08:00', [1, 4], {}),
        ('Lavar lençóis e toalhas', 'Limpeza', 'Médio', 15, 5, '09:00', [0], {}),
        ('Arrumar a sala', 'Organização', 'Ultra', 40, 10, '14:00', [2, 6], {}),
        ('Arrumar quarto', 'Organização', 'Ultra', 40, 10, '10:00', [1, 4], {}),
        ('Lavar banheiro', 'Limpeza', 'Ultra', 40, 10, '11:00', [7], {}),
        ('Arrumar sala de jogos', 'Organização', 'Ultra', 40, 10, '15:00', [3], {}),
        ('Aspirar quarto da Isa', 'Limpeza', 'Médio', 15, 5, '16:00', [6], {}),
        ('Lavar roupa', 'Limpeza', 'Fácil', 10, 3, '08:30', [1, 4], {}),
        ('Dobrar roupa', 'Limpeza', 'Médio', 15, 5, '19:30', [2, 5], {}),
        ('Guardar roupa', 'Limpeza', 'Fácil', 10, 3, '20:00', [2, 5], {}),
        ('Tirar o lixo', 'Organização', 'Fácil', 10, 3, '19:30', [3, 6], {}),
        ('Limpar a areia dos gatos', 'Pets', 'Difícil', 25, 5, '19:30', [0, 2, 4, 6], {0: '10:00', 2: '08:30', 6: '10:00'}),
        ('Pia da cozinha', 'Limpeza', 'Fácil', 10, 1, '20:30', [0, 1, 2, 3, 4, 5, 6], {})
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
        day_of_week = int(current_date.strftime('%w')) # Sunday is 0, Monday is 1...
        
        for title, category, difficulty, xp, gold, time_str, days, overrides, recurrence in isa_templates:
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
                    recorrencia=recurrence,
                    db_path=target_path,
                    conn=conn
                )
                
                # Insert task
                cursor.execute('''
                    INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
                    VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                ''', ('Isa', title, category, difficulty, xp, gold, date_str, t_str, event_id))
                
    # Generate all Cassi/Mari shared instances
    shared_instances = []
    for offset in range(7):
        current_date = start_date + datetime.timedelta(days=offset)
        date_str = current_date.strftime('%Y-%m-%d')
        day_of_week = int(current_date.strftime('%w')) # Sunday is 0, Monday is 1...
        
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
            db_path=target_path,
            conn=conn
        )
        
        cursor.execute('''
            INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        ''', (user, inst['titulo'], inst['categoria'], inst['dificuldade'], inst['reward_xp'], inst['reward_gold'], inst['data'], inst['hora'], event_id))

    # Generate daily clutter focus tasks for both Cassi and Mari
    for offset in range(7):
        current_date = start_date + datetime.timedelta(days=offset)
        date_str = current_date.strftime('%Y-%m-%d')
        
        for user in ['Cassi', 'Mari']:
            color = user_colors[user]
            event_id = save_event(
                titulo=f"Tarefa {user}: 15 minutos apagando foco de bagunça",
                data=date_str,
                hora='19:45',
                responsavel=user,
                cor=color,
                categoria='Organização',
                db_path=target_path,
                conn=conn
            )
            
            cursor.execute('''
                INSERT INTO tarefas (usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, completed, data, hora, evento_calendario_id)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            ''', (user, '15 minutos apagando foco de bagunça', 'Organização', 'Médio', 15, 3, date_str, '19:45', event_id))

    if should_close:
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

def save_task(usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, evento_calendario_id=None, recorrencia=None, db_path=None):
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
            recorrencia=recorrencia,
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

def update_reward_in_db(reward_id, usuario_nome, titulo, custo, icone, db_path=None):
    """Updates an existing reward in the database by its ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE recompensas SET usuario_nome = ?, titulo = ?, custo = ?, icone = ? WHERE id = ?",
        (usuario_nome, titulo, custo, icone, reward_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_reward_in_db(reward_id, db_path=None):
    """Deletes a reward by ID."""
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM recompensas WHERE id = ?", (reward_id,))
    conn.commit()
    conn.close()
    return True

def complete_reward_in_db(reward_id, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE recompensas SET resgatado = 2 WHERE id = ?", (reward_id,))
    conn.commit()
    conn.close()
    return True

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

def update_task_in_db(task_id, usuario_nome, titulo, categoria, dificuldade, reward_xp, reward_gold, data, hora, recorrencia=None, db_path=None):
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
            SET titulo = ?, data = ?, hora = ?, responsavel = ?, cor = ?, categoria = ?, recorrencia = ?
            WHERE id = ?
        ''', (f"Tarefa {usuario_nome}: {titulo}", data, hora, usuario_nome, color, categoria, recorrencia, evt_id))
        
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

def update_despesa(id, descricao, valor, categoria, dia, tipo, total_parcelas):
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE despesas_recorrentes 
        SET descricao = ?, valor = ?, categoria = ?, dia_vencimento = ?, tipo = ?, total_parcelas = ?
        WHERE id = ?
    ''', (descricao, valor, categoria, dia, tipo, total_parcelas, id))
    
    # Update or insert corresponding transaction
    tx_desc = f"Despesa: {descricao}"
    tx_valor = -abs(valor)
    tx_cat = map_expense_category(categoria)
    tx_date = get_vencimento_date(dia)
    
    cursor.execute("SELECT id FROM transacoes WHERE despesa_recorrente_id = ?", (id,))
    tx_row = cursor.fetchone()
    if tx_row:
        cursor.execute('''
            UPDATE transacoes
            SET descricao = ?, valor = ?, categoria = ?, data = ?
            WHERE despesa_recorrente_id = ?
        ''', (tx_desc, tx_valor, tx_cat, tx_date, id))
    else:
        cursor.execute("SELECT pago FROM despesas_recorrentes WHERE id = ?", (id,))
        pago_status = cursor.fetchone()[0]
        cursor.execute('''
            INSERT INTO transacoes (descricao, valor, categoria, data, responsavel, pago, despesa_recorrente_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (tx_desc, tx_valor, tx_cat, tx_date, "Família", pago_status, id))
        
    conn.commit()
    conn.close()

def save_despesa(descricao, valor, categoria, dia, tipo, total_parcelas):
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO despesas_recorrentes 
        (descricao, valor, categoria, dia_vencimento, tipo, total_parcelas, pago)
        VALUES (?, ?, ?, ?, ?, ?, 0)
    ''', (descricao, valor, categoria, dia, tipo, total_parcelas))
    new_despesa_id = cursor.lastrowid
    
    # Also create a corresponding unpaid transaction in transacoes
    tx_desc = f"Despesa: {descricao}"
    tx_valor = -abs(valor)
    tx_cat = map_expense_category(categoria)
    tx_date = get_vencimento_date(dia)
    cursor.execute('''
        INSERT INTO transacoes (descricao, valor, categoria, data, responsavel, pago, despesa_recorrente_id)
        VALUES (?, ?, ?, ?, ?, 0, ?)
    ''', (tx_desc, tx_valor, tx_cat, tx_date, "Família", new_despesa_id))
    
    conn.commit()
    conn.close()
    return new_despesa_id

def get_all_despesas():
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM despesas_recorrentes')
    despesas = cursor.fetchall()
    conn.close()
    return [dict(d) for d in despesas]

def delete_despesa(id):
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM transacoes WHERE despesa_recorrente_id = ?', (id,))
    cursor.execute('DELETE FROM despesas_recorrentes WHERE id = ?', (id,))
    conn.commit()
    conn.close()

def toggle_despesa_pago(id, pago):
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE despesas_recorrentes 
        SET pago = ?
        WHERE id = ?
    ''', (pago, id))
    
    cursor.execute('''
        UPDATE transacoes
        SET pago = ?
        WHERE despesa_recorrente_id = ?
    ''', (pago, id))
    
    conn.commit()
    conn.close()

def delete_transaction_from_db(id):
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT despesa_recorrente_id FROM transacoes WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and row['despesa_recorrente_id']:
        despesa_id = row['despesa_recorrente_id']
        cursor.execute("UPDATE despesas_recorrentes SET pago = 0 WHERE id = ?", (despesa_id,))
        # Delete transaction
        cursor.execute("DELETE FROM transacoes WHERE id = ?", (id,))
        # Re-create the unpaid transaction so it shows as pending/overdue
        cursor.execute("SELECT descricao, valor, categoria, dia_vencimento FROM despesas_recorrentes WHERE id = ?", (despesa_id,))
        d_row = cursor.fetchone()
        if d_row:
            tx_desc = f"Despesa: {d_row['descricao']}"
            tx_valor = -abs(d_row['valor'])
            tx_cat = map_expense_category(d_row['categoria'])
            tx_date = get_vencimento_date(d_row['dia_vencimento'])
            cursor.execute('''
                INSERT INTO transacoes (descricao, valor, categoria, data, responsavel, pago, despesa_recorrente_id)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (tx_desc, tx_valor, tx_cat, tx_date, "Família", despesa_id))
    else:
        cursor.execute("DELETE FROM transacoes WHERE id = ?", (id,))
        
    conn.commit()
    conn.close()

def get_all_transactions(db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, descricao, valor, categoria, data, responsavel, pago FROM transacoes ORDER BY id DESC")
    rows = cursor.fetchall()
    transactions = [
        {
            "description": row["descricao"],
            "amount": row["valor"],
            "category": row["categoria"],
            "date": row["data"],
            "user": row["responsavel"],
            "id": row["id"],
            "pago": row["pago"] if "pago" in dict(row) else 1
        }
        for row in rows
    ]
    conn.close()
    return transactions

def save_transaction_to_db(descricao, valor, categoria, data, responsavel, pago=1, db_path=None):
    target_path = db_path if db_path else DATABASE_PATH
    conn = get_db_connection(target_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transacoes (descricao, valor, categoria, data, responsavel, pago) VALUES (?, ?, ?, ?, ?, ?)",
        (descricao, valor, categoria, data, responsavel, pago)
    )
    conn.commit()
    trans_id = cursor.lastrowid
    conn.close()
    return trans_id