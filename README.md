# 🏡 DashFamília - Dashboard de Gestão Familiar

O **DashFamília** é um dashboard inteligente, premium e interativo, projetado para centralizar, organizar e gamificar a rotina, finanças e memórias de uma família. Ele roda **100% localmente**, garantindo privacidade absoluta dos dados domésticos (sem APIs externas, sem nuvem, sem vazamento de informações confidenciais).

---

## 🌟 Funcionalidades Principais

### 🧠 Módulo de IA - Memória da Casa (com Active Learning local!)
Uma inteligência centralizadora para guardar e consultar informações do dia a dia do lar que costumam sumir ou ficar espalhadas (chaves, senhas, contatos rápidos, locais de objetos).
* **NLU Local**: Utiliza processamento de intenções e entidades via **Ollama (Qwen2:1.5b)** sem dependências externas.
* **Busca Semântica TF-IDF**: Mecanismo rápido de fallback para consultar memórias usando similaridade de cosseno.
* **Loop de Aprendizado Ativo (Active Learning)**: Se a IA classificar mal uma intenção (ex: buscar em vez de remover), você pode clicar em **👎 Corrigir Entendimento**, selecionar a ação correta e a IA irá:
  1. Corrigir e aplicar o comando imediatamente no banco de dados.
  2. Registrar o feedback localmente.
  3. Recompilar o modelo Ollama `dashfamilia-ia` em background para aprender o comportamento correto!
* **Status Visual do Cérebro**: O cabeçalho exibe badges dinâmicos (**Online**, **Offline**, **Treinando IA... 🧠**) e bloqueia interações temporariamente durante a compilação do modelo local.
* **Gestão de Receitas e Lista de Compras Inteligente**: Cadastro, edição, busca e exclusão de receitas (divididas em ingredientes e passo a passo) diretamente por comandos de chat. Com o comando *"Quero fazer [receita], o que preciso comprar?"*, o assistente extrai os ingredientes necessários da memória e os adiciona à lista de compras de mercado (`Mercado`) automaticamente.

### 💰 Controle Financeiro Familiar
Gestão integrada de fluxo de caixa familiar.
* Lançamento de receitas e despesas com identificação do responsável.
* Divisão automática de despesas e visualização por categorias.
* Painel de metas de poupança coletivas com barra de progresso visual.

### 📅 Calendário Compartilhado
Agenda dinâmica integrada para coordenar a rotina do lar.
* Diferenciação visual entre tarefas coletivas e individuais.
* Visualização limpa com marcação por cores de quem é responsável por cada tarefa.

### 🎮 To-Do List Gamer (Gamificação com Perfis e Regras FlyLady)
Transforma as tarefas domésticas da casa em uma jornada divertida de RPG (Role-Playing Game).
* **Perfis Personalizados**: 3 jogadores cadastrados: **Mari** (Guardiã da Organização), **Cassi** (Guerreiro da Limpeza) e **Isa** (Pequena Aprendiz, 5 anos), com regras de pontuação adaptadas e progresso individual.
* **Tarefas Inteligentes (Método FlyLady)**: Chores gerados dinamicamente seguindo o método FlyLady (Bênção Semanal, Rotinas Diárias, Passos de Bebê para Isa), ajustados automaticamente às restrições dos membros (trabalho presencial do Cassi, quarta-feira fora da Mari, escola e atividades da Isa).
* **Gestão de Missões (CRUD Completo)**: Permite adicionar, editar e excluir missões (tarefas) diretamente pelo painel através do modal de criação de novas missões, preenchendo datas, horários e dificuldades de forma integrada.
* **Sistema de Rollover de Missões**: Missões passadas não completadas continuam visíveis na lista como acumuladas, recebendo o marcador `⚠️ Acumulada` e escalando as recompensas dinamicamente em **+2 XP** e **+1 Gold** por dia de atraso.
* **Níveis de Dificuldade e Recompensas**: Dificuldades predefinidas: Fácil (10 XP / 1 Gold), Médio (15 XP / 3 Gold), Difícil (25 XP / 5 Gold), e a nova dificuldade **Ultra** (40 XP / 10 Gold) para faxinas pesadas e complexas.
* **Integração com Calendário**: As quests ativas são sincronizadas automaticamente como eventos no calendário familiar (sem poluir a visão mensal com marcações redundantes), ganhando um checkmark (`✅`) no título assim que completadas.
* **Resgate de Recompensas**: Loja de itens com preços em ouro virtual, permitindo que cada usuário troque seu ouro por recompensas customizadas (ex: SPA para Mari, Videogame para Cassi, Desenhos/Tablet para Isa).
* **NLU Conversacional**: Conclusão de tarefas e resgate de recompensas podem ser feitos digitando comandos diretamente no chat (ex: *"completei a tarefa de limpar a caixa de areia"* ou *"Isa quer comprar a recompensa de historinha"*), com fallback local offline robusto.
* **Divisão Justa de Tarefas Domésticas**: Cassi e Mari dividem as tarefas semanais na metade (50/50) de forma aleatória a cada carregamento de diárias, e a pequena Isa fica responsável pelas tarefas adequadas para a idade, como *"Tirar o lixo do banheiro"* (2x por semana) e *"Verificar água dos gatos"* (2x por semana).
* **Reconhecimento de Ações Extras (Não Planejadas)**: Permite recompensar membros da família com bônus de XP e Ouro por ações nobres espontâneas (ex: ajudar a carregar as compras, limpar algo sem ninguém pedir). O registro da ação é inserido no quadro sob a categoria "Extra" e com status "⭐ Concluída" para servir como histórico.

