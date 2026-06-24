import unicodedata
import math
import urllib.request
import json
import time
import datetime

# Basic Portuguese stop words to ignore during tokenization/vectorization
PORTUGUESE_STOPWORDS = {
    'de', 'a', 'o', 'que', 'e', 'do', 'da', 'em', 'um', 'para', 'e', 'com', 'nao', 'uma', 'os', 
    'no', 'se', 'na', 'por', 'mais', 'as', 'dos', 'como', 'mas', 'foi', 'ao', 'ele', 'das', 
    'em', 'para', 'seu', 'sua', 'ou', 'ser', 'quando', 'muito', 'ha', 'nos', 'ja', 'esta', 
    'eu', 'tambem', 'so', 'pelo', 'pela', 'ate', 'isso', 'ela', 'entre', 'depois', 'sem', 
    'mesmo', 'aos', 'seus', 'quem', 'nas', 'me', 'esse', 'eles', 'voce', 'essa', 'num', 
    'nem', 'suas', 'meu', 'minha', 'numa', 'pelos', 'pelas', 'qual', 'quais', 'onde', 'estao',
    'esta', 'sao', 'como', 'onde', 'quem', 'por'
}

def remove_accents(text):
    """Removes accents from string."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def tokenize(text):
    """Normalizes text, removes punctuation, converts to lowercase, splits into tokens, and filters stopwords."""
    text = remove_accents(text.lower())
    # Normalize wi-fi to wifi
    text = text.replace('wi-fi', 'wifi')
    # Replace non-alphanumeric characters with spaces without regex
    cleaned_chars = [c if c.isalnum() or c.isspace() else ' ' for c in text]
    text = "".join(cleaned_chars)
    tokens = text.split()
    # Remove stopwords and short words
    return [t for t in tokens if t not in PORTUGUESE_STOPWORDS and len(t) > 1]

def classify_category(text):
    """Categorizes a memory automatically based on keyword matching."""
    text_lower = text.lower()
    if any(word in text_lower for word in ['lista', 'compra', 'mercado', 'supermercado', 'feira', 'comprar', 'compras']):
        return 'Mercado'
    if any(word in text_lower for word in ['senha', 'wifi', 'wi-fi', 'acesso', 'login', 'password', 'roteador']):
        return 'Senhas'
    if any(word in text_lower for word in ['chave', 'cadeado', 'alarme', 'seguranca', 'tranca', 'portao', 'trancado']):
        return 'Segurança'
    if any(word in text_lower for word in ['telefone', 'celular', 'contato', 'numero', 'eletricista', 'encanador', 'pedreiro', 'mecanico', 'seu', 'dona']):
        return 'Contatos'
    if any(word in text_lower for word in ['ferramenta', 'martelo', 'chave de fenda', 'furadeira', 'alicate', 'parafuso', 'prego', 'furar']):
        return 'Ferramentas'
    if any(word in text_lower for word in ['caixa', 'guardado', 'gaveta', 'armario', 'sotao', 'maleiro', 'organizar', 'limpeza', 'escondido', 'natal', 'decoracao']):
        return 'Organização'
    if any(word in text_lower for word in ['pipoca', 'cachorro', 'gato', 'pet', 'vacina', 'racao', 'veterinario', 'remedio']):
        return 'Pets'
    if any(word in text_lower for word in ['receita', 'receitas', 'ingredientes', 'passo a passo', 'preparo', 'cozinhar']):
        return 'Receitas'
    return 'Geral'



# ==========================================================================
# TF-IDF & Cosine Similarity search engine
# ==========================================================================
def calculate_cosine_similarity(vec1, vec2):
    """Calculates cosine similarity between two frequency vectors (dicts)."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    if not intersection:
        return 0.0
        
    numerator = sum([vec1[x] * vec2[x] for x in intersection])
    
    sum1 = sum([vec1[x]**2 for x in vec1.keys()])
    sum2 = sum([vec2[x]**2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)
    
    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator

def search_best_memory(query, memories):
    """
    Finds the most relevant memory from the database based on a query using TF-IDF.
    Returns (best_memory, score) or (None, 0.0).
    """
    query_tokens = tokenize(query)
    if not query_tokens:
        return None, 0.0
        
    # Calculate term frequency for query
    query_vec = {}
    for t in query_tokens:
        query_vec[t] = query_vec.get(t, 0) + 1
        
    best_score = 0.0
    best_match = None
    
    # Pre-tokenize all memories and compute TF
    corpus_tokens_list = []
    memory_vecs = []
    
    for mem in memories:
        combined_text = f"{mem['categoria']} {mem['chave']} {mem['conteudo']}"
        tokens = tokenize(combined_text)
        
        # Calculate term frequency for memory
        mem_vec = {}
        for t in tokens:
            mem_vec[t] = mem_vec.get(t, 0) + 1
            
        memory_vecs.append((mem, mem_vec))
        corpus_tokens_list.append(tokens)
        
    # Standard TF-IDF calculation
    all_documents_count = len(memories)
    df = {}
    for tokens in corpus_tokens_list:
        unique_tokens = set(tokens)
        for t in unique_tokens:
            df[t] = df.get(t, 0) + 1
            
    weighted_query_vec = {}
    for term, tf in query_vec.items():
        document_freq = df.get(term, 0)
        if document_freq > 0:
            idf = math.log(all_documents_count / document_freq) + 1.0
        else:
            idf = 1.0
        weighted_query_vec[term] = tf * idf
        
    for mem, mem_vec in memory_vecs:
        weighted_mem_vec = {}
        for term, tf in mem_vec.items():
            document_freq = df.get(term, 1)
            idf = math.log(all_documents_count / document_freq) + 1.0
            weighted_mem_vec[term] = tf * idf
            
        score = calculate_cosine_similarity(weighted_query_vec, weighted_mem_vec)
        
        # Boost score slightly if direct keyword matches the "chave" field
        chave_tokens = tokenize(mem['chave'])
        match_count = sum([1 for t in query_tokens if t in chave_tokens])
        if match_count > 0:
            score += 0.15 * match_count
            
        if score > best_score:
            best_score = score
            best_match = mem
            
    return best_match, best_score

def format_list_to_bullets(text):
    """
    Formats comma or 'e' separated list items after a colon into a neat bulleted list.
    Example: "A lista de compras é: arroz, feijão e batata"
    becomes:
    "A lista de compras é:<br>• Arroz<br>• Feijão<br>• Batata"
    """
    if ':' not in text:
        return text
        
    parts = text.split(':', 1)
    prefix = parts[0].strip()
    list_content = parts[1].strip()
    
    # Split list_content by commas, semicolons, or the word ' e ' (surrounded by spaces)
    # First, normalize ' e ' and semicolons to a comma
    normalized = list_content.replace(' e ', ', ').replace('; ', ', ').replace(';', ', ')
    items = [item.strip() for item in normalized.split(',')]
    
    # Filter out empty items
    items = [item for item in items if item]
    
    # If we have at least 2 items, format them as bullets
    if len(items) >= 2:
        bullet_items = []
        for item in items:
            # Clean ending periods or spaces
            cleaned_item = item.strip()
            if cleaned_item.endswith('.'):
                cleaned_item = cleaned_item[:-1].strip()
            if cleaned_item:
                # Capitalize first letter of each item
                capitalized = cleaned_item[0].upper() + cleaned_item[1:]
                bullet_items.append(f"• {capitalized}")
                
        return f"{prefix}:<br>" + "<br>".join(bullet_items)
        
    return text

def clean_item_name(item):
    item = item.strip()
    if not item:
        return ""
    
    # Common prefixes to remove
    prefixes = [
        "para a lista de compras ", "para a lista de mercado ", "para a lista de comprar ",
        "da lista de compras ", "da lista de mercado ", "da lista de comprar ",
        "na lista de compras ", "na lista de mercado ", "na lista de comprar ",
        "lista de compras ", "lista de mercado ", "lista de comprar ",
        "para a lista ", "da lista ", "na lista ", "de lista ",
        "do mercado ", "de mercado ", "de compras ",
        "de ", "do ", "da ", "para ", "pra ", "na ", "no ", "comprar ",
        "o ", "a ", "os ", "as ", "um ", "uma ", "uns ", "umas "
    ]
    
    prev = None
    while prev != item:
        prev = item
        item_lower = item.lower()
        for prefix in prefixes:
            if item_lower.startswith(prefix):
                item = item[len(prefix):].strip()
                break
                
    if item:
        item = item[0].upper() + item[1:]
    return item

OLLAMA_HOST = "http://127.0.0.1:11434"
_cached_model = None
_last_check_time = 0
_ollama_online = True

def check_ollama_status(force=False):
    """Checks if Ollama is online, caching the status for 5 seconds to avoid timeout delays."""
    global _ollama_online, _last_check_time, _cached_model
    current_time = time.time()
    
    if not force and (current_time - _last_check_time < 5.0):
        return _ollama_online
        
    _last_check_time = current_time
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3.0) as response:
            data = json.loads(response.read().decode('utf-8'))
            models = data.get("models", [])
            names = [m["name"] for m in models]
            if "dashfamilia-ia:latest" in names or "dashfamilia-ia" in names:
                _cached_model = "dashfamilia-ia"
            elif models:
                _cached_model = models[0]["name"]
            else:
                _cached_model = "qwen2:1.5b"
            _ollama_online = True
            return True
    except Exception:
        _ollama_online = False
        _cached_model = None
        return False

