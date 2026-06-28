import os
import json
import datetime
import re
from .database import (
    get_all_memories, save_memory, delete_memory, update_memory,
    get_all_events, save_event, delete_event, update_event_google_id,
    get_all_users, get_user_by_name, get_all_tasks, get_tasks_for_user,
    complete_task_in_db, get_all_rewards, get_rewards_for_user,
    redeem_reward_in_db, reset_tasks_db, save_transaction_to_db
)
from .nlp_engine import (
    search_best_memory, classify_category, tokenize, 
    format_list_to_bullets, clean_item_name
)

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
    msg_lower = message.lower()
    prefixes = ["salvar receita de ", "registrar receita de ", "cadastrar receita de ", "adicionar receita de ",
                "salvar receita ", "registrar receita ", "cadastrar receita ", "adicionar receita "]
    prefix_found = None
    for p in prefixes:
        if msg_lower.startswith(p):
            prefix_found = p
            break
            
    if not prefix_found:
        has_inst = any(kw in msg_lower for kw in ['passo a passo', 'modo de preparo', 'preparo', 'instrucoes', 'instruções', 'modo de fazer'])
        has_ing = any(kw in msg_lower for kw in ['ingredientes', 'farinha', 'açúcar', 'acucar', 'leite', 'ovo', 'ovos', 'colher', 'chá', 'cha', 'g de', 'ml de', 'gramas', 'fermento'])
        if has_inst and has_ing:
            lines = [line.strip() for line in message.split('\n') if line.strip()]
            recipe_name = "Receita"
            if lines:
                first_line = lines[0]
                first_line_clean = first_line.strip('🥣:-*• \t')
                if len(first_line_clean) < 60 and not any(k in first_line_clean.lower() for k in ['ingredientes', 'passo a passo', 'modo de preparo']):
                    recipe_name = first_line_clean
            content_part = message.strip()
        else:
            return None
    else:
        content_part = message[len(prefix_found):].strip()
        
    if prefix_found:
        after_prefix = message[len(prefix_found):].strip()
        after_prefix_lower = after_prefix.lower()
        end_idx = len(after_prefix)
        for sep in [':', '\n', 'ingredientes', 'passo a passo', 'modo de preparo', 'preparo']:
            idx = after_prefix_lower.find(sep)
            if idx != -1 and idx < end_idx:
                end_idx = idx
        recipe_name = after_prefix[:end_idx].strip()
        recipe_name = recipe_name.strip(',. ')
        content_part = after_prefix[end_idx:].strip()
    else:
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
        ing_part_lower = ingredients_part.lower()
        ing_header_idx = ing_part_lower.find('ingredientes')
        if ing_header_idx != -1:
            ingredients_text = ingredients_part[ing_header_idx + len('ingredientes'):].strip()
        else:
            ingredients_text = ingredients_part
        while ingredients_text and ingredients_text[0] in [':', ',', '.', ' ', '-', '\n']:
            ingredients_text = ingredients_text[1:].strip()
            
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


class BaseAgent:
    def __init__(self, name, recommended_model):
        self.name = name
        self.recommended_model = recommended_model

    def handle(self, intent, detalhes, message):
        raise NotImplementedError("Subclasses must implement handle method")


