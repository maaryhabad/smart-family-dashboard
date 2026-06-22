import os
import random
from modules.ia_memoria.google_calendar import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request

from modules.ia_memoria.database import init_db
from modules.ia_memoria.routes import ia_memoria_bp

app = Flask(__name__)
app.register_blueprint(ia_memoria_bp)

# Mock database/state for demonstration purposes
GAMES_STATE = {
    "character": {
        "name": "Família Aventureira",
        "avatar": "🛡️",
        "class": "Guardiões do Lar",
        "level": 3,
        "xp": 340,
        "xp_to_next_level": 1000,
        "gold": 120
    },
    "quests": [
        {"id": 1, "title": "Lavar e guardar a louça do jantar", "reward_xp": 50, "reward_gold": 15, "category": "Limpeza", "difficulty": "Fácil", "completed": False},
        {"id": 2, "title": "Levar o lixo e recicláveis para fora", "reward_xp": 30, "reward_gold": 10, "category": "Organização", "difficulty": "Rápido", "completed": False},
        {"id": 3, "title": "Organizar os brinquedos/sala de estar", "reward_xp": 80, "reward_gold": 25, "category": "Organização", "difficulty": "Médio", "completed": False},
        {"id": 4, "title": "Limpar a caixa de areia do gato / dar comida", "reward_xp": 40, "reward_gold": 12, "category": "Pets", "difficulty": "Fácil", "completed": False},
        {"id": 5, "title": "Faxina profunda no quarto (Missão Semanal)", "reward_xp": 200, "reward_gold": 75, "category": "Limpeza", "difficulty": "Difícil", "completed": False}
    ],
    "rewards": [
        {"id": 101, "title": "30 minutos extras de videogame", "cost": 100, "icon": "🎮"},
        {"id": 102, "title": "Escolher a pizza/jantar de sexta", "cost": 200, "icon": "🍕"},
        {"id": 103, "title": "Cinema no fim de semana com pipoca", "cost": 450, "icon": "🍿"},
        {"id": 104, "title": "Isenção de uma tarefa diária à escolha", "cost": 300, "icon": "🎫"}
    ]
}



FINANCIAL_DATA = {
    "summary": {
        "income": 12500.00,
        "expenses": 8420.50,
        "savings": 4079.50,
        "savings_rate": 32.6
    },
    "categories": [
        {"name": "Habitação (Aluguel/Contas)", "value": 3200.00, "percentage": 38, "color": "#ff4d4d"},
        {"name": "Educação", "value": 950.00, "percentage": 12, "color": "#111827"},
        {"name": "Alimentação e Supermercado", "value": 1850.50, "percentage": 22, "color": "#ff9f43"},
        {"name": "Saúde e Planos", "value": 1200.00, "percentage": 14, "color": "#00d2d3"},
        {"name": "Transporte/Combustível", "value": 950.00, "percentage": 11, "color": "#54a0ff"},
        {"name": "Lazer e Streaming", "value": 720.00, "percentage": 9, "color": "#5f27cd"},
        {"name": "Outros", "value": 500.00, "percentage": 6, "color": "#c8d6e5"}
    ],
    "savings_goals": [
        {"title": "Viagem de Fim de Ano", "target": 8000.00, "current": 5400.00, "percentage": 67.5},
        {"title": "Reforma do Escritório", "target": 3500.00, "current": 1200.00, "percentage": 34.2}
    ],
    "recent_transactions": [
        {"description": "Supermercado Carrefour", "amount": -450.20, "category": "Alimentação", "date": "10/06/2026", "user": "Mariana"},
        {"description": "Salário Mensal", "amount": 12500.00, "category": "Receita", "date": "05/06/2026", "user": "Empresa"},
        {"description": "Conta de Energia (Enel)", "amount": -280.30, "category": "Habitação", "date": "03/06/2026", "user": "Rodrigo"},
        {"description": "Mensalidade Faculdade (Mariana)", "amount": -950.00, "category": "Educação", "date": "03/06/2026", "user": "Mariana"},
        {"description": "Netflix Mensal", "amount": -55.90, "category": "Lazer", "date": "01/06/2026", "user": "Família"}
    ]
}

