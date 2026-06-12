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
    init_db, save_memory, get_all_memories, delete_memory, get_db_connection, update_memory
)

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_database.db')

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


if __name__ == '__main__':
    unittest.main()

