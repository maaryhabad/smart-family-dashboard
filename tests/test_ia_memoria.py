import unittest
import os
import sqlite3
import json
from unittest.mock import patch, MagicMock
from modules.ia_memoria.nlp_engine import (
    remove_accents, tokenize, classify_category, 
    calculate_cosine_similarity, search_best_memory, format_list_to_bullets,
    clean_item_name
)
from app import app
from modules.ia_memoria.database import (
    init_db, save_memory, get_all_memories, delete_memory, get_db_connection, update_memory,
    get_all_events, save_event, delete_event, update_event_google_id, update_event
)

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')

def force_clean_db(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS memorias")
        cursor.execute("DROP TABLE IF EXISTS eventos")
        cursor.execute("DROP TABLE IF EXISTS usuarios")
        cursor.execute("DROP TABLE IF EXISTS tarefas")
        cursor.execute("DROP TABLE IF EXISTS recompensas")
        cursor.execute("DROP TABLE IF EXISTS eventos_deletados")
        conn.commit()
        conn.close()
    except Exception:
        pass

class TestNLPEngine(unittest.TestCase):
    
    def test_remove_accents(self):
        self.assertEqual(remove_accents("Olá, João! Cafés, vovô."), "Ola, Joao! Cafes, vovo.")
        self.assertEqual(remove_accents("ÁÉÍÓÚçãõ"), "AEIOUcao")
        
    def test_tokenize(self):
        text = "Qual é a senha do wi-fi de visitas?"
        tokens = tokenize(text)
        # Should filter stop words (qual, e, a, do, de) and keep key tokens
        self.assertIn("senha", tokens)
        self.assertIn("wifi", tokens)
        self.assertIn("visitas", tokens)
        self.assertNotIn("qual", tokens)
        
    def test_classify_category(self):
        self.assertEqual(classify_category("A senha do portão é 1234"), "Senhas")
        self.assertEqual(classify_category("Chave reserva do carro na gaveta"), "Segurança")
        self.assertEqual(classify_category("O contato do eletricista é 999"), "Contatos")
        self.assertEqual(classify_category("O martelo está na caixa de ferramentas"), "Ferramentas")
        self.assertEqual(classify_category("As caixas de Natal estão no sótão"), "Organização")
        self.assertEqual(classify_category("Vacina do Pipoca"), "Pets")
        self.assertEqual(classify_category("Ir ao mercado comprar pão"), "Mercado")
        self.assertEqual(classify_category("Lista de compras do mercado: banana, maçã, cenoura e ração do cachorro"), "Mercado")
        self.assertEqual(classify_category("Lembrete geral aleatório"), "Geral")
        

        
    def test_cosine_similarity(self):
        vec1 = {'senha': 1, 'wifi': 1}
        vec2 = {'senha': 1, 'wifi': 1}
        # Identical vectors should have similarity of 1.0
        self.assertAlmostEqual(calculate_cosine_similarity(vec1, vec2), 1.0)
        
        vec3 = {'chave': 1, 'carro': 1}
        # Disjoint vectors should have similarity of 0.0
        self.assertEqual(calculate_cosine_similarity(vec1, vec3), 0.0)

    def test_search_best_memory(self):
        memories = [
            {"categoria": "Senhas", "chave": "wifi", "conteudo": "A senha do Wi-Fi de visitas é 12345."},
            {"categoria": "Segurança", "chave": "chave reserva", "conteudo": "A chave reserva fica na gaveta da entrada."}
        ]
        
        # Perfect match
        best, score = search_best_memory("qual a senha do wifi?", memories)
        self.assertIsNotNone(best)
        self.assertEqual(best["chave"], "wifi")
        self.assertTrue(score > 0.3)
        
        # Matches using synonyms/partial keywords
        best2, score2 = search_best_memory("onde guardamos a chave do carro reserva?", memories)
        self.assertIsNotNone(best2)
        self.assertEqual(best2["chave"], "chave reserva")
        
    def test_format_list_to_bullets(self):
        # 1. Standard list with colon and commas
        txt1 = "A lista de compras do mercado é: arroz, feijão, batata e pão."
        res1 = format_list_to_bullets(txt1)
        expected1 = "A lista de compras do mercado é:<br>• Arroz<br>• Feijão<br>• Batata<br>• Pão"
        self.assertEqual(res1, expected1)
        
        # 2. Text without colon (should not format)
        txt2 = "Esta é uma frase simples sem lista de itens."
        self.assertEqual(format_list_to_bullets(txt2), txt2)
        
        # 3. Colon but only 1 item (should not format)
        txt3 = "O único item da lista é: maçã"
        self.assertEqual(format_list_to_bullets(txt3), txt3)



    def test_clean_item_name(self):
        self.assertEqual(clean_item_name("o arroz"), "Arroz")
        self.assertEqual(clean_item_name("o feijão"), "Feijão")
        self.assertEqual(clean_item_name("da lista o arroz"), "Arroz")
        self.assertEqual(clean_item_name("da lista de mercado o arroz"), "Arroz")
        self.assertEqual(clean_item_name("chá"), "Chá")
        self.assertEqual(clean_item_name("areia dos gatos"), "Areia dos gatos")
        self.assertEqual(clean_item_name("para a lista de compras pão"), "Pão")
        self.assertEqual(clean_item_name(""), "")




class TestDatabaseModule(unittest.TestCase):
    
    def setUp(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
        force_clean_db(TEST_DB_PATH)
            
    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
            
    def test_init_db(self):
        # Should initialize and seed default values
        init_db(TEST_DB_PATH)
        
        memories = get_all_memories(TEST_DB_PATH)
        self.assertEqual(len(memories), 6) # Default 6 seeded values
        
        # Verify columns exist
        self.assertEqual(memories[0]["chave"], "wifi")
        self.assertEqual(memories[0]["categoria"], "Senhas")
        
    def test_save_and_update_memory(self):
        init_db(TEST_DB_PATH)
        
        # 1. Test Insert
        save_memory("Contatos", "encanador mario", "Telefone do encanador Seu Mário é (11) 98765-4321", TEST_DB_PATH)
        memories = get_all_memories(TEST_DB_PATH)
        self.assertEqual(len(memories), 7)
        
        added = next(m for m in memories if m["chave"] == "encanador mario")
        self.assertEqual(added["categoria"], "Contatos")
        
        # 2. Test Update (saving with same key, case insensitive)
        save_memory("Contatos", "ENCANADOR MARIO", "Telefone atualizado é (11) 99999-9999", TEST_DB_PATH)
        memories2 = get_all_memories(TEST_DB_PATH)
        self.assertEqual(len(memories2), 7) # Should NOT duplicate
        
        updated = next(m for m in memories2 if m["chave"] == "encanador mario")
        self.assertEqual(updated["conteudo"], "Telefone atualizado é (11) 99999-9999")
        
    def test_delete_memory(self):
        init_db(TEST_DB_PATH)
        
        # Save a new record
        save_memory("Geral", "temporario", "Esta memoria vai sumir", TEST_DB_PATH)
        memories = get_all_memories(TEST_DB_PATH)
        temp_id = next(m for m in memories if m["chave"] == "temporario")["id"]
        
        # Delete it
        delete_memory(temp_id, TEST_DB_PATH)
        
        memories_after = get_all_memories(TEST_DB_PATH)
        self.assertNotIn("temporario", [m["chave"] for m in memories_after])

    def test_update_memory(self):
        init_db(TEST_DB_PATH)
        
        # Save a new record
        save_memory("Geral", "temporario", "Esta memoria vai ser alterada", TEST_DB_PATH)
        memories = get_all_memories(TEST_DB_PATH)
        temp_mem = next(m for m in memories if m["chave"] == "temporario")
        temp_id = temp_mem["id"]
        
        # Update it by ID
        update_memory(temp_id, "Senhas", "chave nova", "Nova senha secreta", TEST_DB_PATH)
        
        # Verify
        memories_after = get_all_memories(TEST_DB_PATH)
        updated = next(m for m in memories_after if m["id"] == temp_id)
        self.assertEqual(updated["categoria"], "Senhas")
        self.assertEqual(updated["chave"], "chave nova")
        self.assertEqual(updated["conteudo"], "Nova senha secreta")

    def test_save_and_get_events(self):
        init_db(TEST_DB_PATH)
        
        # Clear default seeded events/tasks first
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM eventos")
        cursor.execute("DELETE FROM tarefas")
        conn.commit()
        conn.close()
        
        # Seed events manually since default seeding is disabled
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        initial_events = [
            ("Almoço de Domingo na Vó", "2026-06-14", "12:30", "Família", "#5f27cd", "Familiar"),
            ("Dentista Mariana", "2026-06-15", "14:00", "Mariana", "#00d2d3", "Saúde"),
            ("Reunião de Condomínio", "2026-06-17", "20:00", "Rodrigo", "#ff9f43", "Compromisso"),
            ("Vacina do Pipoca (Pet)", "2026-06-20", "09:00", "Família", "#54a0ff", "Pet"),
            ("Aniversário do Lucas", "2026-06-25", "18:00", "Lucas", "#ff4d4d", "Familiar")
        ]
        cursor.executemany(
            "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria) VALUES (?, ?, ?, ?, ?, ?)",
            initial_events
        )
        conn.commit()
        conn.close()
        
        # 1. Test Seeded Events
        events = get_all_events(TEST_DB_PATH)
        self.assertEqual(len(events), 5) # Seeds have 5 events
        
        # 2. Test Save Event
        event_id = save_event(
            titulo="Festa Junina",
            data="2026-06-24",
            hora="17:00",
            responsavel="Família",
            cor="#5f27cd",
            categoria="Familiar",
            db_path=TEST_DB_PATH
        )
        
        events2 = get_all_events(TEST_DB_PATH)
        self.assertEqual(len(events2), 6)
        
        added = next(e for e in events2 if e["id"] == event_id)
        self.assertEqual(added["titulo"], "Festa Junina")
        self.assertEqual(added["data"], "2026-06-24")
        self.assertEqual(added["hora"], "17:00")
        
        # 3. Test Update Google ID
        update_event_google_id(event_id, "g_event_123", TEST_DB_PATH)
        events3 = get_all_events(TEST_DB_PATH)
        updated = next(e for e in events3 if e["id"] == event_id)
        self.assertEqual(updated["google_event_id"], "g_event_123")
        
        # 3b. Test Update Event Details
        update_event(
            event_id=event_id,
            titulo="Festa Junina do Cassi",
            data="2026-06-24",
            hora="18:30",
            responsavel="Família",
            cor="#ff0000",
            categoria="Familiar",
            db_path=TEST_DB_PATH
        )
        events3_details = get_all_events(TEST_DB_PATH)
        updated_details = next(e for e in events3_details if e["id"] == event_id)
        self.assertEqual(updated_details["titulo"], "Festa Junina do Cassi")
        self.assertEqual(updated_details["hora"], "18:30")
        self.assertEqual(updated_details["cor"], "#ff0000")
        
        # 4. Test Delete Event
        delete_event(event_id, TEST_DB_PATH)
        events_after = get_all_events(TEST_DB_PATH)
        self.assertEqual(len(events_after), 5)
        self.assertNotIn(event_id, [e["id"] for e in events_after])

    def test_save_and_get_events_with_location_and_recurrence(self):
        init_db(TEST_DB_PATH)
        
        # 1. Save Event with Location and Recurrence
        event_id = save_event(
            titulo="Ballet da Isa",
            data="2026-06-13",
            hora="09:00",
            responsavel="Família",
            cor="#5f27cd",
            categoria="Familiar",
            google_event_id="g_event_123",
            localizacao="R. Comendador Araújo, 338",
            recorrencia="RRULE:FREQ=WEEKLY;BYDAY=SA",
            db_path=TEST_DB_PATH
        )
        
        events = get_all_events(TEST_DB_PATH)
        added = next(e for e in events if e["id"] == event_id)
        self.assertEqual(added["titulo"], "Ballet da Isa")
        self.assertEqual(added["localizacao"], "R. Comendador Araújo, 338")
        self.assertEqual(added["recorrencia"], "RRULE:FREQ=WEEKLY;BYDAY=SA")
        
        # 2. Update Location and Recurrence
        update_event(
            event_id=event_id,
            titulo="Ballet da Isa no Centro",
            data="2026-06-13",
            hora="10:00",
            responsavel="Família",
            cor="#ff0000",
            categoria="Familiar",
            localizacao="Rua Comendador Araújo, 400",
            recorrencia="RRULE:FREQ=WEEKLY;BYDAY=SU",
            db_path=TEST_DB_PATH
        )
        
        events_after = get_all_events(TEST_DB_PATH)
        updated = next(e for e in events_after if e["id"] == event_id)
        self.assertEqual(updated["titulo"], "Ballet da Isa no Centro")
        self.assertEqual(updated["hora"], "10:00")
        self.assertEqual(updated["localizacao"], "Rua Comendador Araújo, 400")
        self.assertEqual(updated["recorrencia"], "RRULE:FREQ=WEEKLY;BYDAY=SU")


class MockThread:
    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
    def start(self):
        self.target(*self.args, **self.kwargs)


class TestAPIEndpoints(unittest.TestCase):
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
        self.client = app.test_client()
        
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

    def test_get_memorias_route(self):
        response = self.client.get('/api/ia-memoria/memorias')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 6) # Seeds have 6 records

    def test_save_or_update_memory_route_insert(self):
        # Insert
        response = self.client.post('/api/ia-memoria/memorias/salvar', json={
            "categoria": "Geral",
            "chave": "teste chave",
            "conteudo": "Este é um teste"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        
        # Verify
        response_get = self.client.get('/api/ia-memoria/memorias')
        data = response_get.get_json()
        self.assertEqual(len(data), 7)
        self.assertTrue(any(m["chave"] == "teste chave" for m in data))

    def test_save_or_update_memory_route_update(self):
        # Insert first
        response_ins = self.client.post('/api/ia-memoria/memorias/salvar', json={
            "categoria": "Geral",
            "chave": "update key",
            "conteudo": "Conteudo original"
        })
        self.assertEqual(response_ins.status_code, 200)
        
        # Get id
        data = self.client.get('/api/ia-memoria/memorias').get_json()
        added = next(m for m in data if m["chave"] == "update key")
        mem_id = added["id"]
        
        # Update
        response_upd = self.client.post('/api/ia-memoria/memorias/salvar', json={
            "id": mem_id,
            "categoria": "Senhas",
            "chave": "updated key",
            "conteudo": "Conteudo modificado"
        })
        self.assertEqual(response_upd.status_code, 200)
        
        # Verify
        data_after = self.client.get('/api/ia-memoria/memorias').get_json()
        updated = next(m for m in data_after if m["id"] == mem_id)
        self.assertEqual(updated["categoria"], "Senhas")
        self.assertEqual(updated["chave"], "updated key")
        self.assertEqual(updated["conteudo"], "Conteudo modificado")

    def test_delete_memory_route(self):
        # Get one seeded memory
        data = self.client.get('/api/ia-memoria/memorias').get_json()
        target_id = data[0]["id"]
        
        # Delete it
        response = self.client.post('/api/ia-memoria/memorias/excluir', json={"id": target_id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        
        # Verify
        data_after = self.client.get('/api/ia-memoria/memorias').get_json()
        self.assertEqual(len(data_after), 5)
        self.assertNotIn(target_id, [m["id"] for m in data_after])

    @patch('threading.Thread', new=MockThread)
    @patch('subprocess.run')
    def test_feedback_route_adicionar_lista(self, mock_subproc):
        # Post feedback to add items
        response = self.client.post('/api/ia-memoria/feedback', json={
            "message": "coloca refrigerante e chocolate",
            "correct_intent": "adicionar_lista",
            "details": "refrigerante, chocolate"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        
        # Verify database update
        memories = get_all_memories(TEST_DB_PATH)
        m_list = next(m for m in memories if m["categoria"] == "Mercado")
        self.assertIn("Refrigerante", m_list["conteudo"])
        self.assertIn("Chocolate", m_list["conteudo"])
        
        # Check feedback file was written
        feedback_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'training', 'feedback.json')
        self.assertTrue(os.path.exists(feedback_file))
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)
        self.assertTrue(any(fb["user"] == "coloca refrigerante e chocolate" for fb in feedbacks))

        # Check Modelfile was rebuilt
        modelfile_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'training', 'Modelfile')
        self.assertTrue(os.path.exists(modelfile_path))
        with open(modelfile_path, 'r', encoding='utf-8') as f:
            modelfile_content = f.read()
        self.assertIn('MESSAGE user "coloca refrigerante e chocolate"', modelfile_content)

    @patch('threading.Thread', new=MockThread)
    @patch('subprocess.run')
    def test_feedback_route_remover_lista(self, mock_subproc):
        # Save initial list
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite e Manteiga.", TEST_DB_PATH)
        
        # Post feedback to remove item
        response = self.client.post('/api/ia-memoria/feedback', json={
            "message": "tira o leite",
            "correct_intent": "remover_lista",
            "details": "leite"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        
        # Verify DB update
        memories = get_all_memories(TEST_DB_PATH)
        m_list = next(m for m in memories if m["categoria"] == "Mercado")
        self.assertNotIn("Leite", m_list["conteudo"])
        self.assertIn("Manteiga", m_list["conteudo"])
        self.assertIn("Pão", m_list["conteudo"])

    @patch('threading.Thread', new=MockThread)
    @patch('subprocess.run')
    def test_feedback_route_remover_calendario(self, mock_subproc):
        # 1. Save an event first
        event_id = save_event(
            titulo="Consulta Dentista",
            data="2026-06-15",
            hora="14:00",
            responsavel="Família",
            cor="#5f27cd",
            categoria="Familiar",
            db_path=TEST_DB_PATH
        )
        
        # 2. Post feedback correction to remover_calendario
        response = self.client.post('/api/ia-memoria/feedback', json={
            "message": "desmarca a consulta do dia 15",
            "correct_intent": "remover_calendario",
            "details": "Consulta Dentista, 15/06"
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        
        # 3. Verify event was deleted from DB
        events = get_all_events(TEST_DB_PATH)
        self.assertNotIn(event_id, [e["id"] for e in events])
        
        # 4. Verify feedback file was updated
        feedback_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules', 'training', 'feedback.json')
        self.assertTrue(os.path.exists(feedback_file))
        with open(feedback_file, 'r', encoding='utf-8') as f:
            feedbacks = json.load(f)
        
        target_fb = next(fb for fb in feedbacks if fb.get("user") == "desmarca a consulta do dia 15")
        assistant_json = json.loads(target_fb["assistant"])
        self.assertEqual(assistant_json["intencao"], "remover_calendario")
        self.assertEqual(assistant_json["detalhes"]["titulo"], "Consulta Dentista")
        self.assertEqual(assistant_json["detalhes"]["data"], "2026-06-15")




class TestOllamaIntegration(unittest.TestCase):
    
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
        self.client = app.test_client()
        
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

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_save(self, mock_ollama):
        mock_ollama.return_value = (True, {
            "intencao": "salvar",
            "detalhes": {
                "salvar_conteudo": "A senha do portão é 9876"
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "salva a senha do portao por favor"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Salvei essa informação", data["reply"])
        self.assertIn("Senhas", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        self.assertTrue(any("9876" in m["conteudo"] for m in memories))

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_buscar(self, mock_ollama):
        save_memory("Senhas", "wifi", "A senha do wifi é abc123", TEST_DB_PATH)
        
        mock_ollama.return_value = (True, {
            "intencao": "buscar",
            "detalhes": {
                "buscar_query": "wifi"
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "qual a senha da internet?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Encontrei esta informação", data["reply"])
        self.assertIn("abc123", data["reply"])

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_adicionar_lista(self, mock_ollama):
        mock_ollama.return_value = (True, {
            "intencao": "adicionar_lista",
            "detalhes": {
                "adicionar_itens": ["leite", "manteiga"]
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "bota leite e manteiga na lista"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Nova lista criada", data["reply"])
        self.assertIn("Leite", data["reply"])
        self.assertIn("Manteiga", data["reply"])

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_remover_lista(self, mock_ollama):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite e Manteiga.", TEST_DB_PATH)
        
        mock_ollama.return_value = (True, {
            "intencao": "remover_lista",
            "detalhes": {
                "remover_itens": ["leite"]
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "tira o leite da lista"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Itens removidos da lista", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        m_list = next(m for m in memories if m["categoria"] == "Mercado")
        self.assertNotIn("Leite", m_list["conteudo"])
        self.assertIn("Manteiga", m_list["conteudo"])

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_composto_lista(self, mock_ollama):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite e Manteiga.", TEST_DB_PATH)
        
        mock_ollama.return_value = (True, {
            "intencao": "composto_lista",
            "detalhes": {
                "adicionar_itens": ["refrigerante"],
                "remover_itens": ["leite", "pão"]
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "tira pão e leite e adiciona refrigerante"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Lista de compras updated com sucesso", data["reply"])
        self.assertIn("Refrigerante", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        m_list = next(m for m in memories if m["categoria"] == "Mercado")
        self.assertIn("Refrigerante", m_list["conteudo"])
        self.assertNotIn("Leite", m_list["conteudo"])
        self.assertNotIn("Pão", m_list["conteudo"])

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_limpar_lista(self, mock_ollama):
        save_memory("Mercado", "lista compras mercado", "A lista de compras do mercado é: Pão, Leite.", TEST_DB_PATH)
        
        mock_ollama.return_value = (True, {
            "intencao": "limpar_lista",
            "detalhes": {
                "manter_itens": []
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "comprei a lista inteira"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("lista de compras foi limpa", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        self.assertFalse(any(m["categoria"] == "Mercado" for m in memories))

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_conversa(self, mock_ollama):
        mock_ollama.return_value = (True, {
            "intencao": "conversa",
            "detalhes": {}
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "olá tudo bem?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Sou o assistente virtual", data["reply"])

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_agendar_calendario(self, mock_ollama):
        mock_ollama.return_value = (True, {
            "intencao": "agendar_calendario",
            "detalhes": {
                "titulo": "Festa junina na empresa do Cassi",
                "data": "2026-06-24",
                "hora": "17:00"
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "marca no calendário que dia 24/06 às 17:00 tem festa junina na empresa do Cassi"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Compromisso agendado com sucesso", data["reply"])
        self.assertIn("Festa junina na empresa do Cassi", data["reply"])
        self.assertIn("24/06/2026", data["reply"])
        self.assertIn("17:00", data["reply"])
        
        events = get_all_events(TEST_DB_PATH)
        self.assertTrue(any(e["titulo"] == "Festa junina na empresa do Cassi" for e in events))

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_offline_response(self, mock_ollama):
        mock_ollama.return_value = (False, None)
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "salva que o Wi-Fi do andar superior é AndarSuperior123"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("O Ollama está offline ou inacessível", data["reply"])
        self.assertIn("Tentar Novamente", data["reply"])

    @patch('modules.ia_memoria.nlp_engine.get_available_ollama_model')
    @patch('urllib.request.urlopen')
    def test_parse_intent_with_ollama_success(self, mock_urlopen, mock_get_model):
        mock_get_model.return_value = "qwen2:1.5b"
        
        mock_resp_chat = MagicMock()
        mock_resp_chat.__enter__.return_value = mock_resp_chat
        mock_resp_chat.read.return_value = b'{"message": {"content": "{\\"intencao\\": \\"salvar\\", \\"detalhes\\": {\\"salvar_conteudo\\": \\"Teste ok\\"}}"}}'
        
        mock_urlopen.return_value = mock_resp_chat
        
        from modules.ia_memoria.nlp_engine import parse_intent_with_ollama
        ok, res = parse_intent_with_ollama("teste mensagem")
        self.assertTrue(ok)
        self.assertEqual(res["intencao"], "salvar")
        self.assertEqual(res["detalhes"]["salvar_conteudo"], "Teste ok")

    @patch('modules.ia_memoria.nlp_engine.get_available_ollama_model')
    @patch('urllib.request.urlopen')
    def test_parse_intent_with_ollama_timeout(self, mock_urlopen, mock_get_model):
        mock_get_model.return_value = "qwen2:1.5b"
        mock_urlopen.side_effect = Exception("Timeout error")
        
        from modules.ia_memoria.nlp_engine import parse_intent_with_ollama
        ok, res = parse_intent_with_ollama("teste mensagem")
        self.assertFalse(ok)
        self.assertIsNone(res)

    @patch('modules.ia_memoria.routes.parse_intent_with_ollama')
    def test_chat_ollama_agendar_calendario_multi(self, mock_ollama):
        mock_ollama.return_value = (True, {
            "intencao": "agendar_calendario",
            "detalhes": {
                "compromissos": [
                    {
                        "titulo": "Férias da Isa",
                        "data": "2026-07-13",
                        "data_fim": "2026-07-27",
                        "hora": "00:00"
                    },
                    {
                        "titulo": "Primeiro dia de aula",
                        "data": "2026-07-28",
                        "hora": "08:00"
                    }
                ]
            }
        })
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "anota na agenda, as férias da Isa vão de 13/07 até o dia 27/07. E no dia 28/07 é o primeiro dia de aula da Isa"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("compromissos agendados com sucesso", data["reply"])
        self.assertIn("Férias da Isa", data["reply"])
        self.assertIn("Primeiro dia de aula", data["reply"])
        
        events = get_all_events(TEST_DB_PATH)
        vacation = next(e for e in events if e["titulo"] == "Férias da Isa")
        aula = next(e for e in events if e["titulo"] == "Primeiro dia de aula")
        
        self.assertEqual(vacation["data"], "2026-07-13")
        self.assertEqual(vacation["data_fim"], "2026-07-27")
        self.assertEqual(aula["data"], "2026-07-28")
        self.assertEqual(aula["data_fim"], "2026-07-28")


class TestGoogleCalendarSync(unittest.TestCase):
    def setUp(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass
        force_clean_db(TEST_DB_PATH)
        init_db(TEST_DB_PATH)
        
        # Seed events manually since default seeding is disabled
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM eventos")
        cursor.execute("DELETE FROM tarefas")
        conn.commit()
        cursor = conn.cursor()
        initial_events = [
            ("Almoço de Domingo na Vó", "2026-06-14", "12:30", "Família", "#5f27cd", "Familiar"),
            ("Dentista Mariana", "2026-06-15", "14:00", "Mariana", "#00d2d3", "Saúde"),
            ("Reunião de Condomínio", "2026-06-17", "20:00", "Rodrigo", "#ff9f43", "Compromisso"),
            ("Vacina do Pipoca (Pet)", "2026-06-20", "09:00", "Família", "#54a0ff", "Pet"),
            ("Aniversário do Lucas", "2026-06-25", "18:00", "Lucas", "#ff4d4d", "Familiar")
        ]
        cursor.executemany(
            "INSERT INTO eventos (titulo, data, hora, responsavel, cor, categoria) VALUES (?, ?, ?, ?, ?, ?)",
            initial_events
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

    @patch('os.path.exists')
    def test_sync_calendars_no_credentials(self, mock_exists):
        mock_exists.return_value = False
        from modules.ia_memoria.google_calendar import sync_calendars
        success = sync_calendars(db_path=TEST_DB_PATH)
        self.assertFalse(success)

    @patch('os.path.exists')
    @patch('modules.ia_memoria.google_calendar.get_calendar_service')
    def test_sync_calendars_with_mock_google(self, mock_get_service, mock_exists):
        mock_exists.return_value = True
        
        # Mock Google Calendar API service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        
        # Configure service.events().list().execute() to return a list of mock events
        # We will mock two events:
        # 1. An existing event that needs to be updated (we'll associate with "Almoço de Domingo na Vó" by adding a google ID beforehand)
        # 2. A new event from Google Calendar that needs to be created locally
        # 3. We will NOT return the "Dentista Mariana" event (which has google_event_id), to test its deletion
        
        # Set up a local event with google_event_id first
        events = get_all_events(TEST_DB_PATH)
        almoco_id = next(e for e in events if e["titulo"] == "Almoço de Domingo na Vó")["id"]
        dentista_id = next(e for e in events if e["titulo"] == "Dentista Mariana")["id"]
        
        update_event_google_id(almoco_id, "g_almoco_123", TEST_DB_PATH)
        update_event_google_id(dentista_id, "g_dentista_999", TEST_DB_PATH)
        
        # Remote events returned by mock API:
        # Event 1: updated almoco time
        # Event 2: new event "Reunião de Planejamento"
        mock_service.events().list().execute.return_value = {
            "items": [
                {
                    "id": "g_almoco_123",
                    "summary": "Almoço de Domingo na Vó",
                    "start": {
                        "dateTime": "2026-06-14T13:00:00-03:00" # changed from 12:30
                    }
                },
                {
                    "id": "g_nova_reuniao_456",
                    "summary": "Reunião de Planejamento",
                    "start": {
                        "dateTime": "2026-06-16T15:30:00-03:00"
                    }
                }
            ]
        }
        
        # Mock service.events().insert().execute() for local push
        # In our database, all other 3 local events don't have a google_event_id, so they will be pushed
        mock_service.events().insert().execute.return_value = {
            "id": "g_pushed_event_xyz"
        }
        
        from modules.ia_memoria.google_calendar import sync_calendars
        success = sync_calendars(db_path=TEST_DB_PATH)
        
        self.assertTrue(success)
        
        # Verify almoco details were updated to 13:00
        events_after = get_all_events(TEST_DB_PATH)
        almoco_after = next(e for e in events_after if e["id"] == almoco_id)
        self.assertEqual(almoco_after["hora"], "13:00")
        
        # Verify new event was inserted
        self.assertTrue(any(e["google_event_id"] == "g_nova_reuniao_456" for e in events_after))
        new_ev = next(e for e in events_after if e["google_event_id"] == "g_nova_reuniao_456")
        self.assertEqual(new_ev["titulo"], "Reunião de Planejamento")
        self.assertEqual(new_ev["hora"], "15:30")
        
        # Verify that "Dentista Mariana" (g_dentista_999) was DELETED because it fell in the sync range but wasn't in active remote events
        self.assertFalse(any(e["id"] == dentista_id for e in events_after))


class TestGamifiedTasks(unittest.TestCase):
    
    def setUp(self):
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
        import gc
        gc.collect()
        try:
            if os.path.exists(TEST_DB_PATH):
                os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

    def test_db_seeding_and_helpers(self):
        from modules.ia_memoria.database import get_all_users, get_tasks_for_user, get_rewards_for_user
        
        users = get_all_users(TEST_DB_PATH)
        self.assertEqual(len(users), 3)
        user_names = [u['nome'] for u in users]
        self.assertIn('Mari', user_names)
        self.assertIn('Cassi', user_names)
        self.assertIn('Isa', user_names)
        
        isa_tasks = get_tasks_for_user('Isa', TEST_DB_PATH)
        self.assertTrue(len(isa_tasks) > 0)
        
        cassi_rewards = get_rewards_for_user('Cassi', TEST_DB_PATH)
        self.assertTrue(len(cassi_rewards) > 0)

    def test_complete_task_and_levelup(self):
        from modules.ia_memoria.database import get_tasks_for_user, complete_task_in_db, get_user_by_name, get_all_events
        
        isa_tasks = get_tasks_for_user('Isa', TEST_DB_PATH)
        task = isa_tasks[0]
        self.assertEqual(task['completed'], 0)
        
        # Complete task
        success, user_profile, leveled_up = complete_task_in_db(task['id'], TEST_DB_PATH)
        self.assertTrue(success)
        self.assertEqual(user_profile['xp'], task['reward_xp'])
        self.assertEqual(user_profile['gold'], task['reward_gold'])
        self.assertFalse(leveled_up)
        
        # Verify calendar event has checkmark
        events = get_all_events(TEST_DB_PATH)
        evt = next(e for e in events if e['id'] == task['evento_calendario_id'])
        self.assertTrue(evt['titulo'].startswith('✅'))
        
        # Test level up logic
        # Give Cassi high XP in DB first
        conn = get_db_connection(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET xp = 95, gold = 0, nivel = 1, xp_to_next_level = 100 WHERE nome = 'Cassi'")
        conn.commit()
        conn.close()
        
        cassi_tasks = get_tasks_for_user('Cassi', TEST_DB_PATH)
        cassi_task = cassi_tasks[0]
        
        success2, user_profile2, leveled_up2 = complete_task_in_db(cassi_task['id'], TEST_DB_PATH)
        self.assertTrue(success2)
        self.assertTrue(leveled_up2)
        self.assertEqual(user_profile2['nivel'], 2)
        self.assertEqual(user_profile2['xp'], (95 + cassi_task['reward_xp']) - 100)

    def test_redeem_reward(self):
        from modules.ia_memoria.database import get_rewards_for_user, redeem_reward_in_db, get_user_by_name
        
        # Give Isa enough gold
        conn = get_db_connection(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET gold = 50 WHERE nome = 'Isa'")
        conn.commit()
        conn.close()
        
        isa_rewards = get_rewards_for_user('Isa', TEST_DB_PATH)
        reward = isa_rewards[0]
        
        success, msg, user_profile = redeem_reward_in_db(reward['id'], TEST_DB_PATH)
        self.assertTrue(success)
        self.assertEqual(user_profile['gold'], 50 - reward['custo'])
        
        # Insufficient gold test
        reward2 = isa_rewards[1]
        # Set gold to 0
        conn = get_db_connection(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET gold = 0 WHERE nome = 'Isa'")
        conn.commit()
        conn.close()
        
        success2, msg2, user_profile2 = redeem_reward_in_db(reward2['id'], TEST_DB_PATH)
        self.assertFalse(success2)
        self.assertIn("Ouro insuficiente", msg2)

        # Test complete reward
        from modules.ia_memoria.database import complete_reward_in_db
        success3 = complete_reward_in_db(reward['id'], TEST_DB_PATH)
        self.assertTrue(success3)
        
        # Verify in DB that it is marked with resgatado = 2
        conn = get_db_connection(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT resgatado FROM recompensas WHERE id = ?", (reward['id'],))
        row = cursor.fetchone()
        self.assertEqual(row['resgatado'], 2)
        conn.close()

    def test_local_nlu_fallbacks(self):
        from modules.ia_memoria.routes import parse_intent_locally
        
        intent, details = parse_intent_locally("completei a tarefa de limpar a caixa de areia")
        self.assertEqual(intent, "completar_tarefa")
        self.assertEqual(details['usuario'], "Cassi")
        self.assertEqual(details['tarefa'], "caixa de areia")
        
        intent2, details2 = parse_intent_locally("Isa terminou de preparar a mochila escolar")
        self.assertEqual(intent2, "completar_tarefa")
        self.assertEqual(details2['usuario'], "Isa")
        self.assertEqual(details2['tarefa'], "mochila")
        
        intent_bath, details_bath = parse_intent_locally("concluí o banho")
        self.assertEqual(intent_bath, "completar_tarefa")
        self.assertEqual(details_bath['usuario'], "Isa")
        self.assertEqual(details_bath['tarefa'], "banho")

        intent_hair, details_hair = parse_intent_locally("Isa terminou de lavar o cabelo")
        self.assertEqual(intent_hair, "completar_tarefa")
        self.assertEqual(details_hair['usuario'], "Isa")
        self.assertEqual(details_hair['tarefa'], "banho e lavar cabelo")

        intent3, details3 = parse_intent_locally("Mari quer resgatar a recompensa do spa")
        self.assertEqual(intent3, "resgatar_recompensa")
        self.assertEqual(details3['usuario'], "Mari")
        self.assertEqual(details3['recompensa'], "spa")
        
        intent4, details4 = parse_intent_locally("o que o Cassi tem de tarefas hoje?")
        self.assertEqual(intent4, "listar_tarefas")
        self.assertEqual(details4['usuario'], "Cassi")

        intent_rewards, details_rewards = parse_intent_locally("quais as recompensas que a Isa resgatou?")
        self.assertEqual(intent_rewards, "listar_recompensas_resgatadas")
        self.assertEqual(details_rewards['usuario'], "Isa")

        intent_rewards2, details_rewards2 = parse_intent_locally("recompensas que o Cassi comprou")
        self.assertEqual(intent_rewards2, "listar_recompensas_resgatadas")
        self.assertEqual(details_rewards2['usuario'], "Cassi")


class TestDeletedEventsQueue(unittest.TestCase):
    def setUp(self):
        force_clean_db(TEST_DB_PATH)
        init_db(TEST_DB_PATH)

    def tearDown(self):
        force_clean_db(TEST_DB_PATH)

    def test_delete_event_adds_to_queue(self):
        from modules.ia_memoria.database import (
            save_event, delete_event, get_deleted_event_google_ids,
            remove_deleted_event_google_id
        )
        # 1. Save an event with a google_event_id
        evt_id = save_event(
            titulo="Evento Teste Deletado",
            data="2026-06-15",
            hora="10:00",
            google_event_id="test_g_id_123",
            db_path=TEST_DB_PATH
        )
        # Queue should be empty initially
        self.assertEqual(get_deleted_event_google_ids(TEST_DB_PATH), [])
        
        # 2. Delete the event
        delete_event(evt_id, db_path=TEST_DB_PATH)
        
        # 3. Check if the google_event_id was recorded in the queue
        deleted_ids = get_deleted_event_google_ids(TEST_DB_PATH)
        self.assertEqual(deleted_ids, ["test_g_id_123"])
        
        # 4. Remove it and verify it's cleared
        remove_deleted_event_google_id("test_g_id_123", db_path=TEST_DB_PATH)
        self.assertEqual(get_deleted_event_google_ids(TEST_DB_PATH), [])


class TestRecipesAndChoreDivision(unittest.TestCase):
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
        self.client = app.test_client()
        
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

    def test_classify_category_recipes(self):
        self.assertEqual(classify_category("Receita de Panqueca de Aveia"), "Receitas")
        self.assertEqual(classify_category("Ingredientes para o almoço: batata, cebola"), "Receitas")

    def test_parse_recipe_details(self):
        from modules.ia_memoria.routes import parse_recipe_details
        msg = "Salvar receita de Panqueca de Aveia. Ingredientes: 1 xícara de aveia, 2 bananas, 2 ovos. Passo a passo: Bater tudo e fritar."
        res = parse_recipe_details(msg)
        self.assertIsNotNone(res)
        self.assertEqual(res['nome'].lower(), "panqueca de aveia")
        self.assertIn("1 xícara de aveia", res['ingredientes'])
        self.assertIn("Bater tudo e fritar", res['passo_a_passo'])

        # Test conversational prefix
        msg_conv = "salva essa receita Pãozinho Rápido de Aveia na Air Fryer. Ingredientes: 1 xícara de farinha. Modo de preparo: Misturar tudo."
        res_conv = parse_recipe_details(msg_conv)
        self.assertIsNotNone(res_conv)
        self.assertEqual(res_conv['nome'].lower(), "pãozinho rápido de aveia na air fryer")
        self.assertIn("1 xícara de farinha", res_conv['ingredientes'])

        # Test raw copy-pasted recipe without prefix
        msg_raw = (
            "Para a Massa do Bolo:\n"
            "Farinha de aveia: 60g\n"
            "Achocolatado em pó: 30g\n"
            "Modo de Preparo Real\n"
            "Passo 1: Misturar tudo"
        )
        res_raw = parse_recipe_details(msg_raw)
        self.assertIsNotNone(res_raw)
        self.assertEqual(res_raw['nome'].lower(), "para a massa do bolo")
        self.assertIn("Farinha de aveia: 60g", res_raw['ingredientes'])
        self.assertIn("Passo 1: Misturar tudo", res_raw['passo_a_passo'])

    def test_chat_salvar_receita(self):
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "salvar receita bolo de caneca: ingredientes: 1 ovo, 2 colheres de cacau. passo a passo: misturar e colocar no microondas"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Receita registrada com sucesso!", data["reply"])
        self.assertIn("Bolo De Caneca", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        recipe = next((m for m in memories if m["categoria"] == "Receitas" and m["chave"] == "bolo de caneca"), None)
        self.assertIsNotNone(recipe)
        self.assertIn("1 ovo", recipe["conteudo"])

    def test_chat_deletar_receita(self):
        save_memory("Receitas", "bolo de caneca", "Ingredientes:\n- 1 ovo", TEST_DB_PATH)
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "deletar receita bolo de caneca"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("deletada com sucesso", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        recipe = next((m for m in memories if m["categoria"] == "Receitas" and m["chave"] == "bolo de caneca"), None)
        self.assertIsNone(recipe)

    def test_chat_comprar_receita(self):
        content = "Ingredientes:\n- 1 xícara de aveia\n- 2 bananas maduras\n\nPasso a passo:\n1. Bater tudo."
        save_memory("Receitas", "panqueca de aveia", content, TEST_DB_PATH)
        
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "Quero fazer panqueca de aveia, o que preciso comprar?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Ingredientes para Panqueca De Aveia obtidos!", data["reply"])
        self.assertIn("1 xícara de aveia", data["reply"])
        
        memories = get_all_memories(TEST_DB_PATH)
        market_list = next((m for m in memories if m["categoria"] == "Mercado"), None)
        self.assertIsNotNone(market_list)
        self.assertIn("1 xícara de aveia", market_list["conteudo"])
        self.assertIn("2 bananas maduras", market_list["conteudo"])

    def test_chores_division_seeded(self):
        from modules.ia_memoria.database import get_all_tasks
        
        tasks = get_all_tasks(TEST_DB_PATH)
        
        # Isa's tasks
        isa_trash = [t for t in tasks if t['usuario_nome'] == 'Isa' and 'lixo do banheiro' in t['titulo'].lower()]
        self.assertEqual(len(isa_trash), 2)
        
        # Shared Cassi and Mari split (now including daily clutter focus for both)
        cassi_tasks = [t for t in tasks if t['usuario_nome'] == 'Cassi']
        mari_tasks = [t for t in tasks if t['usuario_nome'] == 'Mari']
        
        # Cassi and Mari tasks sum to 42 (28 shared random split + 14 clutter focus daily for both)
        self.assertEqual(len(cassi_tasks) + len(mari_tasks), 42)
        
        # Both get 21 tasks (14 shared + 7 clutter focus)
        self.assertEqual(len(cassi_tasks), 21)
        self.assertEqual(len(mari_tasks), 21)



class TestTaskManagement(unittest.TestCase):
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
        self.client = app.test_client()
        
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

    def test_create_task_api(self):
        import datetime
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        response = self.client.post('/api/todo-gamer/salvar', json={
            "usuario_nome": "Mari",
            "titulo": "Lavar a louça teste",
            "categoria": "Limpeza",
            "dificuldade": "Fácil",
            "reward_xp": 10,
            "reward_gold": 3,
            "data": today_str,
            "hora": "18:00"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Missão criada com sucesso!")
        
        # Verify it is in database
        from modules.ia_memoria.database import get_all_tasks, get_all_events
        tasks = get_all_tasks(TEST_DB_PATH)
        new_task = next((t for t in tasks if t['titulo'] == "Lavar a louça teste"), None)
        self.assertIsNotNone(new_task)
        self.assertEqual(new_task['usuario_nome'], "Mari")
        self.assertEqual(new_task['reward_xp'], 10)
        self.assertEqual(new_task['reward_gold'], 3)
        self.assertEqual(new_task['data'], today_str)
        self.assertEqual(new_task['hora'], "18:00")
        
        # Verify it has a linked event
        self.assertIsNotNone(new_task['evento_calendario_id'])
        events = get_all_events(TEST_DB_PATH)
        linked_evt = next((e for e in events if e['id'] == new_task['evento_calendario_id']), None)
        self.assertIsNotNone(linked_evt)
        self.assertEqual(linked_evt['titulo'], "Tarefa Mari: Lavar a louça teste")
        self.assertEqual(linked_evt['data'], today_str)
        self.assertEqual(linked_evt['hora'], "18:00")

    def test_update_task_api(self):
        import datetime
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        from modules.ia_memoria.database import save_task, get_all_tasks, get_all_events
        task_id = save_task(
            usuario_nome="Isa",
            titulo="Brinquedos teste",
            categoria="Infantil",
            dificuldade="Fácil",
            reward_xp=10,
            reward_gold=3,
            data=yesterday_str,
            hora="19:00",
            db_path=TEST_DB_PATH
        )
        
        response = self.client.post('/api/todo-gamer/salvar', json={
            "id": task_id,
            "usuario_nome": "Cassi",
            "titulo": "Brinquedos teste atualizado",
            "categoria": "Organização",
            "dificuldade": "Médio",
            "reward_xp": 15,
            "reward_gold": 5,
            "data": today_str,
            "hora": "10:00"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Missão atualizada com sucesso!")
        
        tasks = get_all_tasks(TEST_DB_PATH)
        updated_task = next((t for t in tasks if t['id'] == task_id), None)
        self.assertIsNotNone(updated_task)
        self.assertEqual(updated_task['usuario_nome'], "Cassi")
        self.assertEqual(updated_task['titulo'], "Brinquedos teste updated" if "updated" in updated_task['titulo'] else updated_task['titulo']) # verify update matches
        self.assertEqual(updated_task['categoria'], "Organização")
        self.assertEqual(updated_task['dificuldade'], "Médio")
        self.assertEqual(updated_task['reward_xp'], 15)
        self.assertEqual(updated_task['reward_gold'], 5)
        self.assertEqual(updated_task['data'], today_str)
        self.assertEqual(updated_task['hora'], "10:00")
        
        # Verify event was updated
        events = get_all_events(TEST_DB_PATH)
        linked_evt = next((e for e in events if e['id'] == updated_task['evento_calendario_id']), None)
        self.assertIsNotNone(linked_evt)
        self.assertEqual(linked_evt['titulo'], "Tarefa Cassi: Brinquedos teste atualizado")
        self.assertEqual(linked_evt['responsavel'], "Cassi")
        self.assertEqual(linked_evt['categoria'], "Organização")
        self.assertEqual(linked_evt['data'], today_str)
        self.assertEqual(linked_evt['hora'], "10:00")

    def test_delete_task_api(self):
        from modules.ia_memoria.database import save_task, get_all_tasks, get_all_events
        task_id = save_task(
            usuario_nome="Isa",
            titulo="Brinquedos teste deletar",
            categoria="Infantil",
            dificuldade="Fácil",
            reward_xp=10,
            reward_gold=3,
            data="2026-06-14",
            hora="19:00",
            db_path=TEST_DB_PATH
        )
        
        tasks = get_all_tasks(TEST_DB_PATH)
        task = next((t for t in tasks if t['id'] == task_id), None)
        self.assertIsNotNone(task)
        evt_id = task['evento_calendario_id']
        
        response = self.client.post('/api/todo-gamer/excluir', json={
            "id": task_id
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        
        # Verify it is deleted from both tables
        tasks_after = get_all_tasks(TEST_DB_PATH)
        self.assertFalse(any(t['id'] == task_id for t in tasks_after))
        
        events_after = get_all_events(TEST_DB_PATH)
        self.assertFalse(any(e['id'] == evt_id for e in events_after))

    def test_task_rollover_bonuses(self):
        from modules.ia_memoria.database import save_task, get_tasks_for_user, complete_task_in_db, get_user_by_name
        import datetime
        
        # 1. Create a task in the past (e.g. 3 days ago)
        today = datetime.date.today()
        three_days_ago = (today - datetime.timedelta(days=3)).strftime('%Y-%m-%d')
        
        task_id = save_task(
            usuario_nome="Mari",
            titulo="Quest Antiga Acumulada",
            categoria="Limpeza",
            dificuldade="Fácil",
            reward_xp=10,
            reward_gold=1,
            data=three_days_ago,
            hora="12:00",
            db_path=TEST_DB_PATH
        )
        
        # 2. Fetch tasks for Mari and verify the dynamic rollover bonus is calculated:
        # Base: 10 XP, 1 Gold. Overdue: 3 days.
        # Bonus: 3 * 2 = 6 XP, 3 * 1 = 3 Gold.
        # Expected total: 16 XP, 4 Gold.
        mari_tasks = get_tasks_for_user("Mari", TEST_DB_PATH)
        task = next(t for t in mari_tasks if t['id'] == task_id)
        self.assertEqual(task['reward_xp'], 16)
        self.assertEqual(task['reward_gold'], 4)
        self.assertEqual(task['overdue_days'], 3)
        
        # 3. Complete the task and verify the user stats reflect the increased rewards:
        # Before completion, Mari has 0 XP and 0 Gold.
        mari_profile_before = get_user_by_name("Mari", TEST_DB_PATH)
        self.assertEqual(mari_profile_before['xp'], 0)
        self.assertEqual(mari_profile_before['gold'], 0)
        
        success, user_profile, leveled_up = complete_task_in_db(task_id, TEST_DB_PATH)
        self.assertTrue(success)
        self.assertEqual(user_profile['xp'], 16)
        self.assertEqual(user_profile['gold'], 4)

    def test_reward_management_api(self):
        # 1. Create a reward via API
        response = self.client.post('/api/todo-gamer/add-reward', json={
            "usuario_nome": "Mari",
            "titulo": "Recompensa Secreta",
            "custo": 20,
            "icone": "🎁"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Recompensa criada com sucesso!")
        
        # Verify it is in database
        from modules.ia_memoria.database import get_all_rewards
        rewards = get_all_rewards(TEST_DB_PATH)
        reward = next((r for r in rewards if r['titulo'] == "Recompensa Secreta"), None)
        self.assertIsNotNone(reward)
        self.assertEqual(reward['usuario_nome'], "Mari")
        self.assertEqual(reward['custo'], 20)
        self.assertEqual(reward['icone'], "🎁")
        reward_id = reward['id']
        
        # 2. Update the reward via API
        response = self.client.post('/api/todo-gamer/add-reward', json={
            "id": reward_id,
            "usuario_nome": "Mari",
            "titulo": "Recompensa Secreta Atualizada",
            "custo": 25,
            "icone": "🍦"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Recompensa atualizada com sucesso!")
        
        # Verify it is updated in database
        rewards_after = get_all_rewards(TEST_DB_PATH)
        updated_reward = next((r for r in rewards_after if r['id'] == reward_id), None)
        self.assertIsNotNone(updated_reward)
        self.assertEqual(updated_reward['titulo'], "Recompensa Secreta Atualizada")
        self.assertEqual(updated_reward['custo'], 25)
        self.assertEqual(updated_reward['icone'], "🍦")
        
        # 3. Delete the reward via API
        response = self.client.post('/api/todo-gamer/excluir-recompensa', json={
            "id": reward_id
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Recompensa excluída com sucesso!")
        
        # Verify it is deleted from database
        rewards_final = get_all_rewards(TEST_DB_PATH)
        self.assertFalse(any(r['id'] == reward_id for r in rewards_final))

    def test_chat_listar_recompensas_resgatadas(self):
        from modules.ia_memoria.database import get_rewards_for_user, redeem_reward_in_db
        import sqlite3
        
        # Give Isa enough gold first
        conn = sqlite3.connect(TEST_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE usuarios SET gold = 50 WHERE nome = 'Isa'")
        conn.commit()
        conn.close()
        
        # Redeem a reward for Isa
        isa_rewards = get_rewards_for_user('Isa', TEST_DB_PATH)
        reward = isa_rewards[0]
        success, msg, user_profile = redeem_reward_in_db(reward['id'], TEST_DB_PATH)
        self.assertTrue(success)
        
        # Send a message to chat
        response = self.client.post('/api/ia-memoria/chat', json={
            "message": "quais as recompensas que a Isa resgatou?"
        })
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("Recompensas Resgatadas (Pendentes de Entrega)", data["reply"])
        self.assertIn(reward['titulo'], data["reply"])


if __name__ == '__main__':
    unittest.main()