CALENDAR_EVENTS = [
    {"title": "Almoço de Domingo na Vó", "date": "2026-06-14", "time": "12:30", "user": "Família", "color": "#5f27cd", "category": "Familiar"},
    {"title": "Dentista Mariana", "date": "2026-06-15", "time": "14:00", "user": "Mariana", "color": "#00d2d3", "category": "Saúde"},
    {"title": "Reunião de Condomínio", "date": "2026-06-17", "time": "20:00", "user": "Rodrigo", "color": "#ff9f43", "category": "Compromisso"},
    {"title": "Vacina do Pipoca (Pet)", "date": "2026-06-20", "time": "09:00", "user": "Família", "color": "#54a0ff", "category": "Pet"},
    {"title": "Aniversário do Lucas", "date": "2026-06-25", "time": "18:00", "user": "Lucas", "color": "#ff4d4d", "category": "Familiar"}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/nas-status')
def get_nas_status():
    # Detect local drive information if possible, otherwise return config-based mock NAS details
    try:
        drive_letter = os.path.splitdrive(os.path.abspath(__file__))[0] or "E:"
    except Exception:
        drive_letter = "E:"
        
    return jsonify({
        "status": "Online",
        "connection_type": "USB 3.0 (Adaptador NVMe)",
        "drive_letter": drive_letter,
        "disk_total_gb": 1024,
        "disk_used_gb": 184,
        "disk_free_gb": 840,
        "disk_percentage": 18.0,
        "temperature_c": 38,
        "device_model": "Crucial P3 Plus NVMe SSD"
    })



@app.route('/api/financas')
def get_financas():
    from modules.ia_memoria.database import get_all_transactions
    transactions = get_all_transactions()
    
    # Calculate summary dynamically
    income = sum(t["amount"] for t in transactions if t["amount"] > 0 and t.get("pago", 1) == 1)
    expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0 and t.get("pago", 1) == 1)
    savings = income - expenses
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0.0
    
    # Categories breakdown
    categories_map = {
        "Habitação (Aluguel/Contas)": {"value": 0.0, "color": "#ff4d4d"},
        "Educação": {"value": 0.0, "color": "#111827"},
        "Alimentação e Supermercado": {"value": 0.0, "color": "#ff9f43"},
        "Saúde e Planos": {"value": 0.0, "color": "#00d2d3"},
        "Transporte/Combustível": {"value": 0.0, "color": "#54a0ff"},
        "Lazer e Streaming": {"value": 0.0, "color": "#5f27cd"},
        "Outros": {"value": 0.0, "color": "#c8d6e5"}
    }
    
    category_mapping = {
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
    
    for t in transactions:
        if t["amount"] < 0 and t.get("pago", 1) == 1:
            cat_key = category_mapping.get(t["category"].lower(), "Outros")
            categories_map[cat_key]["value"] += abs(t["amount"])
            
    # Format categories list
    categories_list = []
    total_expense = sum(c["value"] for c in categories_map.values())
    for name, info in categories_map.items():
        percentage = round((info["value"] / total_expense * 100)) if total_expense > 0 else 0
        categories_list.append({
            "name": name,
            "value": round(info["value"], 2),
            "percentage": percentage,
            "color": info["color"]
        })
        
    savings_goals = [
        {"title": "Viagem de Fim de Ano", "target": 8000.00, "current": min(5400.00 + max(0.0, savings - 4079.50), 8000.00), "percentage": 0.0},
        {"title": "Reforma do Escritório", "target": 3500.00, "current": 1200.00, "percentage": 34.2}
    ]
    savings_goals[0]["percentage"] = round((savings_goals[0]["current"] / savings_goals[0]["target"] * 100), 1)
    
    financial_data = {
        "summary": {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings": round(savings, 2),
            "savings_rate": savings_rate
        },
        "categories": categories_list,
        "savings_goals": savings_goals,
        "recent_transactions": transactions[:10]
    }
    return jsonify(financial_data)

@app.route('/api/calendario')
def get_calendario():
    from modules.ia_memoria.database import get_db_connection, DATABASE_PATH
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    # Query events left joined with tasks to get task completion status and rewards
    cursor.execute('''
        SELECT 
            e.id, e.titulo, e.data, e.hora, e.responsavel, e.cor, e.categoria, 
            e.google_event_id, e.localizacao, e.recorrencia,
            t.id AS task_id, t.completed AS task_completed, t.reward_xp, t.reward_gold
        FROM eventos e
        LEFT JOIN tarefas t ON e.id = t.evento_calendario_id
    ''')
    rows = cursor.fetchall()
    conn.close()
    
    mapped_events = []
    for r in rows:
        is_task = r["task_id"] is not None
        mapped_events.append({
            "id": r["id"],
            "title": r["titulo"],
            "date": r["data"],
            "time": r["hora"],
            "user": r["responsavel"],
            "color": r["cor"],
            "category": r["categoria"],
            "google_event_id": r["google_event_id"],
            "localizacao": r["localizacao"],
            "recorrencia": r["recorrencia"],
            "is_task": is_task,
            "task_id": r["task_id"],
            "completed": bool(r["task_completed"]) if is_task else False,
            "reward_xp": r["reward_xp"],
            "reward_gold": r["reward_gold"]
        })
    return jsonify(mapped_events)

@app.route('/api/calendario/sync', methods=['POST'])
def sync_calendario_route():
    from modules.ia_memoria.google_calendar import sync_calendars
    import os
    
    # Check if credentials exist
    root_dir = os.path.dirname(os.path.abspath(__file__))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    if not os.path.exists(credentials_path):
        return jsonify({
            "success": False, 
            "error": "Arquivo 'credentials.json' não encontrado na raiz do projeto. Por favor, configure as credenciais da conta de serviço para sincronizar."
        }), 400
        
    from modules.ia_memoria.google_calendar import LAST_SYNC_ERROR
    success = sync_calendars()
    if success:
        return jsonify({"success": True, "message": "Calendário sincronizado com o Google com sucesso!"})
    else:
        err_msg = LAST_SYNC_ERROR or "Erro desconhecido durante a sincronização."
        if "Google Calendar API has not been used" in err_msg or "accessNotConfigured" in err_msg:
            err_msg = (
                "A API do Google Calendar está desativada no seu projeto do Google Cloud. "
                "Ative-a clicando no link: https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview?project=281421242488"
            )
        return jsonify({"success": False, "error": err_msg}), 500

@app.route('/api/calendario/salvar', methods=['POST'])
def save_or_update_event_route():
    data = request.json or {}
    event_id = data.get("id")
    titulo = data.get("titulo", "").strip()
    data_evt = data.get("data", "").strip()
    hora = data.get("hora", "").strip()
    responsavel = data.get("responsavel", "Família").strip()
    cor = data.get("cor", "#5f27cd").strip()
    categoria = data.get("categoria", "Familiar").strip()
    localizacao = data.get("localizacao", "").strip() or None
    recorrencia = data.get("recorrencia", "").strip() or None
    
    if not titulo or not data_evt or not hora:
        return jsonify({"success": False, "error": "Título, Data e Hora são obrigatórios."}), 400
        
    from modules.ia_memoria.database import save_event, update_event, get_all_events
    from modules.ia_memoria.google_calendar import push_event_to_google_background, update_event_in_google_background
    
    if event_id:
        update_event(
            event_id=event_id,
            titulo=titulo,
            data=data_evt,
            hora=hora,
            responsavel=responsavel,
            cor=cor,
            categoria=categoria,
            localizacao=localizacao,
            recorrencia=recorrencia
        )
        
        events = get_all_events()
        curr_evt = next((e for e in events if e["id"] == event_id), None)
        if curr_evt and curr_evt.get("google_event_id"):
            update_event_in_google_background(
                google_event_id=curr_evt["google_event_id"],
                event_title=titulo,
                event_date=data_evt,
                event_time=hora,
                localizacao=localizacao,
                recorrencia=recorrencia
            )
        return jsonify({"success": True, "message": "Compromisso atualizado com sucesso!"})
    else:
        new_id = save_event(
            titulo=titulo,
            data=data_evt,
            hora=hora,
            responsavel=responsavel,
            cor=cor,
            categoria=categoria,
            localizacao=localizacao,
            recorrencia=recorrencia
        )
        push_event_to_google_background(new_id, titulo, data_evt, hora, localizacao, recorrencia)
        return jsonify({"success": True, "message": "Compromisso cadastrado com sucesso!"})

@app.route('/api/calendario/excluir', methods=['POST'])
def delete_event_route():
    data = request.json or {}
    event_id = data.get("id")
    if not event_id:
        return jsonify({"success": False, "error": "ID do evento é obrigatório."}), 400
        
    from modules.ia_memoria.database import delete_event, get_all_events
    from modules.ia_memoria.google_calendar import delete_event_from_google_background
    
    events = get_all_events()
    curr_evt = next((e for e in events if e["id"] == event_id), None)
    
    delete_event(event_id)
    
    if curr_evt and curr_evt.get("google_event_id"):
        delete_event_from_google_background(curr_evt["google_event_id"])
        
    return jsonify({"success": True, "message": "Compromisso excluído com sucesso!"})


@app.route('/api/todo-gamer')
def get_todo_gamer():
    from modules.ia_memoria.database import get_all_users, get_all_tasks, get_all_rewards
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    return jsonify({
        "character": users[0] if users else {},
        "profiles": users,
        "quests": tasks,
        "rewards": rewards
    })

@app.route('/api/todo-gamer/complete', methods=['POST'])
def complete_quest():
    data = request.json or {}
    quest_id = data.get("quest_id")
    if not quest_id:
        return jsonify({"error": "ID da missão não fornecido."}), 400
        
    from modules.ia_memoria.database import complete_task_in_db, get_all_users, get_all_tasks, get_all_rewards
    
    # Get rewards before completion for return payload
    tasks_all = get_all_tasks()
    quest = next((t for t in tasks_all if t['id'] == quest_id), None)
    if not quest:
        return jsonify({"error": "Missão não encontrada."}), 404
        
    success, user_profile, leveled_up = complete_task_in_db(quest_id)
    if not success:
        return jsonify({"error": "Missão já concluída anteriormente."}), 400
        
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "message": "Missão concluída com sucesso! Recompensas creditadas.",
        "leveled_up": leveled_up,
        "reward_xp": quest["reward_xp"],
        "reward_gold": quest["reward_gold"],
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/reset', methods=['POST'])
def reset_quests():
    from modules.ia_memoria.database import reset_tasks_db, get_all_users, get_all_tasks, get_all_rewards
    reset_tasks_db()
    
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "message": "Missões reiniciadas!",
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/redeem', methods=['POST'])
def redeem_reward_route():
    data = request.json or {}
    reward_id = data.get("reward_id")
    if not reward_id:
        return jsonify({"error": "ID da recompensa é obrigatório."}), 400
        
    from modules.ia_memoria.database import redeem_reward_in_db, get_all_users, get_all_tasks, get_all_rewards
    success, msg, user_profile = redeem_reward_in_db(reward_id)
    if not success:
        return jsonify({"error": msg}), 400
        
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "message": msg,
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/complete-reward', methods=['POST'])
def complete_reward_route_api():
    data = request.json or {}
    reward_id = data.get("reward_id")
    if not reward_id:
        return jsonify({"error": "ID da recompensa é obrigatório."}), 400
        
    from modules.ia_memoria.database import complete_reward_in_db, get_all_users, get_all_tasks, get_all_rewards
    complete_reward_in_db(reward_id)
    
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "message": "Recompensa concluída com sucesso!",
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/add-reward', methods=['POST'])
def add_reward_route():
    data = request.json or {}
    reward_id = data.get("id")
    user_nome = data.get("usuario_nome")
    titulo = data.get("titulo")
    custo = data.get("custo")
    icone = data.get("icone")
    
    if not user_nome or not titulo or not custo or not icone:
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
    from modules.ia_memoria.database import save_reward, update_reward_in_db, get_all_users, get_all_tasks, get_all_rewards
    
    if reward_id:
        update_reward_in_db(reward_id, user_nome, titulo, int(custo), icone)
        msg = "Recompensa atualizada com sucesso!"
    else:
        save_reward(user_nome, titulo, int(custo), icone)
        msg = "Recompensa criada com sucesso!"
        
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "success": True,
        "message": msg,
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/excluir-recompensa', methods=['POST'])
def delete_reward_route():
    data = request.json or {}
    reward_id = data.get("id")
    if not reward_id:
        return jsonify({"error": "ID da recompensa é obrigatório."}), 400
        
    from modules.ia_memoria.database import delete_reward_in_db, get_all_users, get_all_tasks, get_all_rewards
    delete_reward_in_db(reward_id)
    
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "success": True,
        "message": "Recompensa excluída com sucesso!",
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/salvar', methods=['POST'])
def save_or_update_quest_route():
    data = request.json or {}
    quest_id = data.get("id")
    usuario_nome = data.get("usuario_nome", "Mari").strip()
    titulo = data.get("titulo", "").strip()
    categoria = data.get("categoria", "Limpeza").strip()
    dificuldade = data.get("dificuldade", "Fácil").strip()
    
    try:
        reward_xp = int(data.get("reward_xp", 10))
        reward_gold = int(data.get("reward_gold", 3))
    except ValueError:
        return jsonify({"error": "XP e Gold devem ser números inteiros."}), 400
        
    data_evt = data.get("data", "").strip()
    hora = data.get("hora", "").strip()
    
    if not titulo or not data_evt or not hora:
        return jsonify({"error": "Nome da missão, Data e Hora são obrigatórios."}), 400
        
    from modules.ia_memoria.database import save_task, update_task_in_db, get_all_users, get_all_tasks, get_all_rewards
    
    if quest_id:
        update_task_in_db(
            task_id=quest_id,
            usuario_nome=usuario_nome,
            titulo=titulo,
            categoria=categoria,
            dificuldade=dificuldade,
            reward_xp=reward_xp,
            reward_gold=reward_gold,
            data=data_evt,
            hora=hora
        )
        msg = "Missão atualizada com sucesso!"
    else:
        save_task(
            usuario_nome=usuario_nome,
            titulo=titulo,
            categoria=categoria,
            dificuldade=dificuldade,
            reward_xp=reward_xp,
            reward_gold=reward_gold,
            data=data_evt,
            hora=hora
        )
        msg = "Missão criada com sucesso!"
        
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "success": True,
        "message": msg,
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/todo-gamer/excluir', methods=['POST'])
def delete_quest_route():
    data = request.json or {}
    quest_id = data.get("id")
    if not quest_id:
        return jsonify({"error": "ID da missão é obrigatório."}), 400
        
    from modules.ia_memoria.database import delete_task_in_db, get_all_users, get_all_tasks, get_all_rewards
    delete_task_in_db(quest_id)
    
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    return jsonify({
        "success": True,
        "message": "Missão excluída com sucesso!",
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@app.route('/api/financas/despesas', methods=['GET', 'POST'])
def gerenciar_despesas():
    from modules.ia_memoria.database import get_all_despesas, save_despesa
    
    if request.method == 'POST':
        data = request.json
        save_despesa(
            data['descricao'], 
            data['valor'], 
            data['categoria'], 
            data['dia_vencimento'], 
            data['tipo'], 
            data.get('total_parcelas', 1)
        )
        return jsonify({"success": True, "message": "Despesa registrada!"})
    
    return jsonify(get_all_despesas())

@app.route('/api/financas/despesas/editar', methods=['POST'])
def editar_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import update_despesa
        update_despesa(
            data['id'], data['descricao'], data['valor'], data['categoria'], 
            data['dia_vencimento'], data['tipo'], data.get('total_parcelas', 1)
        )
        return jsonify({"success": True, "message": "Despesa atualizada!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/financas/despesas/excluir', methods=['POST'])
def excluir_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import delete_despesa
        delete_despesa(data['id'])
        return jsonify({"success": True, "message": "Despesa excluída!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/financas/despesas/pago', methods=['POST'])
def toggle_pago_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import toggle_despesa_pago
        toggle_despesa_pago(data['id'], data['pago'])
        return jsonify({"success": True, "message": "Status de pagamento atualizado!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/financas/transacoes', methods=['POST'])
def adicionar_transacao_manual():
    data = request.json
    try:
        from modules.ia_memoria.database import save_transaction_to_db
        import datetime
        
        descricao = data['descricao'].strip()
        valor = float(data['valor'])
        tipo = data['tipo'] # 'entrada' or 'saida'
        categoria = data['categoria']
        responsavel = data.get('responsavel', 'Família')
        pago = int(data.get('pago', 1))
        
        if tipo == 'saida':
            valor = -abs(valor)
        else:
            valor = abs(valor)
            
        raw_date = data.get('data') # e.g. "2026-06-22"
        if raw_date:
            try:
                dt = datetime.datetime.strptime(raw_date, '%Y-%m-%d')
                date_str = dt.strftime('%d/%m/%Y')
            except Exception:
                date_str = datetime.date.today().strftime('%d/%m/%Y')
        else:
            date_str = datetime.date.today().strftime('%d/%m/%Y')
            
        save_transaction_to_db(descricao, valor, categoria, date_str, responsavel, pago)
        return jsonify({"success": True, "message": "Transação registrada com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/financas/transacoes/excluir', methods=['POST'])
def excluir_transacao_manual():
    data = request.json
    try:
        from modules.ia_memoria.database import delete_transaction_from_db
        delete_transaction_from_db(data['id'])
        return jsonify({"success": True, "message": "Transação excluída com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    # Initialize SQLite database
    init_db()
    
    # Start the server on port 5000. host='0.0.0.0' allows access from other devices in the local network!
    print("Iniciando Dashboard Familiar no NVMe local...")
    app.run(host='0.0.0.0', port=5000, debug=True)
