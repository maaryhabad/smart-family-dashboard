from flask import Blueprint, jsonify, request
import os
import json
import threading
import subprocess
from .database import (
    get_all_memories, save_memory, delete_memory, update_memory,
    get_all_events, save_event, delete_event, update_event_google_id,
    get_all_users, get_user_by_name, get_all_tasks, get_tasks_for_user,
    complete_task_in_db, get_all_rewards, get_rewards_for_user,
    redeem_reward_in_db, reset_tasks_db
)
from .nlp_engine import (
    search_best_memory, classify_category, tokenize, 
    format_list_to_bullets, parse_intent_with_ollama,
    clean_item_name
)

ia_memoria_bp = Blueprint('ia_memoria', __name__)
is_retraining_model = False

def extract_date_from_text(text):
    import re
    import datetime
    text_lower = text.lower().strip()
    
    # 1. Relative terms
    if 'amanhã' in text_lower or 'amanha' in text_lower:
        return (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    if 'hoje' in text_lower:
        return datetime.date.today().strftime("%Y-%m-%d")
        
    # 2. ISO format YYYY-MM-DD
    m_iso = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', text)
    if m_iso:
        return m_iso.group(0)
        
    # 3. Brazilian format DD/MM/YYYY or DD/MM
    m_br = re.search(r'\b(\d{2})/(\d{2})(?:/(\d{4}))?\b', text)
    if m_br:
        day = m_br.group(1)
        month = m_br.group(2)
        year = m_br.group(3) if m_br.group(3) else "2026"  # Mock current year
        return f"{year}-{month}-{day}"
        
    return None

def parse_recipe_details(message):
    # Convert to lowercase to find keywords, but keep original case for content extraction
    msg_lower = message.lower()
    
    prefixes = [
        # registrar
        "registrar a receita de ", "registrar a receita ", "registrar receita de ", "registrar receita ",
        "registra essa receita de ", "registra essa receita ", "registra a receita de ", "registra a receita ", "registra receita de ", "registra receita ",
        # salvar
        "salvar a receita de ", "salvar a receita ", "salvar receita de ", "salvar receita ",
        "salva essa receita de ", "salva essa receita ", "salva a receita de ", "salva a receita ", "salva receita de ", "salva receita ",
        "salve essa receita de ", "salve essa receita ", "salve a receita de ", "salve a receita ", "salve receita de ", "salve receita ",
        # cadastrar
        "cadastrar a receita de ", "cadastrar a receita ", "cadastrar receita de ", "cadastrar receita ",
        "cadastra essa receita de ", "cadastra essa receita ", "cadastra a receita de ", "cadastra a receita ", "cadastra receita de ", "cadastra receita ",
        # adicionar
        "adicionar a receita de ", "adicionar a receita ", "adicionar receita de ", "adicionar receita ",
        "adiciona essa receita de ", "adiciona essa receita ", "adiciona a receita de ", "adiciona a receita ", "adiciona receita de ", "adiciona receita ",
        # anotar
        "anote essa receita de ", "anote essa receita ", "anote a receita de ", "anote a receita ", "anote receita de ", "anote receita ",
        "anota essa receita de ", "anota essa receita ", "anota a receita de ", "anota a receita ", "anota receita de ", "anota receita ",
        # editar / alterar / atualizar / modificar
        "editar a receita de ", "editar a receita ", "editar receita de ", "editar receita ",
        "alterar a receita de ", "alterar a receita ", "alterar receita de ", "alterar receita ",
        "atualizar a receita de ", "atualizar a receita ", "atualizar receita de ", "atualizar receita ",
        "modificar a receita de ", "modificar a receita ", "modificar receita de ", "modificar receita "
    ]
    
    prefix_found = None
    for p in prefixes:
        if msg_lower.startswith(p):
            prefix_found = p
            break
            
    if not prefix_found:
        for p in prefixes:
            idx = msg_lower.find(p)
            if idx != -1:
                message = message[idx:]
                msg_lower = message.lower()
                prefix_found = p
                break
                
    if not prefix_found:
        # Fallback for raw pasted recipes without standard prefixes
        # Check if the message contains instructions/preparation keywords AND ingredients indicators
        has_inst = any(kw in msg_lower for kw in ['passo a passo', 'modo de preparo', 'preparo', 'instrucoes', 'instruções', 'modo de fazer'])
        has_ing = any(kw in msg_lower for kw in ['ingredientes', 'farinha', 'açúcar', 'acucar', 'leite', 'ovo', 'ovos', 'colher', 'chá', 'cha', 'g de', 'ml de', 'gramas', 'fermento'])
        
        if has_inst and has_ing:
            # We treat the whole message as the recipe
            # Try to determine a name from the first non-empty line
            lines = [line.strip() for line in message.split('\n') if line.strip()]
            recipe_name = "Receita"
            if lines:
                first_line = lines[0]
                first_line_clean = first_line.strip('🥣:-*• \t')
                if len(first_line_clean) < 60 and not any(k in first_line_clean.lower() for k in ['ingredientes', 'passo a passo', 'modo de preparo']):
                    recipe_name = first_line_clean
                    
            after_prefix = message.strip()
            after_prefix_lower = after_prefix.lower()
        else:
            return None
    else:
        after_prefix = message[len(prefix_found):].strip()
        after_prefix_lower = after_prefix.lower()
        
    # End of recipe name is colon, newline or key terms
    if prefix_found:
        end_idx = len(after_prefix)
        for sep in [':', '\n', 'ingredientes', 'passo a passo', 'modo de preparo', 'preparo']:
            idx = after_prefix_lower.find(sep)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        recipe_name = after_prefix[:end_idx].strip()
        recipe_name = recipe_name.strip(',. ')
        content_part = after_prefix[end_idx:].strip()
    else:
        # For raw pasted recipes, name is already parsed from first line, so content_part is the rest of the message
        first_line_len = message.find('\n')
        if first_line_len != -1:
            content_part = message[first_line_len:].strip()
        else:
            content_part = message.strip()
            
    while content_part and content_part[0] in [':', ',', '.', ' ', '-', '\n']:
        content_part = content_part[1:].strip()
        
    content_part_lower = content_part.lower()
    
    inst_idx = -1
    for inst_kw in ['passo a passo', 'modo de preparo', 'preparo', 'instrucoes', 'instruções', 'modo de fazer']:
        idx = content_part_lower.find(inst_kw)
        if idx != -1:
            inst_idx = idx
            break
            
    ingredients_text = ""
    instructions_text = ""
    
    if inst_idx != -1:
        ingredients_part = content_part[:inst_idx].strip()
        instructions_part = content_part[inst_idx:].strip()
        
        # Clean "ingredientes" header from ingredients_part if present
        ing_part_lower = ingredients_part.lower()
        ing_header_idx = ing_part_lower.find('ingredientes')
        if ing_header_idx != -1:
            ingredients_text = ingredients_part[ing_header_idx + len('ingredientes'):].strip()
        else:
            ingredients_text = ingredients_part
            
        while ingredients_text and ingredients_text[0] in [':', ',', '.', ' ', '-', '\n']:
            ingredients_text = ingredients_text[1:].strip()
            
        # Clean preparation header from instructions_part
        while instructions_part and not instructions_part[0].isalnum():
            instructions_part = instructions_part[1:].strip()
            
        inst_part_lower = instructions_part.lower()
        matched_kw = None
        for inst_kw in ['passo a passo', 'modo de preparo', 'preparo', 'instrucoes', 'instruções', 'modo de fazer']:
            if inst_part_lower.startswith(inst_kw):
                matched_kw = inst_kw
                break
        start_inst = len(matched_kw) if matched_kw else 0
        instructions_text = instructions_part[start_inst:].strip()
        while instructions_text and instructions_text[0] in [':', ',', '.', ' ', '-', '\n', '🥣']:
            instructions_text = instructions_text[1:].strip()
    else:
        # No instructions header, treat everything as ingredients
        ingredients_part = content_part.strip()
        ing_part_lower = ingredients_part.lower()
        ing_header_idx = ing_part_lower.find('ingredientes')
        if ing_header_idx != -1:
            ingredients_text = ingredients_part[ing_header_idx + len('ingredientes'):].strip()
        else:
            ingredients_text = ingredients_part
        while ingredients_text and ingredients_text[0] in [':', ',', '.', ' ', '-', '\n']:
            ingredients_text = ingredients_text[1:].strip()
        instructions_text = ""
        
    return {
        'nome': recipe_name,
        'ingredientes': ingredients_text,
        'passo_a_passo': instructions_text
    }

def format_recipe_content(ingredients, instructions):
    formatted = "Ingredientes:\n"
    if '\n' in ingredients:
        items = [i.strip() for i in ingredients.split('\n') if i.strip()]
    else:
        items = [i.strip() for i in ingredients.split(',') if i.strip()]
        
    for item in items:
        while item and item[0] in ['-', '*', '•', ' ']:
            item = item[1:].strip()
        if item:
            item = item[0].upper() + item[1:]
            formatted += f"- {item}\n"
            
    if instructions:
        formatted += "\nPasso a passo:\n"
        if '\n' in instructions:
            steps = [s.strip() for s in instructions.split('\n') if s.strip()]
        else:
            steps = [s.strip() for s in instructions.split('.') if s.strip()]
            
        for idx, step in enumerate(steps):
            import re
            step = re.sub(r'^\d+[\.\-\s\)]+', '', step).strip()
            while step and step[0] in ['-', '*', '•', ' ']:
                step = step[1:].strip()
            if step:
                step = step[0].upper() + step[1:]
                formatted += f"{idx+1}. {step}\n"
                
    return formatted.strip()

def parse_intent_locally(message):
    """
    Fallback local parser using keyword/regex matching.
    Returns (intent, detalhes) or (None, None).
    """
    msg = message.lower().strip()
    
    # 0. Wildcard calendar deletion (e.g. "desmarcar todos os compromissos de amanhã")
    delete_keywords = ['desmarcar', 'cancelar', 'remover', 'deletar', 'limpar', 'excluir', 'apagar', 'desmarca', 'cancela', 'remove', 'deleta', 'limpa', 'exclui', 'apaga']
    wildcard_keywords = ['todos', 'tudo', 'todas', 'agenda']
    has_delete = any(kw in msg for kw in delete_keywords)
    has_wildcard = any(kw in msg for kw in wildcard_keywords)
    if has_delete and has_wildcard:
        extracted_date = extract_date_from_text(msg)
        if extracted_date:
            return 'remover_calendario', {'titulo': None, 'data': extracted_date}
            
    # 0.5. Recipe-related intents
    # Delete recipe
    if 'receita' in msg and any(kw in msg for kw in ['deletar', 'excluir', 'apagar', 'remover', 'deleta', 'exclui', 'apaga', 'remove']):
        del_triggers = [
            "deletar receita de ", "deletar receita ", "deletar a receita de ", "deletar a receita ",
            "excluir receita de ", "excluir receita ", "excluir a receita de ", "excluir a receita ",
            "apagar receita de ", "apagar receita ", "apagar a receita de ", "apagar a receita ",
            "remover receita de ", "remover receita ", "remover a receita de ", "remover a receita "
        ]
        for dt in del_triggers:
            idx = msg.find(dt)
            if idx != -1:
                recipe_name = msg[idx + len(dt):].strip()
                recipe_name = recipe_name.strip('?. ')
                if recipe_name:
                    return 'deletar_receita', {'receita': recipe_name}
                    
    # Save/Edit recipe
    is_recipe_action = 'receita' in msg and any(kw in msg for kw in ['salvar', 'registrar', 'cadastrar', 'adicionar', 'editar', 'alterar', 'atualizar', 'modificar'])
    is_raw_recipe = any(kw in msg for kw in ['modo de preparo', 'passo a passo', 'modo de fazer', 'instrucoes', 'instruções']) and any(kw in msg for kw in ['ingredientes', 'farinha', 'açúcar', 'acucar', 'leite', 'ovo', 'ovos', 'colher', 'fermento'])
    if is_recipe_action or is_raw_recipe:
        recipe_details = parse_recipe_details(message)
        if recipe_details:
            return 'salvar_receita', recipe_details
            
    # Shopping list from recipe (e.g. "Quero fazer panqueca de aveia, o que preciso comprar?")
    if 'fazer' in msg or 'comprar' in msg or 'receita' in msg:
        triggers = [
            "quero fazer ", "vou fazer ", "o que preciso comprar para fazer ", "o que preciso comprar pra fazer ",
            "o que preciso comprar para ", "o que preciso comprar pra ", "o que comprar para fazer ", "o que comprar pra fazer ",
            "o que comprar para ", "o que comprar pra ", "ingredientes para fazer ", "ingredientes pra fazer ",
            "ingredientes para ", "ingredientes pra ", "fazer a receita de ", "fazer receita de ", "fazer a receita ",
            "fazer receita "
        ]
        for t in triggers:
            idx = msg.find(t)
            if idx != -1:
                recipe_name = msg[idx + len(t):].strip()
                for question_sep in [', o que', ', oq', ' o que', ' oq', '?', ',']:
                    q_idx = recipe_name.find(question_sep)
                    if q_idx != -1:
                        recipe_name = recipe_name[:q_idx].strip()
                recipe_name = recipe_name.strip('?. ')
                if recipe_name:
                    return 'comprar_receita', {'receita': recipe_name}
    
    # 1. Completar tarefa
    complete_keywords = ['completei', 'conclui', 'concluí', 'terminei', 'feita', 'feito', 'marcar como feita', 'concluir', 'terminou', 'concluiu', 'completou']
    is_complete = any(kw in msg for kw in complete_keywords)
    if is_complete:
        user = None
        if 'isa' in msg:
            user = 'Isa'
        elif 'cassi' in msg:
            user = 'Cassi'
        elif 'mari' in msg:
            user = 'Mari'
            
        task_kw = None
        if 'caixa' in msg or 'areia' in msg:
            task_kw = 'caixa de areia'
        elif 'brinquedo' in msg or 'bau' in msg or 'baú' in msg:
            task_kw = 'brinquedos'
        elif 'mochila' in msg:
            task_kw = 'mochila'
        elif 'planta' in msg or 'horta' in msg or 'varanda' in msg:
            task_kw = 'plantas'
        elif 'jantar' in msg or 'cozinhar' in msg:
            task_kw = 'jantar'
        elif 'pia' in msg or 'brilhar' in msg:
            task_kw = 'pia'
        elif 'lixo' in msg or 'recicla' in msg:
            if 'banheiro' in msg:
                task_kw = 'lixo do banheiro'
            else:
                task_kw = 'lixo'
        elif 'aspirar' in msg or 'aspirador' in msg:
            task_kw = 'aspirador'
        elif 'pano' in msg:
            task_kw = 'passar pano'
        elif 'cabelo' in msg:
            task_kw = 'banho e lavar cabelo'
            user = 'Isa'
        elif 'banho' in msg:
            task_kw = 'banho'
            user = 'Isa'
        elif 'roupa' in msg or 'lavar' in msg:
            if 'cama' in msg or 'banho' in msg:
                task_kw = 'lavar roupa'
                user = 'Mari'
            elif 'semana' in msg:
                task_kw = 'lavar roupa'
                user = 'Cassi'
            else:
                task_kw = 'lavar roupa'
        elif 'lençol' in msg or 'toalha' in msg or 'cama' in msg:
            task_kw = 'lençóis'
        elif 'poeira' in msg or 'espanar' in msg or 'espelho' in msg:
            task_kw = 'poeira'
        elif 'agua' in msg or 'água' in msg or 'potinho' in msg:
            task_kw = 'água'
        elif 'ballet' in msg or 'sapatilha' in msg:
            task_kw = 'ballet'
        elif 'alimentador' in msg or 'automatico' in msg or 'ração' in msg or 'racao' in msg:
            task_kw = 'alimentador'
            
        if task_kw or user:
            if not user and task_kw:
                if task_kw in ['caixa de areia', 'plantas', 'jantar', 'lixo', 'aspirador']:
                    user = 'Cassi'
                elif task_kw in ['brinquedos', 'mochila', 'água', 'ballet', 'lixo do banheiro']:
                    user = 'Isa'
                elif task_kw in ['pia', 'alimentador', 'lençóis', 'poeira', 'passar pano']:
                    user = 'Mari'
            return 'completar_tarefa', {'usuario': user, 'tarefa': task_kw or msg}
            
    # 1.5. Listar recompensas resgatadas
    list_redeemed_keywords = ['quais', 'listar', 'ver', 'mostrar', 'histórico', 'historico', 'resgatadas', 'resgatou', 'comprou', 'compradas', 'pendentes', 'recebeu', 'entregues', 'entrega']
    is_list_redeemed = any(kw in msg for kw in ['recompensa', 'resgate', 'loja', 'item', 'itens']) and any(kw in msg for kw in list_redeemed_keywords)
    if not is_list_redeemed:
        is_list_redeemed = any(kw in msg for kw in ['resgatou', 'resgatadas'])
    if is_list_redeemed:
        user = None
        if 'isa' in msg:
            user = 'Isa'
        elif 'cassi' in msg:
            user = 'Cassi'
        elif 'mari' in msg:
            user = 'Mari'
        return 'listar_recompensas_resgatadas', {'usuario': user}

    # 2. Resgatar recompensa
    redeem_keywords = ['resgatar', 'resgate', 'comprar', 'recompensa', 'reivindicar', 'quero resgatar', 'quero comprar']
    is_redeem = any(kw in msg for kw in redeem_keywords)
    if is_redeem:
        user = None
        if 'isa' in msg:
            user = 'Isa'
        elif 'cassi' in msg:
            user = 'Cassi'
        elif 'mari' in msg:
            user = 'Mari'
            
        reward_kw = None
        if 'spa' in msg or 'banho' in msg:
            reward_kw = 'spa'
        elif 'restaurante' in msg or 'pizza' in msg or 'jantar' in msg:
            reward_kw = 'restaurante'
        elif 'leitura' in msg or 'livro' in msg:
            reward_kw = 'leitura'
        elif 'cafe' in msg or 'café' in msg:
            reward_kw = 'café'
        elif 'videogame' in msg or 'jogo' in msg:
            reward_kw = 'videogame'
        elif 'filme' in msg or 'cinema' in msg:
            reward_kw = 'filme'
        elif 'dormir' in msg or 'tarde' in msg:
            reward_kw = 'dormir'
        elif 'cerveja' in msg or 'artesanal' in msg:
            reward_kw = 'cerveja'
        elif 'tela' in msg or 'desenho' in msg or 'tablet' in msg or 'youtube' in msg:
            reward_kw = 'tela'
        elif 'historinha' in msg or 'dormir' in msg:
            reward_kw = 'historinha'
        elif 'massinha' in msg or 'brincar' in msg:
            reward_kw = 'massinha'
        elif 'parque' in msg or 'passeio' in msg:
            reward_kw = 'parque'
            
        if reward_kw or user:
            return 'resgatar_recompensa', {'usuario': user, 'recompensa': reward_kw or msg}
            
    # 3. Listar tarefas
    list_keywords = ['tarefa', 'tarefas', 'missao', 'missões', 'fazer hoje', 'oq fazer', 'lista de tarefas', 'quadro de mis']
    is_list = any(kw in msg for kw in list_keywords)
    if is_list:
        user = None
        if 'isa' in msg:
            user = 'Isa'
        elif 'cassi' in msg:
            user = 'Cassi'
        elif 'mari' in msg:
            user = 'Mari'
        return 'listar_tarefas', {'usuario': user}

    # 4. Adicionar transação
    transaction_keywords = ['despesa', 'receita', 'ganho', 'gasto', 'gastei', 'recebi', 'paguei', 'lançar transação', 'lançar despesa', 'lançar receita', 'adicionar transação', 'salário', 'salario', 'bônus', 'bonus']
    is_transaction = any(kw in msg for kw in transaction_keywords)
    if is_transaction:
        import re
        numbers = re.findall(r'\b\d+(?:[\.,]\d+)?\b', msg)
        if numbers:
            val = float(numbers[0].replace(',', '.'))
            is_expense = any(kw in msg for kw in ['despesa', 'gasto', 'gastei', 'paguei', 'compra', 'carrefour', 'netflix', 'enel', 'faculdade', 'gasolina', 'padaria', 'farmacia', 'farmácia', 'uber', 'petshop'])
            valor_final = -val if is_expense else val
            
            desc = "Receita"
            if is_expense:
                m_desc = re.search(r'\b(?:no|na|em|de|do|da|para|com)\s+([a-zA-Z0-9\s]+)', msg)
                if m_desc:
                    desc = m_desc.group(1).strip().capitalize()
                else:
                    for known_desc in ['carrefour', 'netflix', 'enel', 'faculdade', 'gasolina', 'padaria', 'farmacia', 'farmácia', 'uber', 'petshop']:
                        if known_desc in msg:
                            desc = known_desc.capitalize()
                            break
                    if desc == "Receita":
                        desc = "Despesa"
            else:
                m_desc = re.search(r'\b(?:de|do|da|com|proveniente\s+de)\s+([a-zA-Z0-9\s]+)', msg)
                if m_desc:
                    desc = m_desc.group(1).strip().capitalize()
                else:
                    for known_desc in ['salário', 'salario', 'bônus', 'bonus']:
                        if known_desc in msg:
                            desc = "Salário" if "sal" in known_desc else "Bônus"
                            break
            
            desc = re.sub(r'\b\d+.*$', '', desc).strip()
            desc = re.sub(r'\b(?:reais|real)\b', '', desc, flags=re.IGNORECASE).strip()
            if not desc:
                desc = "Despesa" if is_expense else "Receita"
                
            return 'adicionar_transacao', {'descricao': desc, 'valor': valor_final}
        
    return None, None

@ia_memoria_bp.route('/api/ia-memoria/chat', methods=['POST'])
def ia_chat():
    data = request.json or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"reply": "Por favor, digite uma pergunta válida!"})
        
    from .orchestrator import Orchestrator
    orchestrator = Orchestrator()
    reply_text, is_ollama = orchestrator.route(message)
    
    if reply_text is None:
        # Default search path
        from .nlp_engine import search_best_memory
        memories = get_all_memories()
        best_match, score = search_best_memory(message, memories)
        
        if best_match and score >= 0.18:
            formatted_content = format_list_to_bullets(best_match['conteudo'])
            reply_text = f"🤖 Encontrei esta informação nas minhas memórias de **{best_match['categoria']}**:<br><br>{formatted_content}"
        else:
            reply_text = (
                f"Desculpe, não encontrei nenhuma informação parecida registrada nas minhas memórias sobre seu pedido.<br><br>"
                f"💡 **Quer que eu lembre disso?** Digite algo como:<br>"
                f"*\"salve que o Wi-Fi de visitas é FamiliaFeliz2026!\"* ou *\"anote que a chave reserva fica no aparador\"*."
            )
            
    # Append engine indicator badge
    if reply_text:
        if is_ollama and "O Ollama está offline" not in reply_text and "Ocorreu um erro de conexão" not in reply_text:
            badge = (
                '<div style="margin-top: 10px; font-size: 0.72rem; color: rgba(255,255,255,0.4); '
                'display: inline-flex; align-items: center; gap: 4px; border-top: 1px solid rgba(255,255,255,0.08); '
                'padding-top: 4px; width: 100%;">'
                '<span style="color: #818cf8; font-size: 0.85rem;">🧠</span> Processado via <b>Ollama (Local)</b>'
                '</div>'
            )
            reply_text += badge

    return jsonify({"reply": reply_text})

