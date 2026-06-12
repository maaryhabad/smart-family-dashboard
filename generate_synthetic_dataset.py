import json
import random
import os

# Set random seed for reproducibility
random.seed(42)

# Vocabulary lists
contatos = ["eletricista", "encanador Seu Mario", "Carlos pedreiro", "mecanico Joao", "Dona Maria faxineira", "Dr. Silva medico", "clinica pet", "dentista Mariana", "escola das criancas"]
nomes = ["Ana", "Pedro", "Mariana", "Rodrigo", "Lucas", "Julia", "Carlos", "Beatriz"]
locais = ["na gaveta da entrada", "no armario da cozinha", "na segunda prateleira da garagem", "no sotao", "no maleiro do quarto de hospedes", "na caixinha de madeira do aparador", "atras da porta principal", "no cofre da suite", "em cima da mesa de jantar", "no bolso do casaco preto"]
ferramentas = ["martelo", "chave de fenda", "furadeira", "alicate de pressao", "parafuso", "trena de 5m", "serrote", "chave inglesa", "furadeira Bosch"]
objetos = ["casa", "carro", "moto", "escritorio", "portao da garagem", "cadeado do quintal", "cofre", "gaveteiro"]
portas = ["entrada", "garagem", "fundos", "cozinha", "sala de estar"]
senhas = ["FamiliaFeliz2026!", "123456", "admin123", "senha123", "Portao2026", "AcessoSeguro", "NetFamilia2.4G"]
datas = ["10/08/2026", "25/12/2026", "15/07/2026", "05/09/2026", "amanha de manha", "no proximo sabado"]
pets = ["Pipoca", "Tobias", "Bolinha", "Mel", "Rex", "Fiona"]
veterinarios = ["Dr. Paulo", "Dra. Juliana", "Clinica Veterinaria PetShow"]

itens_mercado = [
    "arroz", "feijao", "macarrao", "leite", "manteiga", "pao", "queijo", "presunto", "ovos", "cafe", 
    "acucar", "sal", "oleo", "detergente", "sabao em po", "amaciante", "papel higienico", "pasta de dente", 
    "sabonete", "shampoo", "banana", "maca", "laranja", "batata", "cebola", "tomate", "cenoura", "carne", 
    "frango", "peixe", "refrigerante", "suco", "cerveja", "agua", "bolacha", "chocolate", "racao do gato", 
    "racao do cachorro", "areia dos gatos", "iogurte", "limao", "azeite", "farinha"
]

categorias_financas = ["Alimentacao", "Habitacao", "Saude", "Transporte", "Lazer", "Outros"]
descricoes_despesas = ["Carrefour", "Enel", "Netflix", "Gasolina Shell", "Padaria", "Farmacia", "Restaurante", "Uber", "Petshop"]

missoes_nomes = [
    "Lavar e guardar a louca do jantar",
    "Levar o lixo e reciclaveis para fora",
    "Organizar os brinquedos/sala de estar",
    "Limpar a caixa de areia do gato",
    "Faxina profunda no quarto"
]

salvar_verbos = ["salva", "salvar", "anote", "anota", "anotar", "lembre", "lembra", "lembrar", "guarde", "guarda", "guardar", "cadastre", "cadastra", "cadastrar", "registre", "registra", "registrar", "grave", "grava", "gravar"]
salvar_pronomes = ["", "pra mim ", "para nos ", "ai "]
salvar_conectores = ["que ", ": ", " "]
buscar_perguntas = ["qual e", "onde esta", "onde fica", "cadê", "onde guardamos", "como acho", "voce lembra", "onde esta guardado", "onde deixei", "qual o numero do", "onde colocamos"]

lista_adicionar_verbos = ["adicione", "adiciona", "adicionar", "coloque", "coloca", "colocar", "bota", "botar", "acrescente", "acrescentar", "inclua", "inclui", "incluir", "poe", "por"]
lista_remover_verbos = ["tire", "tira", "tirar", "remova", "remover", "exclua", "exclui", "excluir", "apague", "apagar", "delete", "deletar"]
lista_locativos = ["na lista", "na lista de compras", "na lista de mercado", "a lista", "para a lista", "no mercado"]
lista_limpar_triggers = ["comprei tudo", "limpar a lista", "limpa a lista", "apagar a lista", "esvaziar a lista", "lista comprada", "comprei os itens", "ja comprei a lista"]

# Helper to format item
def format_item(item):
    return item.strip().capitalize()