---

## 🔒 Segurança & Privacidade (Privacidade em Primeiro Lugar!)

Para proteger as informações reais da sua casa (senhas do Wi-Fi, segredos de portões, chaves reserva, etc.):
1. **Bancos de Dados Local-Only**: Os arquivos `database.db` e `test_database.db` estão incluídos no `.gitignore` e nunca serão enviados para o seu repositório Git público.
2. **Auto-inicialização**: Caso o arquivo `database.db` não exista na inicialização, o sistema criará o banco automaticamente e o populará com dados de exemplo (mock data) inofensivos para desenvolvimento imediato.
3. **Feedbacks Locais**: O arquivo de logs de aprendizado ativo (`feedback.json`) e a compilação final do `Modelfile` contendo exemplos de treinamento também estão protegidos pelo `.gitignore`.

---

## 🛠️ Tecnologias Utilizadas

* **Backend**: Python 3.x, Flask (Leve e robusto)
* **Frontend**: HTML5 Semântico, CSS3 Vanilla (Design responsivo, moderno, estilo Glassmorphism com gradientes harmoniosos) e JavaScript Vanilla.
* **Processamento de Linguagem Natural (NLP)**: Ollama local (modelo `qwen2:1.5b` customizado) + TF-IDF e Similaridade de Cosseno.
* **Banco de Dados**: SQLite3 (embarcado e local).

---

## 🚀 Como Executar o Projeto Localmente