class ListAgent(BaseAgent):
    def __init__(self):
        super().__init__("ListAgent", "qwen2.5:3b")

    def handle(self, intent, detalhes, message):
        msg_lower = message.lower()
        if any(word in msg_lower for word in ['farmacia', 'farmácia', 'remedio', 'remédio', 'remedios', 'remédios', 'medicamento', 'drogaria']):
            target_category = 'Farmácia'
            list_name = 'farmácia'
            list_title = 'de farmácia'
            list_name_gendered = 'de farmácia'
            default_key = 'lista compras farmacia'
            updated_text = "atualizada"
        else:
            target_category = 'Mercado'
            list_name = 'compras'
            list_title = 'do mercado'
            list_name_gendered = 'de compras'
            default_key = 'lista compras mercado'
            updated_text = "updated"

        memories = get_all_memories()
        market_lists = [m for m in memories if m['categoria'] == target_category]

        # Get target items list based on existing list
        old_items = []
        target_list = None
        if market_lists:
            target_list = market_lists[0]
            old_content = target_list['conteudo']
            if ':' in old_content:
                list_part = old_content.split(':', 1)[1].strip()
            else:
                list_part = old_content
            list_part_clean = list_part.replace(' e ', ', ')
            if list_part_clean.endswith('.'):
                list_part_clean = list_part_clean[:-1]
            list_part_clean = list_part_clean.strip()
            old_items = [item.strip() for item in list_part_clean.split(',')]
            old_items = [item for item in old_items if item]

        # 1. compound list (adicionar_itens and remover_itens)
        if intent == "composto_lista":
            raw_add = detalhes.get("adicionar_itens") or []
            raw_remove = detalhes.get("remover_itens") or []
            items_to_add = [clean_item_name(i) for i in raw_add if clean_item_name(i)]
            items_to_remove = [clean_item_name(i) for i in raw_remove if clean_item_name(i)]
            
            remaining_items = old_items
            if items_to_remove:
                remove_set_lower = {item.lower().strip() for item in items_to_remove}
                remaining_items = [item for item in old_items if item.lower().strip() not in remove_set_lower]
                
            merged_items = []
            seen_lower = set()
            for item in remaining_items + items_to_add:
                item_lower = item.lower().strip()
                if item_lower not in seen_lower and item_lower != "":
                    seen_lower.add(item_lower)
                    merged_items.append(item.strip().capitalize())
            
            if merged_items:
                if len(merged_items) > 1:
                    formatted_keep = ", ".join(merged_items[:-1]) + " e " + merged_items[-1]
                else:
                    formatted_keep = merged_items[0]
                new_content = f"A lista {list_title} é: {formatted_keep}."
                if market_lists:
                    save_memory(target_category, market_lists[0]['chave'], new_content)
                else:
                    save_memory(target_category, default_key, new_content)
                formatted_bullets = format_list_to_bullets(new_content)
                removed_str = ", ".join(items_to_remove) if items_to_remove else "nenhum"
                added_str = ", ".join(items_to_add) if items_to_add else "nenhum"
                return (
                    f"🛒 **Lista de {list_name} {updated_text} com sucesso!**<br><br>"
                    f"➖ **Removido(s):** {removed_str}<br>"
                    f"➕ **Adicionado(s):** {added_str}<br><br>"
                    f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                )
            else:
                if market_lists:
                    delete_memory(market_lists[0]['id'])
                return f"🎉 **Lista de {list_name} limpa!** Removi todos os itens solicitados e a lista de {list_name} ficou vazia."

        # 2. clear list (manter_itens)
        elif intent == "limpar_lista":
            raw_keep = detalhes.get("manter_itens") or []
            keep_items = [clean_item_name(i) for i in raw_keep if clean_item_name(i)]
            if not target_list:
                return f"🤖 Não encontrei nenhuma lista {list_title} ativa nas minhas memórias para atualizar!"
            
            if keep_items:
                if len(keep_items) > 1:
                    formatted_keep = ", ".join(keep_items[:-1]) + " e " + keep_items[-1]
                else:
                    formatted_keep = keep_items[0]
                new_content = f"A lista {list_title} é: {formatted_keep}."
                save_memory(target_category, target_list['chave'], new_content)
                formatted_bullets = format_list_to_bullets(new_content)
                return (
                    f"🛒 **Entendido!** Atualizei a lista nas minhas memórias e marquei os outros itens como comprados.<br><br>"
                    f"📝 **Itens mantidos para a próxima compra:**<br>{formatted_bullets}"
                )
            else:
                delete_memory(target_list['id'])
                return f"🎉 **Parabéns!** Todos os itens foram marcados como comprados e a lista {list_name_gendered} foi limpa das minhas memórias! 🛒"

        # 3. add items (adicionar_itens)
        elif intent == "adicionar_lista":
            raw_add = detalhes.get("adicionar_itens") or []
            items_to_add = [clean_item_name(i) for i in raw_add if clean_item_name(i)]
            if not items_to_add:
                return "🤖 Não entendi quais itens você deseja adicionar. Tente algo como 'adicionar pão e leite'."

            merged_items = []
            seen_lower = set()
            for item in old_items + items_to_add:
                item_lower = item.lower().strip()
                if item_lower not in seen_lower and item_lower != "":
                    seen_lower.add(item_lower)
                    merged_items.append(item.strip().capitalize())

            if merged_items:
                if len(merged_items) > 1:
                    formatted_keep = ", ".join(merged_items[:-1]) + " e " + merged_items[-1]
                else:
                    formatted_keep = merged_items[0]
                new_content = f"A lista {list_title} é: {formatted_keep}."
                if target_list:
                    save_memory(target_category, target_list['chave'], new_content)
                else:
                    save_memory(target_category, default_key, new_content)
                formatted_bullets = format_list_to_bullets(new_content)
                if not target_list:
                    list_title_msg = " de farmácia" if target_category == 'Farmácia' else ""
                    return (
                        f"🛒 **Nova lista{list_title_msg} criada!** Como não encontrei nenhuma lista ativa, criei uma nova com esses itens:<br><br>"
                        f"{formatted_bullets}"
                    )
                else:
                    return (
                        f"🛒 **Item adicionado à lista!** Atualizei sua lista {list_title}.<br><br>"
                        f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                    )
            else:
                if target_list:
                    delete_memory(target_list['id'])
                return f"🎉 A lista {list_name_gendered} foi limpa das minhas memórias!"

        # 4. remove items (remover_itens)
        elif intent == "remover_lista":
            raw_remove = detalhes.get("remover_itens") or []
            items_to_remove = [clean_item_name(i) for i in raw_remove if clean_item_name(i)]
            if not target_list:
                return f"🤖 Não encontrei nenhuma lista {list_title} ativa nas minhas memórias para remover itens!"
            if not items_to_remove:
                return "🤖 Não entendi quais itens você deseja remover. Tente algo como 'remover leite'."

            remove_set_lower = {item.lower().strip() for item in items_to_remove}
            remaining_items = [item for item in old_items if item.lower().strip() not in remove_set_lower]

            if remaining_items:
                if len(remaining_items) > 1:
                    formatted_keep = ", ".join(remaining_items[:-1]) + " e " + remaining_items[-1]
                else:
                    formatted_keep = remaining_items[0]
                new_content = f"A lista {list_title} é: {formatted_keep}."
                save_memory(target_category, target_list['chave'], new_content)
                formatted_bullets = format_list_to_bullets(new_content)
                return (
                    f"🛒 **Itens removidos da lista!** Atualizei sua lista {list_title}.<br><br>"
                    f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                )
            else:
                delete_memory(target_list['id'])
                return f"🎉 **Lista limpa!** Removi todos os itens e limpei a lista {list_title} das minhas memórias."


        return None