@ia_memoria_bp.route('/api/ia-memoria/contatos', methods=['GET'])
def get_contacts():
    memories = get_all_memories()
    # Filter only entries in the 'Contatos' category
    contacts = [m for m in memories if m['categoria'] == 'Contatos']
    return jsonify(contacts)

@ia_memoria_bp.route('/api/ia-memoria/memorias', methods=['GET'])
def get_memories_route():
    memories = get_all_memories()
    return jsonify(memories)

@ia_memoria_bp.route('/api/ia-memoria/memorias/salvar', methods=['POST'])
def save_or_update_memory_route():
    data = request.json or {}
    mem_id = data.get("id")
    category = data.get("categoria", "Geral").strip()
    key = data.get("chave", "").strip()
    content = data.get("conteudo", "").strip()
    
    if not key or not content:
        return jsonify({"success": False, "error": "Assunto e Conteúdo são obrigatórios."}), 400
        
    if mem_id:
        update_memory(mem_id, category, key, content)
        return jsonify({"success": True, "message": "Memória atualizada com sucesso!"})
    else:
        save_memory(category, key, content)
        return jsonify({"success": True, "message": "Memória cadastrada com sucesso!"})

@ia_memoria_bp.route('/api/ia-memoria/memorias/excluir', methods=['POST'])
def delete_memory_route():
    data = request.json or {}
    mem_id = data.get("id")
    if not mem_id:
        return jsonify({"success": False, "error": "ID da memória é obrigatório."}), 400
        
    delete_memory(mem_id)
    return jsonify({"success": True, "message": "Memória excluída com sucesso!"})


