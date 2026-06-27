import unittest
import os
import sqlite3
import json
import datetime
from unittest.mock import patch, MagicMock

from modules.ia_memoria.database import (
    init_db, save_memory, get_all_memories, delete_memory,
    get_all_events, save_event, delete_event, get_all_tasks,
    complete_task_in_db, get_all_rewards, redeem_reward_in_db
)
from modules.ia_memoria.agents import (
    BaseAgent, ListAgent, CalendarAgent, TaskAgent,
    FinanceAgent, MemoryAgent, RecipeAgent, MedicinesAgent,
    parse_intent_locally, extract_date_from_text, parse_recipe_details,
    format_recipe_content
)
from modules.ia_memoria.orchestrator import Orchestrator

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_agents_database.db')

def force_clean_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS memorias")
        cursor.execute("DROP TABLE IF EXISTS eventos")
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        cursor.execute("DROP TABLE IF EXISTS tarefas")
        cursor.execute("DROP TABLE IF EXISTS recompensas")
        cursor.execute("DROP TABLE IF EXISTS transacoes")
        conn.commit()
        conn.close()
    except Exception:
        pass

class TestAgentsBase(unittest.TestCase):
    def setUp(self):
        from modules.ia_memoria import database
        self.old_db_path = database.DATABASE_PATH
        database.DATABASE_PATH = TEST_DB_PATH
        
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
            
        force_clean_db(TEST_DB_PATH)
        init_db(TEST_DB_PATH)
        
    def tearDown(self):
        from modules.ia_memoria import database
        database.DATABASE_PATH = self.old_db_path
        
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass


class TestOrchestrator(TestAgentsBase):
    @patch('modules.ia_memoria.orchestrator.parse_intent_with_ollama')
    def test_orchestrator_ollama_success(self, mock_ollama):
        # AI returns intent successfully
        mock_ollama.return_value = (True, {
            "intencao": "conversa",
            "detalhes": {}
        })
        
        orch = Orchestrator()
        reply, is_ollama = orch.route("oi")
        
        self.assertTrue(is_ollama)
        self.assertIn("Sou o assistente virtual", reply)

    @patch('modules.ia_memoria.orchestrator.parse_intent_with_ollama')
    def test_orchestrator_fallback_local(self, mock_ollama):
        # Ollama fails (returns false/offline)
        mock_ollama.return_value = (False, None)
        
        orch = Orchestrator()
        # Message has local pattern to complete task
        reply, is_ollama = orch.route("completei a pia")
        
        self.assertFalse(is_ollama)
        # Verify it falls back to TaskAgent task complete logic:
        self.assertIsNotNone(reply)

    @patch('modules.ia_memoria.orchestrator.parse_intent_with_ollama')
    def test_orchestrator_unrecognized_intent(self, mock_ollama):
        mock_ollama.return_value = (True, {"intencao": "desconhecida", "detalhes": {}})
        
        orch = Orchestrator()
        reply, is_ollama = orch.route("alguma coisa aleatoria")
        self.assertIsNone(reply)