class CalendarAgent(BaseAgent):
    def __init__(self):
        super().__init__("CalendarAgent", "qwen2.5:3b")

    def handle(self, intent, detalhes, message):
        # 1. agendar_calendario
        if intent == "agendar_calendario":
            compromissos = detalhes.get("compromissos")
            if not compromissos:
                compromissos = [detalhes]

            reply_events = []
            for comp in compromissos:
                event_title = comp.get("titulo") or "Compromisso sem título"
                event_date = comp.get("data")
                event_time = comp.get("hora") or "00:00"
                localizacao = comp.get("localizacao")
                recorrencia = comp.get("recorrencia")
                data_fim = comp.get("data_fim")
                hora_fim = comp.get("hora_fim")

                if not event_date:
                    event_date = datetime.date.today().strftime("%Y-%m-%d")
                if not data_fim:
                    data_fim = event_date

                event_id = save_event(
                    titulo=event_title,
                    data=event_date,
                    hora=event_time,
                    responsavel='Família',
                    cor='#5f27cd',
                    categoria='Familiar',
                    localizacao=localizacao,
                    recorrencia=recorrencia,
                    data_fim=data_fim,
                    hora_fim=hora_fim
                )

                try:
                    from .google_calendar import push_event_to_google_background
                    push_event_to_google_background(event_id, event_title, event_date, event_time, localizacao, recorrencia, data_fim, hora_fim)
                except Exception as ex:
                    print(f"Google Calendar background sync trigger failed: {ex}")

                try:
                    parts = event_date.split("-")
                    formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                except Exception:
                    formatted_date = event_date

                try:
                    parts_fim = data_fim.split("-")
                    formatted_date_fim = f"{parts_fim[2]}/{parts_fim[1]}/{parts_fim[0]}"
                except Exception:
                    formatted_date_fim = data_fim

                recurrence_desc = None
                if recorrencia:
                    if "FREQ=WEEKLY" in recorrencia:
                        day_map = {"MO": "segunda-feira", "TU": "terça-feira", "WE": "quarta-feira",
                                   "TH": "quinta-feira", "FR": "sexta-feira", "SA": "sábado", "SU": "domingo"}
                        day_found = None
                        for code, pt in day_map.items():
                            if f"BYDAY={code}" in recorrencia:
                                day_found = pt
                                break
                        if day_found:
                            recurrence_desc = f"Toda {day_found}" if "feira" in day_found else f"Todo {day_found}"
                        else:
                            recurrence_desc = "Semanal"
                    else:
                        recurrence_desc = recorrencia

                reply_events.append({
                    "titulo": event_title,
                    "data": formatted_date,
                    "data_fim": formatted_date_fim,
                    "hora": event_time,
                    "hora_fim": hora_fim,
                    "localizacao": localizacao,
                    "recurrence_desc": recurrence_desc
                })

            if len(reply_events) == 1:
                evt = reply_events[0]
                formatted_range = evt["data"]
                if evt["data_fim"] and evt["data_fim"] != evt["data"]:
                    formatted_range += f" até {evt['data_fim']}"
                reply = (
                    f"📅 **Compromisso agendado com sucesso!**<br><br>"
                    f"📌 **Evento:** {evt['titulo']}<br>"
                    f"📅 **Data:** {formatted_range}<br>"
                    f"🕒 **Hora:** {evt['hora']}<br>"
                )
                if evt['localizacao']:
                    reply += f"📍 **Local:** {evt['localizacao']}<br>"
                if evt['recurrence_desc']:
                    reply += f"🔁 **Repetição:** {evt['recurrence_desc']}<br>"
                reply += f"<br>💡 *Sincronizando com o Google Calendar em background...*"
                return reply
            else:
                reply = f"📅 **{len(reply_events)} compromissos agendados com sucesso!**<br><br>"
                for idx, evt in enumerate(reply_events):
                    formatted_range = evt["data"]
                    if evt["data_fim"] and evt["data_fim"] != evt["data"]:
                        formatted_range += f" até {evt['data_fim']}"
                    reply += f"**{idx+1}. {evt['titulo']}**<br>"
                    reply += f"📅 Data: {formatted_range}<br>"
                    reply += f"🕒 Hora: {evt['hora']}<br>"
                    if evt['localizacao']:
                        reply += f"📍 Local: {evt['localizacao']}<br>"
                    if evt['recurrence_desc']:
                        reply += f"🔁 Repetição: {evt['recurrence_desc']}<br>"
                    reply += "<br>"
                reply += f"💡 *Sincronizando com o Google Calendar em background...*"
                return reply

        # 2. remover_calendario
        elif intent == "remover_calendario":
            event_title = detalhes.get("titulo")
            event_date = detalhes.get("data")

            if not event_title and not event_date:
                return "🤖 Para remover um compromisso, por favor informe o título ou a data dele!"

            events = get_all_events()
            matched_events = []
            for e in events:
                title_match = False
                date_match = False
                if event_title and event_title.lower().strip() in e['titulo'].lower().strip():
                    title_match = True
                if event_date and e['data'] == event_date:
                    date_match = True
                if event_title and event_date:
                    if title_match and date_match:
                        matched_events.append(e)
                elif event_title:
                    if title_match:
                        matched_events.append(e)
                elif event_date:
                    if date_match:
                        matched_events.append(e)

            if not matched_events:
                query_desc = f"'{event_title}'" if event_title else ""
                if event_date:
                    try:
                        parts = event_date.split("-")
                        formatted_qdate = f"{parts[2]}/{parts[1]}/{parts[0]}"
                    except Exception:
                        formatted_qdate = event_date
                    query_desc += f" no dia {formatted_qdate}" if query_desc else f"no dia {formatted_qdate}"
                return f"🤖 Não encontrei nenhum compromisso sobre {query_desc} no calendário."
            else:
                deleted_names = []
                for me in matched_events:
                    delete_event(me['id'])
                    deleted_names.append(f"\"{me['titulo']}\"")
                    g_id = me.get('google_event_id')
                    if g_id:
                        try:
                            from .google_calendar import delete_event_from_google_background
                            delete_event_from_google_background(g_id)
                        except Exception as ex:
                            print(f"Google Calendar background delete trigger failed: {ex}")
                deleted_str = ", ".join(deleted_names)
                return (
                    f"📅 **Compromisso(s) desmarcado(s) com sucesso!**<br><br>"
                    f"🗑️ **Removido(s):** {deleted_str}<br><br>"
                    f"💡 *Sincronizando exclusão com o Google Calendar em background...*"
                )

        return None


