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

### 💰 Controle Financeiro Familiar
Gestão integrada de fluxo de caixa familiar.
* Lançamento de receitas e despesas com identificação do responsável.
* Divisão automática de despesas e visualização por categorias.
* Painel de metas de poupança coletivas com barra de progresso visual.

### 📅 Calendário Compartilhado
Agenda dinâmica integrada para coordenar a rotina do lar.
* Diferenciação visual entre tarefas coletivas e individuais.
* Visualização limpa com marcação por cores de quem é responsável por cada tarefa.

### 🎮 To-Do List Gamer
Transforma tarefas domésticas chatas em uma divertida jornada de RPG (Role-Playing Game).
* **Quests Ativas**: Louça, lixo ou faxina geram XP e Ouro Virtual.
* **Evolução**: Níveis de personagem e classes (ex: Guardiões do Lar).
* **Loja de Recompensas**: Moedas de ouro conquistadas podem ser trocadas por prêmios reais combinados em família (ex: escolher a pizza de sexta, tempo extra de videogame).

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

## 🧪 Rodando os Testes Unitários

O projeto possui uma suíte completa de testes para validar o comportamento do banco de dados, NLP e fluxos de feedback:
```bash
python -m unittest tests/test_ia_memoria.py
```

---

## 📄 Licença

Este projeto é proprietário. Todos os direitos reservados a Mariana Abad. O código-fonte está disponível publicamente apenas para fins de visualização de portfólio. Não é permitida a cópia, modificação, redistribuição ou uso comercial deste software sem autorização prévia por escrito.