def ensure_ollama_running():
    """Attempts to start Ollama if it is offline."""
    import subprocess
    import os
    if check_ollama_status(force=True):
        return True
        
    print("Ollama is offline. Attempting to auto-start local Ollama service...")
    try:
        creationflags = 0
        if os.name == 'nt':
            creationflags = 0x08000000  # CREATE_NO_WINDOW
            
        subprocess.Popen(
            ["ollama", "serve"], 
            creationflags=creationflags, 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        # Wait up to 5 seconds for it to start
        for _ in range(5):
            time.sleep(1.0)
            if check_ollama_status(force=True):
                print("Ollama started successfully via auto-start.")
                return True
    except Exception as e:
        print(f"Failed to auto-start Ollama: {e}")
    return False

def get_available_ollama_model():
    """Queries Ollama for available models or returns cached model. Returns None if offline."""
    global _cached_model
    if _cached_model:
        return _cached_model
    if check_ollama_status():
        return _cached_model
    return None

def parse_intent_with_ollama(message):
    """
    Calls local Ollama to parse user intent into structured JSON.
    Returns (True, parsed_json) if successful, otherwise (False, None).
    """
    model = get_available_ollama_model()
    if not model:
        # Try to auto-start Ollama
        ensure_ollama_running()
        model = get_available_ollama_model()
        if not model:
            # Fail fast if Ollama is still offline
            return False, None
    
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    system_prompt = (
        f"Você é o NLU do sistema DashFamília. Responda ESTRITAMENTE com um objeto JSON válido.\n"
        f"Não escreva nada além do JSON (sem markdown, sem explicações).\n"
        f"Hoje é {today_str}. Utilize este dia/ano para resolver datas relativas ou parciais (ex: 'dia 24/06' ou 'amanhã').\n\n"
        "Formatos de resposta por intenção:\n"
        "1. Para salvar informações:\n"
        "{\"intencao\": \"salvar\", \"detalhes\": {\"salvar_conteudo\": \"A senha do portão é 1234\"}}\n"
        "2. Para buscar informações:\n"
        "{\"intencao\": \"buscar\", \"detalhes\": {\"buscar_query\": \"senha do portão\"}}\n"
        "3. Para adicionar itens à lista:\n"
        "{\"intencao\": \"adicionar_lista\", \"detalhes\": {\"adicionar_itens\": [\"Arroz\", \"Feijão\"]}}\n"
        "4. Para remover itens da lista:\n"
        "{\"intencao\": \"remover_lista\", \"detalhes\": {\"remover_itens\": [\"Arroz\", \"Feijão\"]}}\n"
        "5. Para limpar ou marcar lista como comprada:\n"
        "{\"intencao\": \"limpar_lista\", \"detalhes\": {\"manter_itens\": []}} ou {\"intencao\": \"limpar_lista\", \"detalhes\": {\"manter_itens\": [\"Banana\"]}} se disser 'exceto banana'.\n"
        "6. Para comandos compostos (adicionar e remover na mesma frase):\n"
        "{\"intencao\": \"composto_lista\", \"detalhes\": {\"adicionar_itens\": [\"Chá\"], \"remover_itens\": [\"Arroz\", \"Feijão\"]}}\n"
        "7. Para conversas gerais ou saudações:\n"
        "{\"intencao\": \"conversa\", \"detalhes\": {}}\n"
        "8. Para agendar um ou mais compromissos no calendário (suporta múltiplos eventos e períodos de vários dias):\n"
        "{\"intencao\": \"agendar_calendario\", \"detalhes\": {\"compromissos\": [{\"titulo\": \"<nome do evento>\", \"data\": \"<YYYY-MM-DD>\", \"data_fim\": \"<YYYY-MM-DD ou null (data de término se for período/vários dias)>\", \"hora\": \"<HH:MM>\", \"hora_fim\": \"<HH:MM ou null>\", \"localizacao\": \"<local do evento ou null>\", \"recorrencia\": \"<recorrencia RRULE ou null>\"}]}}\n"
        "9. Para desmarcar ou remover compromissos do calendário:\n"
        "{\"intencao\": \"remover_calendario\", \"detalhes\": {\"titulo\": \"<nome do evento ou null>\", \"data\": \"<YYYY-MM-DD ou null>\"}}\n"
        "10. Para concluir ou completar uma tarefa do quadro de missões:\n"
        "{\"intencao\": \"completar_tarefa\", \"detalhes\": {\"usuario\": \"<nome do usuario>\", \"tarefa\": \"<nome/termo da tarefa>\"}}\n"
        "11. Para comprar ou resgatar uma recompensa da loja:\n"
        "{\"intencao\": \"resgatar_recompensa\", \"detalhes\": {\"usuario\": \"<nome do usuario>\", \"recompensa\": \"<nome/termo da recompensa>\"}}\n"
        "12. Para listar ou ver as tarefas do dia/semana:\n"
        "{\"intencao\": \"listar_tarefas\", \"detalhes\": {\"usuario\": \"<nome ou null para todos>\"}}\n"
        "13. Para salvar/cadastrar uma receita culinária:\n"
        "{\"intencao\": \"salvar_receita\", \"detalhes\": {\"nome\": \"<nome da receita>\", \"ingredientes\": \"<ingredientes>\", \"passo_a_passo\": \"<passo a passo>\"}}\n"
        "14. Para apagar/deletar uma receita culinária:\n"
        "{\"intencao\": \"deletar_receita\", \"detalhes\": {\"receita\": \"<nome da receita>\"}}\n"
        "15. Para comprar os ingredientes de uma receita:\n"
        "{\"intencao\": \"comprar_receita\", \"detalhes\": {\"receita\": \"<nome da receita>\"}}\n"
        "16. Para listar ou ver as recompensas resgatadas por um usuário que ele ainda não recebeu/recebeu:\n"
        "{\"intencao\": \"listar_recompensas_resgatadas\", \"detalhes\": {\"usuario\": \"<nome ou null para todos>\"}}\n"
    )
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.0
        }
    }
    
    try:
        url = f"{OLLAMA_HOST}/api/chat"
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data_bytes, 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=90.0) as response:
            res_data = response.read().decode('utf-8')
            res_json = json.loads(res_data)
            
            message_content = res_json.get("message", {}).get("content", "").strip()
            if message_content:
                parsed_output = json.loads(message_content)
                return True, parsed_output
    except Exception as e:
        print(f"Ollama error or timeout, falling back to local NLP rules: {e}")
        pass
        
    return False, None