class TaskAgent(BaseAgent):
    def __init__(self):
        super().__init__("TaskAgent", "gemma2:2b")

    def handle(self, intent, detalhes, message):
        from .database import consolidate_tasks_db
        consolidate_tasks_db()
        # 1. completar_tarefa
        if intent == "completar_tarefa":
            user_param = detalhes.get("usuario")
            task_search = detalhes.get("tarefa") or ""

            all_tasks = get_all_tasks()
            active_tasks = [t for t in all_tasks if not t['completed']]
            if user_param:
                active_tasks = [t for t in active_tasks if t['usuario_nome'].lower() == user_param.lower()]

            matched_task = None
            if task_search:
                search_term = task_search.lower().strip()
                if user_param and user_param.lower() == 'isa' and search_term == 'banho':
                    for t in active_tasks:
                        if t['titulo'].lower().strip() in ['banho e lavar cabelo', 'banho e lavar o cabelo']:
                            matched_task = t
                            break
                if not matched_task:
                    for t in active_tasks:
                        if search_term in t['titulo'].lower():
                            matched_task = t
                            break
                if not matched_task:
                    search_tokens = set(search_term.split())
                    best_overlap = 0
                    for t in active_tasks:
                        title_tokens = set(t['titulo'].lower().split())
                        overlap = len(search_tokens & title_tokens)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            matched_task = t

            if matched_task:
                success, user_profile, leveled_up = complete_task_in_db(matched_task['id'])
                if success:
                    reply = (
                        f"⚔️ **Missão Concluída!**<br><br>"
                        f"👤 **Membro:** {matched_task['usuario_nome']}<br>"
                        f"📜 **Tarefa:** {matched_task['titulo']}<br>"
                        f"🔵 **XP ganho:** +{matched_task['reward_xp']}<br>"
                        f"🪙 **Ouro ganho:** +{matched_task['reward_gold']}<br><br>"
                        f"🎉 *Seu progresso foi atualizado no painel e o checkmark (✅) foi adicionado ao calendário!*"
                    )
                    if leveled_up:
                        reply += (
                            f"<br><br>✨ **LEVEL UP!** 🎉<br>"
                            f"🌟 **{user_profile['nome']}** subiu para o **Nível {user_profile['nivel']}**! 🚀"
                        )
                    return reply
                else:
                    return f"🤖 A tarefa '{matched_task['titulo']}' já foi concluída anteriormente!"
            else:
                user_str = f" para {user_param}" if user_param else ""
                return (
                    f"🤖 Não encontrei nenhuma tarefa pendente relacionada a '{task_search}'{user_str}.<br><br>"
                    f"💡 Verifique as missões ativas na aba **To-Do List Gamer**!"
                )

        # 2. listar_tarefas
        elif intent == "listar_tarefas":
            user_param = detalhes.get("usuario")
            all_tasks = get_all_tasks()
            pending_tasks = [t for t in all_tasks if not t['completed']]
            if user_param:
                pending_tasks = [t for t in pending_tasks if t['usuario_nome'].lower() == user_param.lower()]

            if not pending_tasks:
                return "🎉 **Todas as tarefas estão em dia!** Não há missões pendentes no momento."
            else:
                pending_tasks.sort(key=lambda x: x['data'])
                unique_pending = []
                seen_pending = set()
                for t in pending_tasks:
                    key = (t['usuario_nome'].lower(), t['titulo'].lower())
                    if key not in seen_pending:
                        seen_pending.add(key)
                        unique_pending.append(t)

                has_isa_hair_wash = any(
                    t['usuario_nome'].lower() == 'isa' and t['titulo'].lower().strip() in ['banho e lavar cabelo', 'banho e lavar o cabelo']
                    for t in unique_pending
                )
                if has_isa_hair_wash:
                    unique_pending = [
                        t for t in unique_pending
                        if not (t['usuario_nome'].lower() == 'isa' and t['titulo'].lower().strip() == 'banho')
                    ]

                user_desc = f" de {user_param}" if user_param else ""
                reply = f"📜 **Quadro de Missões Pendentes{user_desc}:**<br><br>"
                for t in unique_pending:
                    reply += f"• **{t['usuario_nome']}**: {t['titulo']} ({t['hora']}) - *🔵 {t['reward_xp']} XP | 🪙 {t['reward_gold']} Gold*<br>"
                return reply

        # 3. resgatar_recompensa
        elif intent == "resgatar_recompensa":
            user_param = detalhes.get("usuario")
            reward_search = detalhes.get("recompensa") or ""

            all_rewards = get_all_rewards()
            active_rewards = [r for r in all_rewards if not r['resgatado']]
            if user_param:
                active_rewards = [r for r in active_rewards if r['usuario_nome'].lower() == user_param.lower()]

            matched_reward = None
            if reward_search:
                search_term = reward_search.lower()
                for r in active_rewards:
                    if search_term in r['titulo'].lower():
                        matched_reward = r
                        break
                if not matched_reward:
                    search_tokens = set(search_term.split())
                    best_overlap = 0
                    for r in active_rewards:
                        title_tokens = set(r['titulo'].lower().split())
                        overlap = len(search_tokens & title_tokens)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            matched_reward = r

            if matched_reward:
                success, msg_redeem, user_profile = redeem_reward_in_db(matched_reward['id'])
                if success:
                    return (
                        f"🛒 **Recompensa Resgatada com Sucesso!**<br><br>"
                        f"👤 **Quem resgatou:** {matched_reward['usuario_nome']}<br>"
                        f"🎁 **Recompensa:** {matched_reward['icone']} {matched_reward['titulo']}<br>"
                        f"🪙 **Custo:** {matched_reward['custo']} Ouro<br>"
                        f"💰 **Saldo Atual:** {user_profile['gold']} Ouro<br><br>"
                        f"🎉 *Divirta-se! O saldo de ouro foi atualizado no painel.*"
                    )
                else:
                    return f"⚠️ **Não foi possível resgatar:** {msg_redeem}"
            else:
                return f"🤖 Não encontrei nenhuma recompensa pendente correspondente a '{reward_search}'. Verifique a Loja de Recompensas!"

        # 4. listar_recompensas_resgatadas
        elif intent == "listar_recompensas_resgatadas":
            user_param = detalhes.get("usuario")
            all_rewards = get_all_rewards()
            redeemed_rewards = [r for r in all_rewards if r['resgatado'] == 1]
            if user_param:
                redeemed_rewards = [r for r in redeemed_rewards if r['usuario_nome'].lower() == user_param.lower()]

            if not redeemed_rewards:
                user_desc = f" para {user_param}" if user_param else ""
                return f"🎁 Não há nenhuma recompensa resgatada pendente de recebimento{user_desc}."
            else:
                user_desc = f" de {user_param}" if user_param else ""
                reply = f"🛒 **Recompensas Resgatadas (Pendentes de Entrega){user_desc}:**<br><br>"
                for r in redeemed_rewards:
                    reply += f"• **{r['usuario_nome']}**: {r['icone']} {r['titulo']} - *Custo: 🪙 {r['custo']} Ouro*<br>"
                return reply

        return None