class TestListAgent(TestAgentsBase):
    def test_list_agent_adicionar_lista_new(self):
        # Clear database Mercado memories first
        memories = get_all_memories(TEST_DB_PATH)
        for m in memories:
            if m["categoria"] == "Mercado":
                delete_memory(m["id"], TEST_DB_PATH)

        agent = ListAgent()
        reply = agent.handle("adicionar_lista", {"adicionar_itens": ["leite", "banana"]}, "adicionar leite e banana")
        self.assertIn("Nova lista criada", reply)
        self.assertIn("Leite", reply)
        self.assertIn("Banana", reply)

    def test_list_agent_adicionar_lista_merge(self):
        # Seed initial list
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão.", TEST_DB_PATH)
        
        agent = ListAgent()
        reply = agent.handle("adicionar_lista", {"adicionar_itens": ["leite"]}, "adicionar leite")
        self.assertIn("Item adicionado à lista", reply)
        self.assertIn("Pão", reply)
        self.assertIn("Leite", reply)

    def test_list_agent_remover_lista(self):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite e Manteiga.", TEST_DB_PATH)
        
        agent = ListAgent()
        reply = agent.handle("remover_lista", {"remover_itens": ["leite"]}, "remover leite")
        self.assertIn("Itens removidos da lista", reply)
        self.assertNotIn("Leite", reply)
        self.assertIn("Pão", reply)

    def test_list_agent_remover_lista_clear(self):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Leite.", TEST_DB_PATH)
        
        agent = ListAgent()
        reply = agent.handle("remover_lista", {"remover_itens": ["leite"]}, "remover leite")
        self.assertIn("Lista limpa", reply)

    def test_list_agent_composto_lista(self):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite.", TEST_DB_PATH)
        
        agent = ListAgent()
        reply = agent.handle("composto_lista", {"adicionar_itens": ["refrigerante"], "remover_itens": ["leite"]}, "remover leite e colocar refrigerante")
        self.assertIn("Lista de compras updated com sucesso", reply)
        self.assertIn("Refrigerante", reply)
        self.assertNotIn("• Leite", reply)

    def test_list_agent_limpar_lista(self):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite.", TEST_DB_PATH)
        
        agent = ListAgent()
        reply = agent.handle("limpar_lista", {"manter_itens": ["pão"]}, "comprei tudo exceto pão")
        self.assertIn("Itens mantidos para a próxima compra", reply)
        self.assertIn("Pão", reply)
        self.assertNotIn("Leite", reply)

        reply_clear_all = agent.handle("limpar_lista", {"manter_itens": []}, "comprei a lista inteira")
        self.assertIn("Todos os itens foram marcados como comprados", reply_clear_all)


class TestCalendarAgent(TestAgentsBase):
    def test_calendar_agent_agendar(self):
        agent = CalendarAgent()
        reply = agent.handle("agendar_calendario", {
            "titulo": "Reunião Importante",
            "data": "2026-07-15",
            "hora": "14:00",
            "localizacao": "Escritório",
            "recorrencia": "FREQ=WEEKLY;BYDAY=WE"
        }, "marcar reuniao dia 15/07 as 14:00")
        
        self.assertIn("Compromisso agendado com sucesso", reply)
        self.assertIn("Reunião Importante", reply)
        self.assertIn("15/07/2026", reply)

        # Verify event exists in DB
        events = get_all_events(TEST_DB_PATH)
        self.assertTrue(any(e["titulo"] == "Reunião Importante" for e in events))

    def test_calendar_agent_remover(self):
        save_event("Consulta Dentista", "2026-07-20", "10:00", "Mariana", "#00d2d3", "Saúde", db_path=TEST_DB_PATH)
        
        agent = CalendarAgent()
        reply = agent.handle("remover_calendario", {
            "titulo": "Dentista",
            "data": "2026-07-20"
        }, "desmarcar dentista no dia 20/07")
        
        self.assertIn("Compromisso(s) desmarcado(s) com sucesso", reply)
        self.assertIn("Consulta Dentista", reply)