### 1. Requisitos Prévios
* Ter o **Python 3.8+** instalado.
* Ter o **Ollama** instalado e rodando em sua máquina ([Ollama Download](https://ollama.com/)).

### 2. Instalar e Configurar o Ollama e Modelo Base
Abra o terminal e baixe o modelo de linguagem base:
```bash
ollama pull qwen2:1.5b
```

Crie o modelo personalizado inicial do projeto utilizando o arquivo de template:
```bash
# Navegue até a pasta de treinamento
cd modules/training

# Crie o modelo customizado
ollama create dashfamilia-ia -f Modelfile.template
```

### 3. Configurar o Ambiente Python
Retorne à raiz do projeto e crie o ambiente virtual:
```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# No Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# No Linux/Mac:
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 4. Iniciar a Aplicação
Execute o arquivo inicial da aplicação:
```bash
python app.py
```
Acesse o painel no seu navegador através de: **`http://127.0.0.1:5000/`**

---

## 🏛️ Arquitetura Modular do Projeto

Para garantir manutenibilidade e escalabilidade à medida que novas features são adicionadas, o dashboard foi totalmente refatorado de uma estrutura monolítica para uma arquitetura baseada em **Flask Blueprints** divididos por domínios sob a pasta `modules/`:

- **`app.py`**: Ponto de entrada limpo da aplicação. Inicializa o banco de dados SQLite local e registra todas as rotas modulares.
- **`modules/geral/routes.py`**: Controla o carregamento do template principal (`index.html`) e o status do sistema de armazenamento (NAS).
- **`modules/todo_gamer/routes.py`**: Centraliza todas as rotas de gamificação das rotinas diárias, missões, resgate e criação de recompensas, além do cadastro de novos membros.
- **`modules/calendario/routes.py`**: Gerencia a criação e sincronização bidirecional de compromissos com o Google Calendar.
- **`modules/financas/routes.py`**: Processa as transações de receitas, despesas parceladas/recorrentes, divisão de gastos e metas de poupança.
- **`modules/ia_memoria/`**: Mantém a lógica NLP do "Cérebro da Casa" (TF-IDF local + fallback), as definições dos sub-agentes inteligentes especialistas e o `Orchestrator` de intents.

---

## 👥 Walkthrough/Tutorial: Cadastro de Membros da Família

Agora é possível cadastrar novos jogadores na família, com campos opcionais para **idade** e **telefone**. A adição de novos membros pode ser realizada de duas formas:

### 1. Via Interface Gráfica (Painel)
1. Acesse o painel e selecione a aba **To-Do List Gamer**.
2. Clique no botão **➕ Novo Jogador** (localizado ao lado das abas de seleção de membros).
3. Preencha as informações no modal:
   - **Nome ou Apelido**: Nome do jogador (ex: `Rodrigo`).
   - **Avatar (Emoji)**: Ícone representativo (ex: `🛡️`).
   - **Classe RPG**: Classe do personagem para a gamificação (ex: `Guerreiro`).
   - **Idade** *(Opcional)*: Número inteiro de anos.
   - **Telefone** *(Opcional)*: Contato rápido no formato que preferir.
4. Clique em **Cadastrar**. O novo jogador será inserido no banco de dados SQLite local e seu selector tab correspondente aparecerá dinamicamente na lista!

### 2. Via Chamada de API (cURL / Backend Client)
Você pode enviar uma requisição HTTP do tipo `POST` para o endpoint `/api/todo-gamer/usuario/cadastrar`.

**Exemplo de Requisição cURL:**
```bash
curl -X POST http://127.0.0.1:5000/api/todo-gamer/usuario/cadastrar \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Rodrigo",
    "avatar": "🛡️",
    "classe": "Guerreiro",
    "idade": 35,
    "telefone": "(11) 99999-8888"
  }'
```

**Exemplo de Resposta de Sucesso (JSON):**
```json
{
  "success": true,
  "message": "Usuário cadastrado com sucesso!",
  "profiles": [
    { "id": 1, "nome": "Mari", "avatar": "👩‍💻", "classe": "Guardiã da Organização", "nivel": 1, "xp": 0, "xp_to_next_level": 100, "gold": 0, "idade": null, "telefone": null },
    { "id": 2, "nome": "Cassi", "avatar": "👨‍💻", "classe": "Guerreiro da Limpeza", "nivel": 1, "xp": 0, "xp_to_next_level": 100, "gold": 0, "idade": null, "telefone": null },
    { "id": 3, "nome": "Isa", "avatar": "👧", "classe": "Pequena Aprendiz", "nivel": 1, "xp": 0, "xp_to_next_level": 100, "gold": 0, "idade": null, "telefone": null },
    { "id": 4, "nome": "Rodrigo", "avatar": "🛡️", "classe": "Guerreiro", "nivel": 1, "xp": 0, "xp_to_next_level": 100, "gold": 0, "idade": 35, "telefone": "(11) 99999-8888" }
  ]
}
```

---

## ⚡ Walkthrough/Tutorial: Conceder Pontos por Ação Extra

A concessão de pontos por ações não planejadas/reconhecimento pode ser realizada de duas formas:

### 1. Via Interface Gráfica (Painel)
1. Acesse o painel e selecione a aba **To-Do List Gamer**.
2. Clique no botão **⚡ Ação Extra** no cabeçalho do Quadro de Missões Ativas.
3. No modal que abrir, preencha:
   - **Membro da Família**: Quem receberá o bônus.
   - **O que ele(a) fez de bom?**: Descrição da ação (ex: `Ajudou a carregar as compras do mercado`).
   - **XP Bônus** e **Ouro Bônus**: Pontuações a conceder (padrões de 15 XP e 5 Ouro).
4. Clique em **Conceder Bônus ⚡**. A pontuação e ouro do jogador serão atualizados imediatamente (incluindo level-up automático caso o XP ultrapasse o limite) e a ação aparecerá listada no quadro de missões de hoje com o status "⭐ Concluída".

### 2. Via Chamada de API (POST)
Você pode enviar uma requisição HTTP do tipo `POST` para o endpoint `/api/todo-gamer/extra-points`.

**Exemplo de Requisição cURL:**
```bash
curl -X POST http://127.0.0.1:5000/api/todo-gamer/extra-points \
  -H "Content-Type: application/json" \
  -d '{
    "usuario_nome": "Mari",
    "descricao": "Limpou o fogão espontaneamente",
    "reward_xp": 20,
    "reward_gold": 5
  }'
```

**Exemplo de Resposta de Sucesso (JSON):**
```json
{
  "success": true,
  "message": "Pontos e Ouro extras concedidos com sucesso!",
  "leveled_up": false,
  "reward_xp": 20,
  "reward_gold": 5,
  "state": {
    "character": { ... },
    "profiles": [ ... ],
    "quests": [ ... ],
    "rewards": [ ... ]
  }
}
```

---

## 🧪 Rodando os Testes Unitários

O projeto possui uma suíte completa de testes para validar o comportamento do banco de dados, NLP e fluxos de feedback:
```bash
.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 📄 Licença

Este projeto é proprietário. Todos os direitos reservados a Mariana Abad. O código-fonte está disponível publicamente apenas para fins de visualização de portfólio. Não é permitida a cópia, modificação, redistribuição ou uso comercial deste software sem autorização prévia por escrito.