class FinanceAgent(BaseAgent):
    def __init__(self):
        super().__init__("FinanceAgent", "qwen2.5-coder:1.5b")

    def handle(self, intent, detalhes, message):
        # 1. adicionar_transacao
        if intent == "adicionar_transacao":
            desc = detalhes.get("descricao")
            val = detalhes.get("valor")
            if desc is None or val is None:
                return "🤖 Não entendi a descrição ou o valor da transação. Tente algo como 'gastei 50 no mercado'."

            is_expense = val < 0
            categoria = "Receita"

            CATEGORIES_KEYWORDS = {
                "Habitação (Aluguel/Contas)": ['enel', 'luz', 'água', 'agua', 'aluguel', 'condomínio', 'condominio', 'energia', 'internet', 'fibra', 'gás', 'gas', 'habitação', 'habitacao'],
                "Educação": ['escola', 'faculdade', 'curso', 'livro', 'caderno', 'educação', 'educacao'],
                "Alimentação e Supermercado": ['carrefour', 'mercado', 'supermercado', 'padaria', 'feira', 'comida', 'pão', 'almoço', 'jantar', 'pizza', 'restaurante', 'alimentação', 'alimentacao'],
                "Saúde e Planos": ['farmácia', 'farmacia', 'médico', 'medico', 'dentista', 'consulta', 'remédio', 'remedio', 'plano', 'saúde', 'saude'],
                "Transporte/Combustível": ['gasolina', 'combustível', 'uber', 'estacionamento', 'pedágio', 'ônibus', 'metro', 'transporte'],
                "Lazer e Streaming": ['netflix', 'spotify', 'cinema', 'streaming', 'jogo', 'videogame', 'cerveja', 'churrasco', 'lazer']
            }

            if is_expense:
                categoria = "Outros"
                desc_lower = desc.lower()
                msg_lower = message.lower()
                for cat_name, keywords in CATEGORIES_KEYWORDS.items():
                    if any(re.search(r'\b' + re.escape(kw) + r'\b', desc_lower) or re.search(r'\b' + re.escape(kw) + r'\b', msg_lower) for kw in keywords):
                        categoria = cat_name
                        break

            user = "Família"
            msg_lower = message.lower()
            if 'mari' in msg_lower:
                user = "Mariana"
            elif 'cassi' in msg_lower:
                user = "Cassi"
            elif 'isa' in msg_lower:
                user = "Isa"

            date_str = datetime.date.today().strftime('%d/%m/%Y')
            save_transaction_to_db(desc, val, categoria, date_str, user)

            if val < 0:
                val_formatted = f"- R$ {abs(val):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            else:
                val_formatted = f"R$ {val:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

            return (
                f"💰 **Transação registrada com sucesso!**<br><br>"
                f"📝 **Descrição:** {desc}<br>"
                f"💵 **Valor:** {val_formatted}<br>"
                f"🏷️ **Categoria:** {categoria}<br>"
                f"👤 **Responsável:** {user}<br><br>"
                f"📊 *A aba Controle Financeiro foi atualizada!*"
            )

        return None