# --- MODULE 1: AI MEMORY (1000 SAMPLES) ---
def get_module_memory():
    samples = []
    
    # 1. salvar (~400 samples)
    templates_salvar = [
        ("Senhas", lambda: f"a senha do wifi é {random.choice(senhas)}", lambda s: f"A senha do wifi é {s}"),
        ("Senhas", lambda: f"a senha do portão é {random.choice(senhas)}", lambda s: f"A senha do portão é {s}"),
        ("Segurança", lambda: f"a chave reserva do {random.choice(objetos)} está {random.choice(locais)}", lambda s: f"A chave reserva do {s}"),
        ("Segurança", lambda: f"a chave da porta da {random.choice(portas)} fica {random.choice(locais)}", lambda s: f"A chave da porta da {s}"),
        ("Contatos", lambda: f"o telefone do {random.choice(contatos)} é {random.randint(980000000, 999999999)}", lambda s: f"O telefone do {s}"),
        ("Ferramentas", lambda: f"o {random.choice(ferramentas)} está {random.choice(locais)}", lambda s: f"O {s}"),
        ("Organização", lambda: f"as caixas de {random.choice(['Natal', 'ferias', 'documentos', 'ferramentas'])} estão {random.choice(locais)}", lambda s: f"As caixas de {s}"),
        ("Pets", lambda: f"a vacina do {random.choice(pets)} é {random.choice(datas)}", lambda s: f"A vacina do {s}"),
        ("Pets", lambda: f"a comida do {random.choice(pets)} fica {random.choice(locais)}", lambda s: f"A comida do {s}")
    ]
    for _ in range(400):
        _, content_gen, _ = random.choice(templates_salvar)
        content = content_gen()
        v = random.choice(salvar_verbos)
        p = random.choice(salvar_pronomes)
        c = random.choice(salvar_conectores)
        prompt = f"{v.capitalize()} {p}{c}{content}".replace("  ", " ").replace(" : ", ": ").strip()
        expected = content[0].upper() + content[1:]
        samples.append({
            "mensagem": prompt,
            "intencao": "salvar",
            "detalhes": {"salvar_conteudo": expected}
        })
        
    # 2. buscar (~400 samples)
    targets = [
        "senha do wifi", "senha do portao", "chave reserva do carro", "chave da entrada",
        "telefone do encanador", "whatsapp do eletricista", "contato do mecanico",
        "martelo", "furadeira", "chave de fenda", "caixa de natal", "decoracao de natal",
        "vacina do pipoca", "veterinario do tobias", "comida do cachorro"
    ]
    for _ in range(400):
        prefix = random.choice(buscar_perguntas)
        target = random.choice(targets)
        prompt = f"{prefix.capitalize()} {target}?".replace("??", "?").replace("  ", " ")
        samples.append({
            "mensagem": prompt,
            "intencao": "buscar",
            "detalhes": {"buscar_query": target}
        })
        
    # 3. conversa (~200 samples)
    saudacoes = ["ola", "oi", "bom dia", "boa tarde", "boa noite", "tudo bem?", "como voce esta?", "ola assistente"]
    perguntas_conversa = ["quem e voce?", "o que voce faz?", "como pode me ajudar?", "qual seu nome?", "ajuda da familia"]
    for _ in range(200):
        prompt = random.choice(saudacoes + perguntas_conversa).capitalize()
        samples.append({
            "mensagem": prompt,
            "intencao": "conversa",
            "detalhes": {}
        })
        
    random.shuffle(samples)
    return samples[:1000]

