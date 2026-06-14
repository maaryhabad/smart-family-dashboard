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

def parse_intent_locally(message):
    """
    Fallback local parser using keyword/regex matching.
    Returns (intent, detalhes) or (None, None).
    """
    msg = message.lower().strip()
    
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
            task_kw = 'lixo'
        elif 'aspirar' in msg or 'passar pano' in msg or 'sala' in msg:
            task_kw = 'aspirar'
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
                if task_kw in ['caixa de areia', 'plantas', 'jantar', 'lixo', 'aspirar']:
                    user = 'Cassi'
                elif task_kw in ['brinquedos', 'mochila', 'água', 'ballet']:
                    user = 'Isa'
                elif task_kw in ['pia', 'alimentador', 'lençóis', 'poeira']:
                    user = 'Mari'
            return 'completar_tarefa', {'usuario': user, 'tarefa': task_kw or msg}
            
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
        
    return None, None

@ia_memoria_bp.route('/api/ia-memoria/chat', methods=['POST'])
def ia_chat():
    data = request.json or {}
    message = data.get("message", "").strip()
    
    if not message:
        return jsonify({"reply": "Por favor, digite uma pergunta válida!"})
        
    is_ollama_parsed = False
    items_to_add = None
    items_to_remove = None
    is_compound = False
    is_clear = False
    keep_items = None
    is_add = False
    is_remove = False
    is_save = False
    save_content = None
    
    reply_text = None
    
    # Try local parser first for tasks & rewards
    local_intent, local_detalhes = parse_intent_locally(message)
    intent = None
    detalhes = {}
    
    if local_intent:
        intent = local_intent
        detalhes = local_detalhes
        parsed_ok = True
    else:
        # Try local Ollama NLU
        try:
            parsed_ok, ollama_json = parse_intent_with_ollama(message)
            if parsed_ok and ollama_json:
                intent = ollama_json.get("intencao")
                detalhes = ollama_json.get("detalhes", {})
            else:
                parsed_ok = False
        except Exception as e:
            print(f"Ollama integration error: {e}")
            parsed_ok = False
            
    try:
        if parsed_ok and intent:
            if intent == "composto_lista":
                raw_add = detalhes.get("adicionar_itens") or []
                raw_remove = detalhes.get("remover_itens") or []
                if raw_add or raw_remove:
                    items_to_add = [clean_item_name(i) for i in raw_add if clean_item_name(i)]
                    items_to_remove = [clean_item_name(i) for i in raw_remove if clean_item_name(i)]
                    is_compound = True
                    is_ollama_parsed = True
            elif intent == "limpar_lista":
                is_clear = True
                raw_keep = detalhes.get("manter_itens") or []
                keep_items = [clean_item_name(i) for i in raw_keep if clean_item_name(i)]
                if not keep_items:
                    keep_items = None
                is_ollama_parsed = True
            elif intent == "adicionar_lista":
                raw_add = detalhes.get("adicionar_itens") or []
                if raw_add:
                    items_to_add = [clean_item_name(i) for i in raw_add if clean_item_name(i)]
                    is_add = True
                    is_ollama_parsed = True
            elif intent == "remover_lista":
                raw_remove = detalhes.get("remover_itens") or []
                if raw_remove:
                    items_to_remove = [clean_item_name(i) for i in raw_remove if clean_item_name(i)]
                    is_remove = True
                    is_ollama_parsed = True
            elif intent == "salvar":
                save_content = detalhes.get("salvar_conteudo") or ""
                if save_content:
                    is_save = True
                    is_ollama_parsed = True
            elif intent == "buscar":
                query = detalhes.get("buscar_query") or message
                memories = get_all_memories()
                best_match, score = search_best_memory(query, memories)
                
                if best_match and score >= 0.18:
                    formatted_content = format_list_to_bullets(best_match['conteudo'])
                    reply_text = f"🤖 Encontrei esta informação nas minhas memórias de **{best_match['categoria']}**:<br><br>{formatted_content}"
                else:
                    reply_text = (
                        f"Desculpe, não encontrei nenhuma informação parecida registrada nas minhas memórias sobre seu pedido.<br><br>"
                        f"💡 **Quer que eu lembre disso?** Digite algo como:<br>"
                        f"*\"salve que o Wi-Fi de visitas é FamiliaFeliz2026!\"* ou *\"anote que a chave reserva fica no aparador\"*."
                    )
                is_ollama_parsed = True
            elif intent == "conversa":
                reply_text = (
                    "Olá! Sou o assistente virtual do DashFamília. Como posso ajudar você e sua família hoje? "
                    "Posso lembrar de senhas, contatos, ferramentas ou gerenciar sua lista de compras!"
                )
                is_ollama_parsed = True
            elif intent == "agendar_calendario":
                event_title = detalhes.get("titulo") or "Compromisso sem título"
                event_date = detalhes.get("data")
                event_time = detalhes.get("hora") or "00:00"
                localizacao = detalhes.get("localizacao")
                recorrencia = detalhes.get("recorrencia")
                
                if not event_date:
                    import datetime
                    event_date = datetime.date.today().strftime("%Y-%m-%d")
                    
                event_id = save_event(
                    titulo=event_title,
                    data=event_date,
                    hora=event_time,
                    responsavel='Família',
                    cor='#5f27cd',
                    categoria='Familiar',
                    localizacao=localizacao,
                    recorrencia=recorrencia
                )
                
                try:
                    from .google_calendar import push_event_to_google_background
                    push_event_to_google_background(event_id, event_title, event_date, event_time, localizacao, recorrencia)
                except Exception as ex:
                    print(f"Google Calendar background sync trigger failed: {ex}")
                
                try:
                    parts = event_date.split("-")
                    formatted_date = f"{parts[2]}/{parts[1]}/{parts[0]}"
                except Exception:
                    formatted_date = event_date
                    
                recurrence_desc = None
                if recorrencia:
                    if "FREQ=WEEKLY" in recorrencia:
                        day_map = {
                            "MO": "segunda-feira",
                            "TU": "terça-feira",
                            "WE": "quarta-feira",
                            "TH": "quinta-feira",
                            "FR": "sexta-feira",
                            "SA": "sábado",
                            "SU": "domingo"
                        }
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
                    
                reply_text = (
                    f"📅 **Compromisso agendado com sucesso!**<br><br>"
                    f"📌 **Evento:** {event_title}<br>"
                    f"📅 **Data:** {formatted_date}<br>"
                    f"🕒 **Hora:** {event_time}<br>"
                )
                if localizacao:
                    reply_text += f"📍 **Local:** {localizacao}<br>"
                if recurrence_desc:
                    reply_text += f"🔁 **Repetição:** {recurrence_desc}<br>"
                reply_text += f"<br>💡 *Sincronizando com o Google Calendar em background...*"
                is_ollama_parsed = True
            elif intent == "remover_calendario":
                event_title = detalhes.get("titulo")
                event_date = detalhes.get("data")
                
                if not event_title and not event_date:
                    reply_text = "🤖 Para remover um compromisso, por favor informe o título ou a data dele!"
                    is_ollama_parsed = True
                else:
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
                        reply_text = f"🤖 Não encontrei nenhum compromisso sobre {query_desc} no calendário."
                        is_ollama_parsed = True
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
                        reply_text = (
                            f"📅 **Compromisso(s) desmarcado(s) com sucesso!**<br><br>"
                            f"🗑️ **Removido(s):** {deleted_str}<br><br>"
                            f"💡 *Sincronizando exclusão com o Google Calendar em background...*"
                        )
                        is_ollama_parsed = True
            elif intent == "completar_tarefa":
                user_param = detalhes.get("usuario")
                task_search = detalhes.get("tarefa") or ""
                
                # Fetch all tasks from DB
                all_tasks = get_all_tasks()
                active_tasks = [t for t in all_tasks if not t['completed']]
                
                if user_param:
                    active_tasks = [t for t in active_tasks if t['usuario_nome'].lower() == user_param.lower()]
                    
                matched_task = None
                if task_search:
                    search_term = task_search.lower()
                    # Substring match
                    for t in active_tasks:
                        if search_term in t['titulo'].lower():
                            matched_task = t
                            break
                    # Token overlap match
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
                        reply_text = (
                            f"⚔️ **Missão Concluída!**<br><br>"
                            f"👤 **Membro:** {matched_task['usuario_nome']}<br>"
                            f"📜 **Tarefa:** {matched_task['titulo']}<br>"
                            f"🔵 **XP ganho:** +{matched_task['reward_xp']}<br>"
                            f"🪙 **Ouro ganho:** +{matched_task['reward_gold']}<br><br>"
                            f"🎉 *Seu progresso foi atualizado no painel e o checkmark (✅) foi adicionado ao calendário!*"
                        )
                        if leveled_up:
                            reply_text += (
                                f"<br><br>✨ **LEVEL UP!** 🎉<br>"
                                f"🌟 **{user_profile['nome']}** subiu para o **Nível {user_profile['nivel']}**! 🚀"
                            )
                    else:
                        reply_text = f"🤖 A tarefa '{matched_task['titulo']}' já foi concluída anteriormente!"
                else:
                    user_str = f" para {user_param}" if user_param else ""
                    reply_text = (
                        f"🤖 Não encontrei nenhuma tarefa pendente relacionada a '{task_search}'{user_str}.<br><br>"
                        f"💡 Verifique as missões ativas na aba **To-Do List Gamer**!"
                    )
                is_ollama_parsed = True
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
                        reply_text = (
                            f"🛒 **Recompensa Resgatada com Sucesso!**<br><br>"
                            f"👤 **Quem resgatou:** {matched_reward['usuario_nome']}<br>"
                            f"🎁 **Recompensa:** {matched_reward['icone']} {matched_reward['titulo']}<br>"
                            f"🪙 **Custo:** {matched_reward['custo']} Ouro<br>"
                            f"💰 **Saldo Atual:** {user_profile['gold']} Ouro<br><br>"
                            f"🎉 *Divirta-se! O saldo de ouro foi atualizado no painel.*"
                        )
                    else:
                        reply_text = f"⚠️ **Não foi possível resgatar:** {msg_redeem}"
                else:
                    reply_text = f"🤖 Não encontrei nenhuma recompensa pendente correspondente a '{reward_search}'. Verifique a Loja de Recompensas!"
                is_ollama_parsed = True
            elif intent == "listar_tarefas":
                user_param = detalhes.get("usuario")
                
                all_tasks = get_all_tasks()
                pending_tasks = [t for t in all_tasks if not t['completed']]
                
                if user_param:
                    pending_tasks = [t for t in pending_tasks if t['usuario_nome'].lower() == user_param.lower()]
                    
                if not pending_tasks:
                    reply_text = "🎉 **Todas as tarefas estão em dia!** Não há missões pendentes no momento."
                else:
                    user_desc = f" de {user_param}" if user_param else ""
                    reply_text = f"📜 **Quadro de Missões Pendentes{user_desc}:**<br><br>"
                    for t in pending_tasks:
                        reply_text += f"• **{t['usuario_nome']}**: {t['titulo']} ({t['hora']}) - *🔵 {t['reward_xp']} XP | 🪙 {t['reward_gold']} Gold*<br>"
                is_ollama_parsed = True
        else:
            # Ollama offline or returned invalid response
            reply_text = (
                "🤖 <b>O Ollama está offline ou inacessível.</b><br><br>"
                "Para usar a inteligência artificial da casa, por favor certifique-se de que:<br>"
                "1. O aplicativo <b>Ollama</b> está rodando em seu computador.<br>"
                "2. O modelo de linguagem (ex: <code>qwen2:1.5b</code>) foi baixado.<br><br>"
                '<button class="btn btn-primary btn-sm" style="margin-top: 8px; background: #5f27cd; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;" onclick="window.retryLastChatMessage()">'
                "🔄 Tentar Novamente</button>"
            )
            is_ollama_parsed = True
    except Exception as e:
        print(f"Ollama integration error: {e}")
        reply_text = (
            "🤖 <b>Ocorreu um erro de conexão com o Ollama.</b><br><br>"
            "Por favor, certifique-se de que o Ollama está rodando localmente na porta 11434.<br><br>"
            '<button class="btn btn-primary btn-sm" style="margin-top: 8px; background: #5f27cd; border: none; color: white; padding: 6px 12px; border-radius: 4px; cursor: pointer;" onclick="window.retryLastChatMessage()">'
            "🔄 Tentar Novamente</button>"
        )
        is_ollama_parsed = True
                        
    # Now execute logic based on the determined intent
    if reply_text is None:
        if is_compound:
            memories = get_all_memories()
            market_lists = [m for m in memories if m['categoria'] == 'Mercado']
            
            # 1. Apply removals if list exists
            if market_lists:
                target_list = market_lists[0]
                old_content = target_list['conteudo']
                
                # Parse items from existing list
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
                
                if items_to_remove:
                    remove_set_lower = {item.lower().strip() for item in items_to_remove}
                    remaining_items = [item for item in old_items if item.lower().strip() not in remove_set_lower]
                else:
                    remaining_items = old_items
            else:
                remaining_items = []
                
            # 2. Apply additions
            if items_to_add:
                merged_items = []
                seen_lower = set()
                for item in remaining_items + items_to_add:
                    item_lower = item.lower().strip()
                    if item_lower not in seen_lower and item_lower != "":
                         seen_lower.add(item_lower)
                         merged_items.append(item.strip().capitalize())
            else:
                merged_items = [item.capitalize() for item in remaining_items]
                
            if merged_items:
                # Reconstruct list sentence
                if len(merged_items) > 1:
                    formatted_keep = ", ".join(merged_items[:-1]) + " e " + merged_items[-1]
                else:
                    formatted_keep = merged_items[0]
                    
                new_content = f"A lista de compras do mercado é: {formatted_keep}."
                
                if market_lists:
                    save_memory("Mercado", market_lists[0]['chave'], new_content)
                else:
                    save_memory("Mercado", "lista compras mercado", new_content)
                    
                formatted_bullets = format_list_to_bullets(new_content)
                
                removed_str = ", ".join(items_to_remove) if items_to_remove else "nenhum"
                added_str = ", ".join(items_to_add) if items_to_add else "nenhum"
                
                reply_text = (
                    f"🛒 **Lista de compras updated com sucesso!**<br><br>"
                    f"➖ **Removido(s):** {removed_str}<br>"
                    f"➕ **Adicionado(s):** {added_str}<br><br>"
                    f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                )
            else:
                if market_lists:
                    delete_memory(market_lists[0]['id'])
                reply_text = "🎉 **Lista de compras limpa!** Removi todos os itens solicitados e a lista de compras ficou vazia."
                
        elif is_clear:
            memories = get_all_memories()
            market_lists = [m for m in memories if m['categoria'] == 'Mercado']
            
            if not market_lists:
                reply_text = "🤖 Não encontrei nenhuma lista de compras ativa nas minhas memórias para atualizar!"
            else:
                target_list = market_lists[0]
                
                if keep_items:
                    # Update list with kept items
                    if len(keep_items) > 1:
                        formatted_keep = ", ".join(keep_items[:-1]) + " e " + keep_items[-1]
                    else:
                        formatted_keep = keep_items[0]
                    new_content = f"A lista de compras do mercado é: {formatted_keep}."
                    save_memory("Mercado", target_list['chave'], new_content)
                    
                    formatted_bullets = format_list_to_bullets(new_content)
                    reply_text = (
                        f"🛒 **Entendido!** Atualizei a lista nas minhas memórias e marquei os outros itens como comprados.<br><br>"
                        f"📝 **Itens mantidos para a próxima compra:**<br>{formatted_bullets}"
                    )
                else:
                    # Delete list entirely
                    delete_memory(target_list['id'])
                    reply_text = "🎉 **Parabéns!** Todos os itens foram marcados como comprados e a lista de compras foi limpa das minhas memórias! 🛒"
                    
        elif is_add:
            memories = get_all_memories()
            market_lists = [m for m in memories if m['categoria'] == 'Mercado']
            
            if not market_lists:
                # If no list exists, create a new one!
                if len(items_to_add) > 1:
                    formatted_items = ", ".join(items_to_add[:-1]) + " e " + items_to_add[-1]
                else:
                    formatted_items = items_to_add[0]
                new_content = f"A lista de compras do mercado é: {formatted_items}."
                save_memory("Mercado", "lista compras mercado", new_content)
                
                formatted_bullets = format_list_to_bullets(new_content)
                reply_text = (
                    f"🛒 **Nova lista criada!** Como não encontrei nenhuma lista ativa, criei uma nova com esses itens:<br><br>"
                    f"{formatted_bullets}"
                )
            else:
                target_list = market_lists[0]
                old_content = target_list['conteudo']
                
                # Parse items from the existing list content
                if ':' in old_content:
                    list_part = old_content.split(':', 1)[1].strip()
                else:
                    list_part = old_content
                    
                # Clean ' e ' or periods and split by commas
                list_part_clean = list_part.replace(' e ', ', ')
                if list_part_clean.endswith('.'):
                    list_part_clean = list_part_clean[:-1]
                list_part_clean = list_part_clean.strip()
                
                old_items = [item.strip() for item in list_part_clean.split(',')]
                old_items = [item for item in old_items if item]
                
                # Merge old items and new items, removing duplicates (case-insensitive)
                merged_items = []
                seen_lower = set()
                
                for item in old_items + items_to_add:
                    item_lower = item.lower().strip()
                    if item_lower not in seen_lower and item_lower != "":
                        seen_lower.add(item_lower)
                        merged_items.append(item.strip().capitalize())
                        
                if merged_items:
                    # Reconstruct sentence: join with commas and ' e ' for the last item
                    if len(merged_items) > 1:
                        formatted_keep = ", ".join(merged_items[:-1]) + " e " + merged_items[-1]
                    else:
                        formatted_keep = merged_items[0]
                        
                    new_content = f"A lista de compras do mercado é: {formatted_keep}."
                    save_memory("Mercado", target_list['chave'], new_content)
                    
                    formatted_bullets = format_list_to_bullets(new_content)
                    reply_text = (
                        f"🛒 **Item adicionado à lista!** Atualizei sua lista de compras.<br><br>"
                        f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                    )
                else:
                    delete_memory(target_list['id'])
                    reply_text = "🎉 A lista de compras foi limpa das minhas memórias!"
                    
        elif is_remove:
            memories = get_all_memories()
            market_lists = [m for m in memories if m['categoria'] == 'Mercado']
            
            if not market_lists:
                reply_text = "🤖 Não encontrei nenhuma lista de compras ativa nas minhas memórias para remover itens!"
            else:
                target_list = market_lists[0]
                old_content = target_list['conteudo']
                
                # Parse items from the existing list content
                if ':' in old_content:
                    list_part = old_content.split(':', 1)[1].strip()
                else:
                    list_part = old_content
                    
                # Clean connecting ' e ' or periods and split by commas
                list_part_clean = list_part.replace(' e ', ', ')
                if list_part_clean.endswith('.'):
                    list_part_clean = list_part_clean[:-1]
                list_part_clean = list_part_clean.strip()
                
                old_items = [item.strip() for item in list_part_clean.split(',')]
                old_items = [item for item in old_items if item]
                
                # Filter out items that match the removal request (case-insensitive)
                remove_set_lower = {item.lower().strip() for item in items_to_remove}
                remaining_items = []
                
                for item in old_items:
                    if item.lower().strip() not in remove_set_lower:
                        remaining_items.append(item)
                        
                if remaining_items:
                    # Reconstruct list sentence
                    if len(remaining_items) > 1:
                        formatted_keep = ", ".join(remaining_items[:-1]) + " e " + remaining_items[-1]
                    else:
                        formatted_keep = remaining_items[0]
                        
                    new_content = f"A lista de compras do mercado é: {formatted_keep}."
                    save_memory("Mercado", target_list['chave'], new_content)
                    
                    formatted_bullets = format_list_to_bullets(new_content)
                    reply_text = (
                        f"🛒 **Itens removidos da lista!** Atualizei sua lista de compras.<br><br>"
                        f"📝 **Lista atualizada:**<br>{formatted_bullets}"
                    )
                else:
                    delete_memory(target_list['id'])
                    reply_text = "🎉 **Lista limpa!** Removi todos os itens e limpei a lista de compras das minhas memórias."
                    
        elif is_save:
            category = classify_category(save_content)
            tokens = tokenize(save_content)
            chave = " ".join(tokens[:3]) if tokens else "geral"
            
            save_memory(category, chave, save_content)
            
            formatted_content = format_list_to_bullets(save_content)
            reply_text = (
                f"🤖 **Entendido!** Salvei essa informação na minha memória.<br><br>"
                f"📁 **Categoria:** {category}<br>"
                f"🔑 **Assunto:** {chave}<br>"
                f"📝 **Conteúdo:**<br>{formatted_content}"
            )
            
        else:
            # Default search path
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
        if "O Ollama está offline" not in reply_text and "Ocorreu um erro de conexão" not in reply_text:
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
        
    # Execute database correction logic immediately
    try:
        if correct_intent == "adicionar_lista":
            items_to_add = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
            if items_to_add:
                memories = get_all_memories()
                market_lists = [m for m in memories if m['categoria'] == 'Mercado']
                if not market_lists:
                    if len(items_to_add) > 1:
                        formatted_items = ", ".join(items_to_add[:-1]) + " e " + items_to_add[-1]
                    else:
                        formatted_items = items_to_add[0]
                    new_content = f"A lista de compras do mercado é: {formatted_items}."
                    save_memory("Mercado", "lista compras mercado", new_content)
                else:
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
                        new_content = f"A lista de compras do mercado é: {formatted_keep}."
                        save_memory("Mercado", target_list['chave'], new_content)
                    else:
                        delete_memory(target_list['id'])
                        
        elif correct_intent == "remover_lista":
            items_to_remove = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
            if items_to_remove:
                memories = get_all_memories()
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
                    
                    remove_set_lower = {item.lower().strip() for item in items_to_remove}
                    remaining_items = [item for item in old_items if item.lower().strip() not in remove_set_lower]
                    
                    if remaining_items:
                        if len(remaining_items) > 1:
                            formatted_keep = ", ".join(remaining_items[:-1]) + " e " + remaining_items[-1]
                        else:
                            formatted_keep = remaining_items[0]
                        new_content = f"A lista de compras do mercado é: {formatted_keep}."
                        save_memory("Mercado", target_list['chave'], new_content)
                    else:
                        delete_memory(target_list['id'])
                        
        elif correct_intent == "limpar_lista":
            keep_items = [clean_item_name(i) for i in details.split(",") if clean_item_name(i)]
            memories = get_all_memories()
            market_lists = [m for m in memories if m['categoria'] == 'Mercado']
            if market_lists:
                target_list = market_lists[0]
                if keep_items:
                    if len(keep_items) > 1:
                        formatted_keep = ", ".join(keep_items[:-1]) + " e " + keep_items[-1]
                    else:
                        formatted_keep = keep_items[0]
                    new_content = f"A lista de compras do mercado é: {formatted_keep}."
                    save_memory("Mercado", target_list['chave'], new_content)
                else:
                    delete_memory(target_list['id'])
                    
        elif correct_intent == "salvar":
            if details:
                category = classify_category(details)
                tokens = tokenize(details)
                chave = " ".join(tokens[:3]) if tokens else "geral"
                save_memory(category, chave, details)
                
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
                
            if event_title or event_date:
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
                            
                for me in matched_events:
                    delete_event(me['id'])
                    g_id = me.get('google_event_id')
                    if g_id:
                        try:
                            from .google_calendar import delete_event_from_google_background
                            delete_event_from_google_background(g_id)
                        except Exception as ex:
                            print(f"Google Calendar background delete trigger failed: {ex}")
                
    except Exception as e:
        print(f"Error updating database during feedback execution: {e}")
        return jsonify({"success": False, "error": f"Erro ao atualizar banco de dados: {str(e)}"}), 500

    # Save the feedback to json and rebuild Modelfile
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
                
        # Build expected assistant JSON response
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



