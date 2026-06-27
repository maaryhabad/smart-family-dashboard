from flask import Blueprint, jsonify, request
import os

calendario_bp = Blueprint('calendario', __name__)

@calendario_bp.route('/api/calendario')
def get_calendario():
    from modules.ia_memoria.database import get_db_connection, DATABASE_PATH
    conn = get_db_connection(DATABASE_PATH)
    cursor = conn.cursor()
    # Query events left joined with tasks to get task completion status and rewards
    cursor.execute('''
        SELECT 
            e.id, e.titulo, e.data, e.hora, e.responsavel, e.cor, e.categoria, 
            e.google_event_id, e.localizacao, e.recorrencia, e.data_fim, e.hora_fim,
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
            "data_fim": r["data_fim"],
            "hora_fim": r["hora_fim"],
            "is_task": is_task,
            "task_id": r["task_id"],
            "completed": bool(r["task_completed"]) if is_task else False,
            "reward_xp": r["reward_xp"],
            "reward_gold": r["reward_gold"]
        })
    return jsonify(mapped_events)

@calendario_bp.route('/api/calendario/sync', methods=['POST'])
def sync_calendario_route():
    from modules.ia_memoria.google_calendar import sync_calendars, LAST_SYNC_ERROR
    
    # Check if credentials exist
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    credentials_path = os.path.join(root_dir, 'credentials.json')
    if not os.path.exists(credentials_path):
        return jsonify({
            "success": False, 
            "error": "Arquivo 'credentials.json' não encontrado na raiz do projeto. Por favor, configure as credenciais da conta de serviço para sincronizar."
        }), 400
        
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

@calendario_bp.route('/api/calendario/salvar', methods=['POST'])
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
    data_fim = data.get("data_fim", "").strip() or None
    hora_fim = data.get("hora_fim", "").strip() or None
    
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
            recorrencia=recorrencia,
            data_fim=data_fim,
            hora_fim=hora_fim
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
                recorrencia=recorrencia,
                data_fim=data_fim,
                hora_fim=hora_fim
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
            recorrencia=recorrencia,
            data_fim=data_fim,
            hora_fim=hora_fim
        )
        push_event_to_google_background(new_id, titulo, data_evt, hora, localizacao, recorrencia, data_fim, hora_fim)
        return jsonify({"success": True, "message": "Compromisso cadastrado com sucesso!"})

@calendario_bp.route('/api/calendario/excluir', methods=['POST'])
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