class MemoryAgent(BaseAgent):
    def __init__(self):
        super().__init__("MemoryAgent", "phi3:mini")

    def handle(self, intent, detalhes, message):
        # 1. salvar
        if intent == "salvar":
            save_content = detalhes.get("salvar_conteudo") or ""
            if not save_content:
                return "🤖 O que você gostaria que eu salvasse?"

            category = classify_category(save_content)
            tokens = tokenize(save_content)
            chave = " ".join(tokens[:3]) if tokens else "geral"

            save_memory(category, chave, save_content)
            formatted_content = format_list_to_bullets(save_content)
            return (
                f"🤖 **Entendido!** Salvei essa informação na minha memória.<br><br>"
                f"📁 **Categoria:** {category}<br>"
                f"🔑 **Assunto:** {chave}<br>"
                f"📝 **Conteúdo:**<br>{formatted_content}"
            )

        # 2. buscar
        elif intent == "buscar":
            query = detalhes.get("buscar_query") or message
            memories = get_all_memories()
            best_match, score = search_best_memory(query, memories)

            if best_match and score >= 0.18:
                formatted_content = format_list_to_bullets(best_match['conteudo'])
                return f"🤖 Encontrei esta informação nas minhas memórias de **{best_match['categoria']}**:<br><br>{formatted_content}"
            else:
                return (
                    f"Desculpe, não encontrei nenhuma informação parecida registrada nas minhas memórias sobre seu pedido.<br><br>"
                    f"💡 **Quer que eu lembre disso?** Digite algo como:<br>"
                    f"*\"salve que o Wi-Fi de visitas é FamiliaFeliz2026!\"* ou *\"anote que a chave reserva fica no aparador\"*."
                )

        # 3. conversa
        elif intent == "conversa":
            return (
                "Olá! Sou o assistente virtual do DashFamília. Como posso ajudar você e sua família hoje? "
                "Posso lembrar de senhas, contatos, ferramentas ou gerenciar sua lista de compras!"
            )

        return None


