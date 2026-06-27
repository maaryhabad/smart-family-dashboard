from flask import Blueprint, jsonify, request

todo_gamer_bp = Blueprint('todo_gamer', __name__)

@todo_gamer_bp.route('/api/todo-gamer')
def get_todo_gamer():
    from modules.ia_memoria.database import get_all_users, get_all_tasks, get_all_rewards, consolidate_tasks_db
    consolidate_tasks_db()
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    return jsonify({
        "character": users[0] if users else {},
        "profiles": users,
        "quests": tasks,
        "rewards": rewards
    })

@todo_gamer_bp.route('/api/todo-gamer/complete', methods=['POST'])
def complete_quest():
    data = request.json or {}
    quest_id = data.get("quest_id")
    skip = data.get("skip", False)
    if not quest_id:
        return jsonify({"error": "ID da missão não fornecido."}), 400
        
    from modules.ia_memoria.database import complete_task_in_db, get_all_users, get_all_tasks, get_all_rewards
    
    # Get rewards before completion for return payload
    tasks_all = get_all_tasks()
    quest = next((t for t in tasks_all if t['id'] == quest_id), None)
    if not quest:
        return jsonify({"error": "Missão não encontrada."}), 404
        
    success, user_profile, leveled_up = complete_task_in_db(quest_id, skip=skip)
    if not success:
        return jsonify({"error": "Missão já concluída anteriormente."}), 400
        
    users = get_all_users()
    tasks = get_all_tasks()
    rewards = get_all_rewards()
    
    reward_xp = 0 if skip else quest["reward_xp"]
    reward_gold = 0 if skip else quest["reward_gold"]
    
    return jsonify({
        "message": "Missão marcada como concluída/pulada." if skip else "Missão concluída com sucesso! Recompensas creditadas.",
        "leveled_up": leveled_up,
        "reward_xp": reward_xp,
        "reward_gold": reward_gold,
        "state": {
            "character": users[0] if users else {},
            "profiles": users,
            "quests": tasks,
            "rewards": rewards
        }
    })

@todo_gamer_bp.route('/api/todo-gamer/reset', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/redeem', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/complete-reward', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/add-reward', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/excluir-recompensa', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/salvar', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/excluir', methods=['POST'])
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

@todo_gamer_bp.route('/api/todo-gamer/usuario/cadastrar', methods=['POST'])
def cadastrar_usuario_route():
    data = request.json or {}
    nome = data.get("nome", "").strip()
    avatar = data.get("avatar", "👤").strip()
    classe = data.get("classe", "Aventureiro").strip()
    idade = data.get("idade")
    telefone = data.get("telefone")
    
    if not nome:
        return jsonify({"success": False, "error": "Nome/Apelido é obrigatório."}), 400
        
    if idade is not None and idade != "":
        try:
            idade = int(idade)
        except ValueError:
            return jsonify({"success": False, "error": "Idade deve ser um número inteiro."}), 400
    else:
        idade = None
        
    if not telefone or telefone.strip() == "":
        telefone = None
    else:
        telefone = telefone.strip()
        
    from modules.ia_memoria.database import save_user, get_all_users
    success, msg = save_user(nome, avatar, classe, idade, telefone)
    if not success:
        return jsonify({"success": False, "error": msg}), 400
        
    # Return updated list of profiles
    users = get_all_users()
    return jsonify({
        "success": True,
        "message": msg,
        "profiles": users
    })