@ia_memoria_bp.route('/api/ia-memoria/feedback', methods=['POST'])
def feedback_retrain():
    data = request.json or {}
    message = data.get("message", "").strip()
    correct_intent = data.get("correct_intent", "").strip()
    details = data.get("details", "").strip()
    
    if not message or not correct_intent:
        return jsonify({"success": False, "error": "Mensagem e intenção correta são obrigatórias."}), 400
        
    # 1. Parse 'details' string into structured NLU details dictionary format
    assistant_payload = {"intencao": correct_intent}
    
    if correct_intent == "salvar":
        assistant_payload["detalhes"] = {"salvar_conteudo": details}
    elif correct_intent == "buscar":
        search_query = details if details else message
        assistant_payload["detalhes"] = {"buscar_query": search_query}
    elif correct_intent == "adicionar_lista":
        items = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
        assistant_payload["detalhes"] = {"adicionar_itens": items}
    elif correct_intent == "remover_lista":
        items = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
        assistant_payload["detalhes"] = {"remover_itens": items}
    elif correct_intent == "limpar_lista":
        items = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
        assistant_payload["detalhes"] = {"manter_itens": items}
    elif correct_intent == "conversa":
        assistant_payload["detalhes"] = {}
    elif correct_intent == "remover_calendario":
        import re
        event_title = None
        event_date = None
        
        m_iso = re.search(r'\b(\d{4})-(\d{2})-(\d{2})\b', details)
        m_br = re.search(r'\b(\d{2})/(\d{2})(?:/(\d{4}))?\b', details)
        
        if m_iso:
            event_date = m_iso.group(0)
            remaining = details.replace(event_date, "").strip(", ").strip()
            if remaining:
                event_title = remaining
        elif m_br:
            day = m_br.group(1)
            month = m_br.group(2)
            year = m_br.group(3) if m_br.group(3) else "2026"
            event_date = f"{year}-{month}-{day}"
            remaining = details.replace(m_br.group(0), "").strip(", ").strip()
            if remaining:
                event_title = remaining
        else:
            event_title = details
            
        detalhes_payload = {}
        if event_title:
            detalhes_payload["titulo"] = event_title
        if event_date:
            detalhes_payload["data"] = event_date
        assistant_payload["detalhes"] = detalhes_payload

    elif correct_intent == "composto_lista":
        import re
        raw_add = []
        raw_remove = []
        details_lower = details.lower()
        if "adicionar" in details_lower or "remover" in details_lower:
            parts = re.split(r'\b(adicionar|remover)\b', details, flags=re.IGNORECASE)
            current_action = None
            for part in parts:
                part_strip = part.strip().strip(':').strip()
                if part_strip.lower() == 'adicionar':
                    current_action = 'add'
                elif part_strip.lower() == 'remover':
                    current_action = 'remove'
                elif part_strip:
                    sub_items = [clean_item_name(i) for i in re.split(r',|;| e ', part_strip) if clean_item_name(i)]
                    if current_action == 'add':
                        raw_add.extend(sub_items)
                    elif current_action == 'remove':
                        raw_remove.extend(sub_items)
        else:
            raw_add = [clean_item_name(i) for i in re.split(r',|;| e ', details) if clean_item_name(i)]
        assistant_payload["detalhes"] = {
            "adicionar_itens": raw_add,
            "remover_itens": raw_remove
        }

    elif correct_intent == "agendar_calendario":
        import re
        import datetime
        event_date = None
        data_fim = None
        event_time = "00:00"
        event_title = details
        
        m_iso_list = re.findall(r'\b(\d{4})-(\d{2})-(\d{2})\b', details)
        m_br_list = re.findall(r'\b(\d{2})/(\d{2})(?:/(\d{4}))?\b', details)
        
        all_dates_in_details = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{2}/\d{2}(?:/\d{4})?\b', details)
        for d_str in all_dates_in_details:
            event_title = event_title.replace(d_str, "")
            
        if m_iso_list:
            if len(m_iso_list) >= 2:
                event_date = m_iso_list[0]
                data_fim = m_iso_list[1]
            else:
                event_date = m_iso_list[0]
        elif m_br_list:
            dates_parsed = []
            for m in m_br_list:
                day = m[0]
                month = m[1]
                year = m[2] if m[2] else str(datetime.date.today().year)
                dates_parsed.append(f"{year}-{month}-{day}")
            if len(dates_parsed) >= 2:
                event_date = dates_parsed[0]
                data_fim = dates_parsed[1]
            else:
                event_date = dates_parsed[0]
        else:
            event_date = datetime.date.today().strftime("%Y-%m-%d")
            
        if not data_fim:
            data_fim = event_date
            
        m_time = re.search(r'\b(\d{2}):(\d{2})\b', details)
        if m_time:
            event_time = m_time.group(0)
            event_title = event_title.replace(m_time.group(0), "")
            
        event_title = re.sub(r'\b(às|as|em|dia|no|na|de|ate|até|a)\b', '', event_title, flags=re.IGNORECASE)
        event_title = re.sub(r'\s+', ' ', event_title).strip()
        if not event_title:
            event_title = "Compromisso sem título"
        
        assistant_payload["detalhes"] = {
            "compromissos": [{
                "titulo": event_title,
                "data": event_date,
                "data_fim": data_fim,
                "hora": event_time,
                "hora_fim": None,
                "localizacao": None,
                "recorrencia": None
            }]
        }

    elif correct_intent == "completar_tarefa":
        import re
        user_param = None
        task_search = details
        for u in ['Cassi', 'Isa', 'Mari']:
            if re.search(r'\b' + re.escape(u) + r'\b', details, re.IGNORECASE):
                user_param = u
                task_search = re.sub(r'\b(por|de|do|da|para|user|usuario)?\s*' + re.escape(u) + r'\b', '', task_search, flags=re.IGNORECASE)
                break
        task_search = re.sub(r'\s+', ' ', task_search).strip()
        assistant_payload["detalhes"] = {
            "usuario": user_param,
            "tarefa": task_search
        }

    elif correct_intent == "resgatar_recompensa":
        import re
        user_param = None
        reward_search = details
        for u in ['Cassi', 'Isa', 'Mari']:
            if re.search(r'\b' + re.escape(u) + r'\b', details, re.IGNORECASE):
                user_param = u
                reward_search = re.sub(r'\b(por|de|do|da|para|user|usuario)?\s*' + re.escape(u) + r'\b', '', reward_search, flags=re.IGNORECASE)
                break
        reward_search = re.sub(r'\s+', ' ', reward_search).strip()
        assistant_payload["detalhes"] = {
            "usuario": user_param,
            "recompensa": reward_search
        }

    elif correct_intent == "listar_tarefas":
        import re
        user_param = None
        for u in ['Cassi', 'Isa', 'Mari']:
            if re.search(r'\b' + re.escape(u) + r'\b', details, re.IGNORECASE):
                user_param = u
                break
        assistant_payload["detalhes"] = {
            "usuario": user_param
        }

    elif correct_intent == "listar_recompensas_resgatadas":
        import re
        user_param = None
        for u in ['Cassi', 'Isa', 'Mari']:
            if re.search(r'\b' + re.escape(u) + r'\b', details, re.IGNORECASE):
                user_param = u
                break
        assistant_payload["detalhes"] = {
            "usuario": user_param
        }

    elif correct_intent == "salvar_receita":
        lines = [l.strip() for l in details.split('\n') if l.strip()]
        nome = "Receita"
        ingredientes_list = []
        passo_list = []
        if lines:
            nome = lines[0]
            in_passo = False
            for line in lines[1:]:
                if "passo" in line.lower() or "preparo" in line.lower() or "modo" in line.lower():
                    in_passo = True
                    continue
                if in_passo:
                    passo_list.append(line)
                else:
                    ingredientes_list.append(line)
        ingredientes_str = "\n".join(ingredientes_list) if ingredientes_list else "Ingredientes não especificados"
        passo_str = "\n".join(passo_list) if passo_list else "Modo de preparo não especificado"
        assistant_payload["detalhes"] = {
            "nome": nome,
            "ingredientes": ingredientes_str,
            "passo_a_passo": passo_str
        }

    elif correct_intent == "deletar_receita":
        assistant_payload["detalhes"] = {
            "receita": details.strip()
        }

    elif correct_intent == "comprar_receita":
        assistant_payload["detalhes"] = {
            "receita": details.strip()
        }
        
    elif correct_intent == "adicionar_transacao":
        intent_local, details_local = parse_intent_locally(details)
        if intent_local == 'adicionar_transacao':
            desc = details_local.get('descricao', 'Transação')
            val = details_local.get('valor', 0.0)
        else:
            desc = "Transação"
            val = 0.0
        assistant_payload["detalhes"] = {
            "descricao": desc,
            "valor": val
        }
    else:
        assistant_payload["detalhes"] = {}

    # 2. Execute database correction logic immediately using Agent Architecture
    try:
        from .orchestrator import Orchestrator
        orchestrator = Orchestrator()
        if correct_intent in orchestrator.agents:
            agent = orchestrator.agents[correct_intent]
            agent.handle(correct_intent, assistant_payload.get("detalhes", {}), message)
    except Exception as e:
        print(f"Error updating database during feedback execution: {e}")
        return jsonify({"success": False, "error": f"Erro ao atualizar banco de dados: {str(e)}"}), 500

    # 3. Save the feedback to json and rebuild Modelfile
    try:
        feedback_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'training')
        os.makedirs(feedback_dir, exist_ok=True)
        feedback_file = os.path.join(feedback_dir, 'feedback.json')
        
        feedbacks = []
        if os.path.exists(feedback_file):
            try:
                with open(feedback_file, 'r', encoding='utf-8') as f:
                    feedbacks = json.load(f)
            except Exception as e:
                print(f"Error reading feedback.json: {e}")
                feedbacks = []
                
        assistant_str = json.dumps(assistant_payload)
        
        # Remove duplicate message entries if any
        feedbacks = [fb for fb in feedbacks if fb.get("user") != message]
        
        # Append the new one
        feedbacks.append({
            "user": message,
            "assistant": assistant_str
        })
        
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedbacks, f, indent=2, ensure_ascii=False)
            
        # Rebuild Modelfile
        template_file = os.path.join(feedback_dir, 'Modelfile.template')
        modelfile_path = os.path.join(feedback_dir, 'Modelfile')
        
        if os.path.exists(template_file):
            with open(template_file, 'r', encoding='utf-8') as f:
                modelfile_content = f.read()
        else:
            modelfile_content = "FROM qwen2:1.5b\nPARAMETER temperature 0.0\n"
            
        modelfile_content += "\n# --- Dynamic active learning feedback items ---\n"
        for fb in feedbacks:
            user_msg = fb["user"]
            assistant_msg = fb["assistant"]
            
            # Escape backslashes and double quotes for Modelfile syntax
            escaped_user = user_msg.replace('\\', '\\\\').replace('"', '\\"')
            escaped_assistant = assistant_msg.replace('\\', '\\\\').replace('"', '\\"')
            
            modelfile_content += f'MESSAGE user "{escaped_user}"\n'
            modelfile_content += f'MESSAGE assistant "{escaped_assistant}"\n\n'
            
        with open(modelfile_path, 'w', encoding='utf-8') as f:
            f.write(modelfile_content)
            
        # Trigger background retraining
        def retrain_model():
            global is_retraining_model
            is_retraining_model = True
            try:
                print("Starting background Ollama model creation...")
                res = subprocess.run(
                    ["ollama", "create", "dashfamilia-ia", "-f", modelfile_path],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"Background Ollama model creation succeeded. stdout: {res.stdout}")
            except Exception as e:
                print(f"Error in background Ollama model creation: {e}")
            finally:
                is_retraining_model = False
                
        t = threading.Thread(target=retrain_model)
        t.daemon = True
        t.start()
        
    except Exception as e:
        print(f"Error during feedback processing: {e}")
        return jsonify({"success": False, "error": f"Erro ao processar feedback: {str(e)}"}), 500
        
    return jsonify({"success": True})


@ia_memoria_bp.route('/api/ia-memoria/status', methods=['GET'])
def get_ollama_status():
    from .nlp_engine import check_ollama_status, get_available_ollama_model
    is_online = check_ollama_status()
    model = get_available_ollama_model()
    
    status = "offline"
    if is_online:
        status = "training" if is_retraining_model else "online"
        
    return jsonify({
        "status": status,
        "model": model
    })