class TestTaskAgent(TestAgentsBase):
    def test_task_agent_listar_tarefas(self):
        agent = TaskAgent()
        reply = agent.handle("listar_tarefas", {"usuario": "Isa"}, "quais as tarefas da Isa?")
        self.assertIn("Quadro de Missões Pendentes de Isa", reply)

    def test_task_agent_completar_tarefa(self):
        # Fetch active tasks and find Isa's ballet task or seed tasks
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tarefas (titulo, usuario_nome, completed, reward_xp, reward_gold, data, hora, categoria, dificuldade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("Lavar a louça", "Mari", 0, 50, 10, "2026-06-27", "12:00", "Casa", "Fácil"))
        conn.commit()
        conn.close()

        agent = TaskAgent()
        reply = agent.handle("completar_tarefa", {
            "usuario": "Mari",
            "tarefa": "Lavar a louça"
        }, "conclui lavar a louça")
        
        self.assertIn("Missão Concluída", reply)
        self.assertIn("Mari", reply)
        self.assertIn("Lavar a louça", reply)

    def test_task_agent_resgatar_recompensa(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        # Seed user with gold and a reward
        cursor.execute("UPDATE usuarios SET gold = 100 WHERE nome = 'Isa'")
        cursor.execute("INSERT INTO recompensas (titulo, custo, resgatado, usuario_nome, icone) VALUES (?, ?, ?, ?, ?)",
                       ("Assistir TV", 30, 0, "Isa", "📺"))
        conn.commit()
        conn.close()

        agent = TaskAgent()
        reply = agent.handle("resgatar_recompensa", {
            "usuario": "Isa",
            "recompensa": "Assistir TV"
        }, "Isa quer resgatar Assistir TV")
        
        self.assertIn("Recompensa Resgatada com Sucesso", reply)
        self.assertIn("Assistir TV", reply)
        self.assertIn("70 Ouro", reply) # 100 - 30

    def test_task_agent_skip_quest(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        # Seed user with stats
        cursor.execute("UPDATE usuarios SET xp = 0, gold = 0 WHERE nome = 'Mari'")
        cursor.execute("INSERT INTO tarefas (titulo, usuario_nome, completed, reward_xp, reward_gold, data, hora, categoria, dificuldade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("Skip me", "Mari", 0, 50, 10, "2026-06-27", "12:00", "Casa", "Fácil"))
        conn.commit()
        
        # Fetch task ID
        cursor.execute("SELECT id FROM tarefas WHERE titulo = 'Skip me'")
        task_id = cursor.fetchone()[0]
        conn.close()
        
        # Complete task with skip=True
        from modules.ia_memoria.database import complete_task_in_db, get_user_by_name
        success, user_profile, leveled_up = complete_task_in_db(task_id, skip=True)
        self.assertTrue(success)
        self.assertFalse(leveled_up)
        
        # Verify user rewards didn't change (still 0)
        self.assertEqual(user_profile['xp'], 0)
        self.assertEqual(user_profile['gold'], 0)
        
        # Verify task is completed in DB
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT completed FROM tarefas WHERE id = ?", (task_id,))
        completed = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(completed, 1)

    def test_task_consolidation(self):
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        # Clean current tasks
        cursor.execute("DELETE FROM tarefas")
        
        import datetime
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        past_str = (datetime.date.today() - datetime.timedelta(days=2)).strftime('%Y-%m-%d')
        
        # Seed uncompleted past task (should get +2*2=4 overdue XP and +2*1=2 overdue gold, total 10+4=14 XP and 1+2=3 gold)
        cursor.execute("INSERT INTO tarefas (titulo, usuario_nome, completed, reward_xp, reward_gold, data, hora, categoria, dificuldade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("Sapatos na sapateira", "Mari", 0, 10, 1, past_str, "19:00", "Casa", "Fácil"))
                       
        # Seed today's task
        cursor.execute("INSERT INTO tarefas (titulo, usuario_nome, completed, reward_xp, reward_gold, data, hora, categoria, dificuldade) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       ("Sapatos na sapateira", "Mari", 0, 10, 1, today_str, "19:00", "Casa", "Fácil"))
        conn.commit()
        conn.close()
        
        # Running consolidate_tasks_db consolidates the tasks
        from modules.ia_memoria.database import consolidate_tasks_db, get_all_tasks
        consolidate_tasks_db(TEST_DB_PATH)
        tasks = get_all_tasks()
        
        # Verify only 1 task remains (today's task)
        mari_tasks = [t for t in tasks if t['usuario_nome'] == 'Mari' and t['titulo'] == 'Sapatos na sapateira']
        self.assertEqual(len(mari_tasks), 1)
        self.assertEqual(mari_tasks[0]['data'], today_str)
        # Verify summed points: today's 10 XP + past's 14 XP = 24 XP
        self.assertEqual(mari_tasks[0]['reward_xp'], 24)
        # Verify summed gold: today's 1 Gold + past's 3 Gold = 4 Gold
        self.assertEqual(mari_tasks[0]['reward_gold'], 4)


class TestFinanceAgent(TestAgentsBase):
    def test_finance_agent_adicionar_transacao(self):
        agent = FinanceAgent()
        reply = agent.handle("adicionar_transacao", {
            "descricao": "Carrefour compras",
            "valor": -150.50
        }, "gastei 150.50 no Carrefour compras")
        
        self.assertIn("Transação registrada com sucesso", reply)
        self.assertIn("Carrefour compras", reply)
        self.assertIn("R$ 150,50", reply)
        self.assertIn("Alimentação e Supermercado", reply)


class TestMemoryAgent(TestAgentsBase):
    def test_memory_agent_salvar_buscar(self):
        agent = MemoryAgent()
        
        # Test Save
        reply_save = agent.handle("salvar", {"salvar_conteudo": "A chave reserva do apartamento fica com o Seu Ze do 102"}, "lembre que a chave reserva fica com o Seu Ze")
        self.assertIn("Salvei essa informação na minha memória", reply_save)
        
        # Test Search
        reply_search = agent.handle("buscar", {"buscar_query": "chave reserva"}, "onde fica a chave reserva?")
        self.assertIn("Encontrei esta informação nas minhas memórias", reply_search)
        self.assertIn("Seu Ze", reply_search)


class TestRecipeAgent(TestAgentsBase):
    def test_recipe_agent_salvar_deletar(self):
        agent = RecipeAgent()
        
        # Save Recipe
        reply_save = agent.handle("salvar_receita", {
            "nome": "Bolo de Cenoura",
            "ingredientes": "3 cenouras, 3 ovos, 1 xícara de óleo, 2 xícaras de açúcar, 2 xícaras de farinha",
            "passo_a_passo": "Bata tudo no liquidificador exceto farinha. Asse por 40 min."
        }, "salvar receita bolo de cenoura")
        self.assertIn("Receita registrada com sucesso", reply_save)
        
        # Buy recipe ingredients (integrates to Mercado)
        reply_buy = agent.handle("comprar_receita", {"receita": "Bolo de Cenoura"}, "comprar ingredientes do bolo de cenoura")
        self.assertIn("Ingredientes para Bolo De Cenoura obtidos", reply_buy)
        self.assertIn("Adicionado(s) à sua lista de compras", reply_buy)
        
        # Delete recipe
        reply_del = agent.handle("deletar_receita", {"receita": "Bolo de Cenoura"}, "excluir receita bolo de cenoura")
        self.assertIn("deletada com sucesso", reply_del)


class TestMedicinesAgent(TestAgentsBase):
    def test_medicines_agent_placeholder(self):
        agent = MedicinesAgent()
        reply = agent.handle("medicamentos", {}, "alarme para remedio")
        self.assertIn("Agente de Medicamentos", reply)


class TestLocalParserHelpers(unittest.TestCase):
    def test_extract_date_from_text(self):
        self.assertEqual(extract_date_from_text("festa amanhã"), (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
        self.assertEqual(extract_date_from_text("hoje de noite"), datetime.date.today().strftime("%Y-%m-%d"))
        self.assertEqual(extract_date_from_text("dia 2026-10-12"), "2026-10-12")
        self.assertEqual(extract_date_from_text("evento em 15/08/2026"), "2026-08-15")

    def test_parse_recipe_details(self):
        message = "salvar receita de Bolo:\nIngredientes:\n- Ovos\n- Açúcar\nPasso a passo:\n1. Misture tudo"
        details = parse_recipe_details(message)
        self.assertIsNotNone(details)
        self.assertEqual(details["nome"], "Bolo")
        self.assertIn("Ovos", details["ingredientes"])
        self.assertIn("Misture tudo", details["passo_a_passo"])

    def test_parse_intent_locally_wildcard_delete(self):
        intent, details = parse_intent_locally("cancelar todos os compromissos de amanhã")
        self.assertEqual(intent, "remover_calendario")
        self.assertIsNone(details["titulo"])
        self.assertEqual(details["data"], (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