# --- MODULE 2: SHOPPING LIST (1000 SAMPLES) ---
def get_module_shopping_list():
    samples = []
    
    # 1. adicionar_lista (~350 samples)
    for _ in range(350):
        num_items = random.randint(1, 4)
        items = random.sample(itens_mercado, num_items)
        items_str = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " e " + items[-1]
        verb = random.choice(lista_adicionar_verbos).capitalize()
        loc = random.choice(lista_locativos)
        prompt = f"{verb} {items_str} {loc}" if random.random() > 0.5 else f"{verb} {loc}: {items_str}"
        samples.append({
            "mensagem": prompt,
            "intencao": "adicionar_lista",
            "detalhes": {"adicionar_itens": [format_item(i) for i in items]}
        })
        
    # 2. remover_lista (~350 samples)
    for _ in range(350):
        num_items = random.randint(1, 3)
        items = random.sample(itens_mercado, num_items)
        items_str = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " e " + items[-1]
        verb = random.choice(lista_remover_verbos).capitalize()
        loc = random.choice(lista_locativos)
        prompt = f"{verb} {items_str} {loc}" if random.random() > 0.5 else f"{verb} {loc}: {items_str}"
        samples.append({
            "mensagem": prompt,
            "intencao": "remover_lista",
            "detalhes": {"remover_itens": [format_item(i) for i in items]}
        })
        
    # 3. limpar_lista (~150 samples)
    for _ in range(150):
        trigger = random.choice(lista_limpar_triggers).capitalize()
        if random.random() > 0.6:
            num_keep = random.randint(1, 2)
            keep = random.sample(itens_mercado, num_keep)
            keep_str = " e ".join(keep)
            conector = random.choice([" exceto ", " menos ", " mas guarde ", " mas mantenha "])
            prompt = f"{trigger}{conector}{keep_str}"
            keep_items_parsed = [format_item(k) for k in keep]
        else:
            prompt = trigger
            keep_items_parsed = []
        samples.append({
            "mensagem": prompt,
            "intencao": "limpar_lista",
            "detalhes": {"manter_itens": keep_items_parsed}
        })
        
    # 4. composto_lista (~150 samples)
    for _ in range(150):
        num_add = random.randint(1, 2)
        num_rem = random.randint(1, 2)
        add_items = random.sample(itens_mercado, num_add)
        rem_items = random.sample([i for i in itens_mercado if i not in add_items], num_rem)
        add_str = " e ".join(add_items)
        rem_str = " e ".join(rem_items)
        verb_add = random.choice(lista_adicionar_verbos)
        verb_rem = random.choice(lista_remover_verbos)
        prompt = f"{verb_rem.capitalize()} {rem_str} da lista e {verb_add} {add_str}" if random.random() > 0.5 else f"{verb_add.capitalize()} {add_str} na lista e {verb_rem} {rem_str}"
        samples.append({
            "mensagem": prompt,
            "intencao": "composto_lista",
            "detalhes": {
                "adicionar_itens": [format_item(i) for i in add_items],
                "remover_itens": [format_item(i) for i in rem_items]
            }
        })
        
    random.shuffle(samples)
    return samples[:1000]

# --- MODULE 3: FINANCIAL DATA (1000 SAMPLES) ---
def get_module_finances():
    samples = []
    
    # 1. consultar_financas (~500 samples)
    templates = [
        "quanto a gente gastou com {categoria}?",
        "mostre as despesas de {categoria}",
        "qual foi o gasto de {categoria}?",
        "como estao nossas financas para {categoria}?",
        "quanto sobrou de saldo?",
        "qual a taxa de poupanca da familia?",
        "quanto economizamos esse mes?",
        "qual a receita total?",
        "mostre a meta de {meta}",
        "como esta o progresso de poupanca da {meta}?",
        "quanto falta para a {meta}?",
        "mostre as ultimas transacoes"
    ]
    metas = ["Viagem de Fim de Ano", "Reforma do Escritório", "comprar o carro novo"]
    for _ in range(500):
        t = random.choice(templates)
        cat = random.choice(categorias_financas)
        meta = random.choice(metas)
        prompt = t.format(categoria=cat, meta=meta).capitalize()
        samples.append({
            "mensagem": prompt,
            "intencao": "consultar_financas",
            "detalhes": {
                "categoria_solicitada": cat if "{categoria}" in t else None,
                "meta_solicitada": meta if "{meta}" in t else None
            }
        })
        
    # 2. adicionar_transacao (~500 samples)
    adicionar_verbos = ["anota", "cadastra", "salva", "adiciona", "coloque", "registre", "lança", "lançar"]
    for _ in range(500):
        verb = random.choice(adicionar_verbos).capitalize()
        desc = random.choice(descricoes_despesas)
        val = random.randint(10, 1500)
        if random.random() > 0.2:
            prompt = f"{verb} despesa de {val} reais no {desc}"
            valor_final = -float(val)
        else:
            prompt = f"{verb} receita de {val} reais"
            valor_final = float(val)
            desc = "Receita"
        samples.append({
            "mensagem": prompt,
            "intencao": "adicionar_transacao",
            "detalhes": {
                "descricao": desc,
                "valor": valor_final
            }
        })
        
    random.shuffle(samples)
    return samples[:1000]