class RecipeAgent(BaseAgent):
    def __init__(self):
        super().__init__("RecipeAgent", "qwen2.5:3b")

    def handle(self, intent, detalhes, message):
        # 1. salvar_receita
        if intent == "salvar_receita":
            nome = detalhes.get("nome")
            ingredientes = detalhes.get("ingredientes")
            passo_a_passo = detalhes.get("passo_a_passo")

            if not nome or not ingredientes:
                return "🤖 Para registrar uma receita, preciso pelo menos do nome e dos ingredientes!"

            formatted_content = format_recipe_content(ingredientes, passo_a_passo)
            save_memory("Receitas", nome, formatted_content)
            formatted_content_br = formatted_content.replace('\n', '<br>')
            return (
                f"🍳 **Receita registrada com sucesso!**<br><br>"
                f"📖 **Nome:** {nome.title()}<br><br>"
                f"{formatted_content_br}"
            )

        # 2. deletar_receita
        elif intent == "deletar_receita":
            recipe_name = detalhes.get("receita")
            if not recipe_name:
                return "🤖 Por favor, informe o nome da receita que deseja deletar."

            memories = get_all_memories()
            recipe_mem = None
            for m in memories:
                if m['categoria'] == 'Receitas' and m['chave'].lower().strip() == recipe_name.lower().strip():
                    recipe_mem = m
                    break

            if recipe_mem:
                delete_memory(recipe_mem['id'])
                return f"🗑️ **Receita '{recipe_name.title()}' deletada com sucesso!**"
            else:
                return f"🤖 Não encontrei nenhuma receita cadastrada com o nome '{recipe_name.title()}'."

        # 3. comprar_receita
        elif intent == "comprar_receita":
            recipe_name = detalhes.get("receita")
            if not recipe_name:
                return "🤖 Por favor, me diga qual receita você quer fazer para gerar a lista de compras!"

            memories = get_all_memories()
            recipe_mem = None
            recipes = [m for m in memories if m['categoria'] == 'Receitas']
            if recipes:
                best_match, score = search_best_memory(recipe_name, recipes)
                if best_match and score >= 0.15:
                    recipe_mem = best_match

            if recipe_mem:
                content = recipe_mem['conteudo']
                ingredients_list = []
                lines = content.split('\n')
                in_ingredients = False
                for line in lines:
                    line_strip = line.strip()
                    if line_strip.lower().startswith('ingredientes:'):
                        in_ingredients = True
                        continue
                    if line_strip.lower().startswith('passo a passo:'):
                        in_ingredients = False
                        continue
                    if in_ingredients:
                        if line_strip.startswith('-') or line_strip.startswith('*') or line_strip.startswith('•'):
                            cleaned = line_strip[1:].strip()
                            if cleaned:
                                ingredients_list.append(cleaned)
                        elif line_strip:
                            ingredients_list.append(line_strip)

                if not ingredients_list:
                    idx_inst = content.lower().find('passo a passo')
                    if idx_inst != -1:
                        ing_part = content[:idx_inst].strip()
                    else:
                        ing_part = content.strip()
                    if ing_part.lower().startswith('ingredientes:'):
                        ing_part = ing_part[len('ingredientes:'):].strip()
                    if '\n' in ing_part:
                        ingredients_list = [i.strip() for i in ing_part.split('\n') if i.strip()]
                    else:
                        ingredients_list = [i.strip() for i in ing_part.split(',') if i.strip()]

                cleaned_list = []
                for ing in ingredients_list:
                    item = ing.strip()
                    while item and item[0] in ['-', '*', '•', ' ']:
                        item = item[1:].strip()
                    if item:
                        cleaned_list.append(item)
                ingredients_list = cleaned_list

                if ingredients_list:
                    market_lists = [m for m in memories if m['categoria'] == 'Mercado']
                    if market_lists:
                        target_list = market_lists[0]
                        old_content = target_list['conteudo']
                        if ':' in old_content:
                            list_part = old_content.split(':', 1)[1].strip()
                        else:
                            list_part = old_content
                        list_part_clean = list_part.replace(' e ', ', ')
                        if list_part_clean.endswith('.'):
                            list_part_clean = list_part_clean[:-1]
                        list_part_clean = list_part_clean.strip()
                        old_items = [item.strip() for item in list_part_clean.split(',')]
                        old_items = [item for item in old_items if item]
                    else:
                        target_list = None
                        old_items = []

                    merged_items = []
                    seen_lower = set()
                    added_items = []

                    for item in old_items:
                        item_lower = item.lower().strip()
                        if item_lower not in seen_lower and item_lower != "":
                            seen_lower.add(item_lower)
                            merged_items.append(item.strip().capitalize())

                    for ing in ingredients_list:
                        if ing:
                            ing_clean_cap = ing[0].upper() + ing[1:]
                            ing_lower = ing.lower().strip()
                            if ing_lower not in seen_lower:
                                seen_lower.add(ing_lower)
                                merged_items.append(ing_clean_cap)
                                added_items.append(ing_clean_cap)

                    if merged_items:
                        if len(merged_items) > 1:
                            formatted_keep = ", ".join(merged_items[:-1]) + " e " + merged_items[-1]
                        else:
                            formatted_keep = merged_items[0]
                        new_content = f"A lista de compras do mercado é: {formatted_keep}."
                        if target_list:
                            save_memory("Mercado", target_list['chave'], new_content)
                        else:
                            save_memory("Mercado", "lista compras mercado", new_content)

                    formatted_ing_bullets = "<br>".join([f"• {ing}" for ing in ingredients_list])
                    reply = (
                        f"🛒 **Ingredientes para {recipe_mem['chave'].title()} obtidos!**<br><br>"
                        f"📋 **Itens necessários:**<br>{formatted_ing_bullets}<br><br>"
                    )
                    if added_items:
                        added_str = ", ".join(added_items)
                        reply += f"➕ **Adicionado(s) à sua lista de compras:** {added_str}<br>"
                    else:
                        reply += "✨ Todos os itens já estavam na sua lista de compras!<br>"
                    reply += f"<br>💡 *Você pode ver a lista atualizada no painel lateral!*"
                    return reply
                else:
                    return f"🤖 Não consegui extrair os ingredientes da receita '{recipe_mem['chave'].title()}'."
            else:
                return f"🤖 Não encontrei a receita '{recipe_name}' nas minhas memórias. Cadastre-a primeiro!"

        return None


class MedicinesAgent(BaseAgent):
    def __init__(self):
        super().__init__("MedicinesAgent", "meditron:7b")

    def handle(self, intent, detalhes, message):
        return (
            "💊 **Agente de Medicamentos (Base de Agentes Ativa)**<br><br>"
            "Olá! Estou preparado para gerenciar alarmes, receitas e dosagens de medicamentos em atualizações futuras.<br>"
            "Atualmente, posso registrar isso nas memórias gerais da casa se desejar!"
        )
