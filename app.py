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
    return jsonify(FINANCIAL_DATA)

@app.route('/api/calendario')
def get_calendario():
    from modules.ia_memoria.database import get_all_events
    events = get_all_events()
    mapped_events = []
    for e in events:
        mapped_events.append({
            "id": e.get("id"),
            "title": e.get("titulo"),
            "date": e.get("data"),
            "time": e.get("hora"),
            "user": e.get("responsavel"),
            "color": e.get("cor"),
            "category": e.get("categoria"),
            "google_event_id": e.get("google_event_id")
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

@app.route('/api/todo-gamer')
def get_todo_gamer():
    return jsonify(GAMES_STATE)

@app.route('/api/todo-gamer/complete', methods=['POST'])
def complete_quest():
    data = request.json or {}
    quest_id = data.get("quest_id")
    
    quest = next((q for q in GAMES_STATE["quests"] if q["id"] == quest_id), None)
    if not quest:
        return jsonify({"error": "Missão não encontrada."}), 404
        
    if quest["completed"]:
        return jsonify({"message": "Missão já concluída anteriormente!", "state": GAMES_STATE})
        
    # Mark completed and apply rewards
    quest["completed"] = True
    char = GAMES_STATE["character"]
    char["xp"] += quest["reward_xp"]
    char["gold"] += quest["reward_gold"]
    
    # Level up logic
    leveled_up = False
    while char["xp"] >= char["xp_to_next_level"]:
        char["xp"] -= char["xp_to_next_level"]
        char["level"] += 1
        char["xp_to_next_level"] = int(char["xp_to_next_level"] * 1.2) # Escalation
        leveled_up = True
        
    return jsonify({
        "message": "Missão concluída com sucesso! Recompensas creditadas.",
        "leveled_up": leveled_up,
        "reward_xp": quest["reward_xp"],
        "reward_gold": quest["reward_gold"],
        "state": GAMES_STATE
    })

@app.route('/api/todo-gamer/reset', methods=['POST'])
def reset_quests():
    # Simple route to reset quests for demonstration/testing
    for quest in GAMES_STATE["quests"]:
        quest["completed"] = False
    return jsonify({"message": "Missões reiniciadas!", "state": GAMES_STATE})

if __name__ == '__main__':
    # Initialize SQLite database
    init_db()
    
    # Start the server on port 5000. host='0.0.0.0' allows access from other devices in the local network!
    print("Iniciando Dashboard Familiar no NVMe local...")
    app.run(host='0.0.0.0', port=5000, debug=True)
