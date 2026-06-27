from .nlp_engine import parse_intent_with_ollama
from .agents import (
    parse_intent_locally,
    ListAgent, CalendarAgent, TaskAgent,
    FinanceAgent, MemoryAgent, RecipeAgent, MedicinesAgent
)

class Orchestrator:
    def __init__(self):
        # Instantiate sub-agents
        self.agents = {
            "adicionar_lista": ListAgent(),
            "remover_lista": ListAgent(),
            "limpar_lista": ListAgent(),
            "composto_lista": ListAgent(),
            "agendar_calendario": CalendarAgent(),
            "remover_calendario": CalendarAgent(),
            "completar_tarefa": TaskAgent(),
            "listar_tarefas": TaskAgent(),
            "resgatar_recompensa": TaskAgent(),
            "listar_recompensas_resgatadas": TaskAgent(),
            "adicionar_transacao": FinanceAgent(),
            "salvar": MemoryAgent(),
            "buscar": MemoryAgent(),
            "conversa": MemoryAgent(),
            "salvar_receita": RecipeAgent(),
            "deletar_receita": RecipeAgent(),
            "comprar_receita": RecipeAgent()
        }
        # Future agent placeholder
        self.medicines_agent = MedicinesAgent()

    def route(self, message):
        intent = None
        detalhes = {}
        parsed_ok = False
        is_ollama = False
        
        # 1. Try local Ollama NLU first (AI first)
        try:
            parsed_ok, ollama_json = parse_intent_with_ollama(message)
            if parsed_ok and ollama_json:
                intent = ollama_json.get("intencao")
                detalhes = ollama_json.get("detalhes", {})
                is_ollama = True
        except Exception as e:
            print(f"Ollama NLU error: {e}")
            parsed_ok = False
            
        # 2. If NLU fails or returns no intent, try local parser fallback
        if not intent:
            local_intent, local_detalhes = parse_intent_locally(message)
            if local_intent:
                intent = local_intent
                detalhes = local_detalhes
                parsed_ok = True
                is_ollama = False
            else:
                # Check if it was a failed save attempt while Ollama was offline
                save_keywords = ['salva', 'salvar', 'lembra', 'lembrar', 'anota', 'anotar', 'guarda', 'guardar', 'grave', 'gravar']
                is_save_attempt = any(kw in message.lower() for kw in save_keywords)
                if is_save_attempt:
                    reply = (
                        "🤖 **O Ollama está offline ou inacessível.**<br><br>"
                        "Não foi possível salvar essa informação na minha memória ativa no momento. "
                        "Por favor, tente novamente mais tarde ou verifique se o serviço está ativo. "
                        f"<button class='btn btn-sm btn-outline-primary chat-retry-btn' data-msg='{message}'>Tentar Novamente</button>"
                    )
                    return reply, False
                
        # 3. Route to the appropriate sub-agent
        if parsed_ok and intent:
            if intent in self.agents:
                agent = self.agents[intent]
                reply = agent.handle(intent, detalhes, message)
                return reply, is_ollama
            elif intent == "medicamentos":
                reply = self.medicines_agent.handle(intent, detalhes, message)
                return reply, is_ollama
                
        return None, is_ollama