# --- MODULE 4: CALENDAR (1000 SAMPLES) ---
def get_module_calendar():
    samples = []
    
    # 1. consultar_calendario (~500 samples)
    templates = [
        "quais os compromissos de {data}?",
        "o que temos marcado para {data}?",
        "quais sao os eventos do dia {data}?",
        "mostre a agenda de {data}",
        "quando e o {evento}?",
        "que dia temos {evento}?",
        "qual o horario de {evento}?"
    ]
    eventos = ["almoco de domingo na vo", "dentista Mariana", "reuniao de condominio", "vacina do Pipoca", "aniversario do Lucas"]
    for _ in range(500):
        t = random.choice(templates)
        dt = random.choice(datas)
        evt = random.choice(eventos)
        prompt = t.format(data=dt, evento=evt).capitalize()
        samples.append({
            "mensagem": prompt,
            "intencao": "consultar_calendario",
            "detalhes": {
                "data_solicitada": dt if "{data}" in t else None,
                "evento_solicitado": evt if "{evento}" in t else None
            }
        })
        
    # 2. adicionar_evento (~500 samples)
    adicionar_evento_verbos = ["agenda", "agendar", "marca", "marcar", "coloca no calendario", "adiciona evento", "cria compromisso"]
    for _ in range(500):
        verb = random.choice(adicionar_evento_verbos).capitalize()
        evt = random.choice(["Jantar familiar", "Dentista Lucas", "Veterinario Pipoca", "Reuniao condominio", "Aniversario da Vo", "Futebol quarta"])
        dt = random.choice(datas)
        hora = f"{random.randint(8, 20):02d}:{random.choice([0, 30]):02d}"
        prompt = f"{verb}: {evt} no dia {dt} as {hora}h"
        samples.append({
            "mensagem": prompt,
            "intencao": "adicionar_evento",
            "detalhes": {
                "titulo": evt,
                "data": dt,
                "hora": hora
            }
        })
        
    random.shuffle(samples)
    return samples[:1000]

# --- MODULE 5: QUESTS (TODO-GAMER) & NAS STATUS (1000 SAMPLES) ---
def get_module_quests_nas():
    samples = []
    
    # 1. consultar_missoes (~400 samples)
    templates_missoes = [
        "quais sao as minhas missoes?",
        "quais as tarefas de hoje?",
        "mostre as missoes gamer",
        "tenho alguma missao pendente?",
        "quais tarefas dao mais XP?",
        "quanto ouro eu tenho?",
        "qual o meu level e XP atual?",
        "mostre os status do meu personagem"
    ]
    for _ in range(400):
        prompt = random.choice(templates_missoes).capitalize()
        samples.append({
            "mensagem": prompt,
            "intencao": "consultar_missoes",
            "detalhes": {}
        })
        
    # 2. concluir_missao (~350 samples)
    concluir_verbos = ["conclui", "concluir", "terminei", "finalizei", "completei", "marca como feita", "marca concluida"]
    for _ in range(350):
        verb = random.choice(concluir_verbos).capitalize()
        missao = random.choice(missoes_nomes)
        prompt = f"{verb} a missao {missao}"
        samples.append({
            "mensagem": prompt,
            "intencao": "concluir_missao",
            "detalhes": {
                "titulo_missao": missao
            }
        })
        
    # 3. consultar_nas (~250 samples)
    templates_nas = [
        "como esta o status do NAS?",
        "o servidor NVMe esta online?",
        "quanto espaco livre tem no disco?",
        "qual a temperatura do SSD?",
        "mostre a saude do servidor local",
        "qual o modelo do SSD do NAS?",
        "espaco livre no HD"
    ]
    for _ in range(250):
        prompt = random.choice(templates_nas).capitalize()
        samples.append({
            "mensagem": prompt,
            "intencao": "consultar_nas",
            "detalhes": {}
        })
        
    random.shuffle(samples)
    return samples[:1000]

# Combine all modules
dataset = []
dataset.extend(get_module_memory())
dataset.extend(get_module_shopping_list())
dataset.extend(get_module_finances())
dataset.extend(get_module_calendar())
dataset.extend(get_module_quests_nas())

# Shuffle and cap at exactly 5000
random.shuffle(dataset)
dataset = dataset[:5000]

# Save to dataset.json in the current working directory (root)
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"Dataset de 5000 amostras gerado com sucesso em: {output_path}")
print(f"Total: {len(dataset)} amostras.")
