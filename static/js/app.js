// ==========================================================================
// GLOBALS & STATE
// ==========================================================================
let gamerState = null;
let calendarEvents = [];
let lastUserMessage = "";
let activeGamerMember = "Mari";


// ==========================================================================
// INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
    // Start Clock and Date
    initClock();
    
    // Tab switching setup
    initTabs();
    
    // Load initial API Data
    fetchNasStatus();
    fetchFinanceData();
    fetchCalendarData();
    fetchGamerData();
    fetchVaultMemories();
    
    // Add Event Listeners
    setupChatListeners();
    setupGamerListeners();
    setupVaultListeners();
    setupFeedbackListeners();
    setupCalendarListeners();
    setupVoiceRecognition('btn-chat-mic', 'chat-input');
    setupVoiceRecognition('btn-modal-mic', 'edit-mem-content');
    
    // Start Ollama status check and polling
    checkOllamaStatus();
    setInterval(checkOllamaStatus, 3000);
});

// ==========================================================================
// TOAST NOTIFICATIONS
// ==========================================================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'warning') icon = '⚠️';
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    
    // Remove toast after animation ends
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px) scale(0.9)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ==========================================================================
// CLOCK & DATE
// ==========================================================================
function initClock() {
    const clockEl = document.getElementById('live-clock');
    const dateEl = document.getElementById('live-date');
    
    function updateClock() {
        const now = new Date();
        
        // Time
        const hrs = String(now.getHours()).padStart(2, '0');
        const mins = String(now.getMinutes()).padStart(2, '0');
        const secs = String(now.getSeconds()).padStart(2, '0');
        clockEl.textContent = `${hrs}:${mins}:${secs}`;
        
        // Date formatting in Portuguese
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateEl.textContent = now.toLocaleDateString('pt-BR', options);
    }
    
    updateClock();
    setInterval(updateClock, 1000);
}

// ==========================================================================
// SPA TAB NAVIGATION
// ==========================================================================
const TAB_DETAILS = {
    'ia-memoria': { title: '🤖 Memória da Casa', subtitle: 'Consulte o cérebro da inteligência do lar' },
    'financas': { title: '💰 Controle Financeiro', subtitle: 'Acompanhamento de gastos e metas da família' },
    'calendario': { title: '📅 Calendário Dinâmico', subtitle: 'Compromissos e escalas compartilhadas' },
    'todo-gamer': { title: '🎮 Quadro de Missões Gamer', subtitle: 'Cumpra tarefas domésticas, ganhe XP e suba de nível!' }
};

function initTabs() {
    const navButtons = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');
    const titleEl = document.getElementById('current-tab-title');
    const subtitleEl = document.getElementById('current-tab-subtitle');
    
    navButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            // Toggle sidebar buttons
            navButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Toggle tab content panes
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `tab-${targetTab}`) {
                    // Slight delay to allow transition after style update
                    setTimeout(() => {
                        content.classList.add('active');
                    }, 50);
                }
            });
            
            // Update Header Text
            if (TAB_DETAILS[targetTab]) {
                titleEl.textContent = TAB_DETAILS[targetTab].title;
                subtitleEl.textContent = TAB_DETAILS[targetTab].subtitle;
            }
        });
    });
}

// ==========================================================================
// API FETCHERS
// ==========================================================================

// 1. NAS STATUS
async function fetchNasStatus() {
    try {
        const res = await fetch('/api/nas-status');
        const data = await res.json();
        
        document.getElementById('nas-status').textContent = data.status;
        document.getElementById('nas-conn').textContent = data.connection_type;
        document.getElementById('nas-drive').textContent = `${data.device_model} (${data.drive_letter})`;
        
        const usedGb = data.disk_total_gb - data.disk_free_gb;
        document.getElementById('nas-percentage').textContent = `${data.disk_percentage}%`;
        document.getElementById('nas-storage-bar').style.width = `${data.disk_percentage}%`;
        document.getElementById('nas-used').textContent = `${data.disk_free_gb} GB`;
        document.getElementById('nas-total').textContent = `${data.disk_total_gb} GB`;
    } catch (err) {
        console.error("Erro ao carregar status do NAS:", err);
        document.getElementById('nas-status').textContent = "Offline";
        document.getElementById('nas-status').className = "detail-value text-red";
    }
}

// 2. FINANCES
async function fetchFinanceData() {
    try {
        const res = await fetch('/api/financas');
        const data = await res.json();
        
        // Populate Metric Cards
        document.getElementById('fin-income').textContent = formatCurrency(data.summary.income);
        document.getElementById('fin-expenses').textContent = formatCurrency(data.summary.expenses);
        document.getElementById('fin-savings').textContent = formatCurrency(data.summary.savings);
        document.getElementById('fin-rate').textContent = `${data.summary.savings_rate}%`;
        
        // Populate Transactions Table
        const txBody = document.getElementById('finance-transactions');
        txBody.innerHTML = '';
        data.recent_transactions.forEach(tx => {
            const row = document.createElement('tr');
            const amountClass = tx.amount > 0 ? 'text-green' : 'text-red';
            const prefix = tx.amount > 0 ? '+' : '';
            
            row.innerHTML = `
                <td><strong>${tx.description}</strong></td>
                <td><span class="tag-difficulty">${tx.category}</span></td>
                <td>${tx.date}</td>
                <td>${tx.user}</td>
                <td class="text-right ${amountClass}"><strong>${prefix}${formatCurrency(tx.amount)}</strong></td>
            `;
            txBody.appendChild(row);
        });
        
        // Populate Savings Goals
        const goalsContainer = document.getElementById('finance-goals');
        goalsContainer.innerHTML = '';
        data.savings_goals.forEach(goal => {
            const div = document.createElement('div');
            div.className = 'goal-item';
            div.innerHTML = `
                <div class="goal-header">
                    <span class="goal-name">${goal.title}</span>
                    <span>${goal.percentage}%</span>
                </div>
                <div class="goal-progress-bar">
                    <div class="goal-progress-fill" style="width: ${goal.percentage}%"></div>
                </div>
                <div class="goal-numbers">
                    <span>${formatCurrency(goal.current)}</span>
                    <span>Meta: ${formatCurrency(goal.target)}</span>
                </div>
            `;
            goalsContainer.appendChild(div);
        });
        
        // Populate Categories Breakdown
        const catsContainer = document.getElementById('finance-categories');
        catsContainer.innerHTML = '';
        data.categories.forEach(cat => {
            const div = document.createElement('div');
            div.className = 'cat-item';
            div.innerHTML = `
                <div class="cat-header">
                    <span class="cat-name">
                        <span class="cat-color-dot" style="background-color: ${cat.color}"></span>
                        ${cat.name}
                    </span>
                    <span>${formatCurrency(cat.value)} (${cat.percentage}%)</span>
                </div>
                <div class="cat-meter-bg">
                    <div class="cat-meter-fill" style="width: ${cat.percentage}%; background-color: ${cat.color}"></div>
                </div>
            `;
            catsContainer.appendChild(div);
        });
    } catch (err) {
        console.error("Erro ao buscar dados financeiros:", err);
    }
}

// 3. CALENDAR
async function fetchCalendarData() {
    try {
        const res = await fetch('/api/calendario');
        calendarEvents = await res.json();
        
        renderCalendarGrid(2026, 5); // June is month 5 (0-indexed in JS)
        renderEventsList();
    } catch (err) {
        console.error("Erro ao buscar eventos do calendário:", err);
    }
}

// 4. GAMER STATE
async function fetchGamerData() {
    try {
        const res = await fetch('/api/todo-gamer');
        gamerState = await res.json();
        
        updateGamerUI();
    } catch (err) {
        console.error("Erro ao carregar dados do game To-Do:", err);
    }
}

let allMemories = [];
let vaultActiveCategory = 'all';

// ==========================================================================
// VOICE RECOGNITION (WEB SPEECH API)
// ==========================================================================
function setupVoiceRecognition(btnId, targetInputId) {
    const btn = document.getElementById(btnId);
    const input = document.getElementById(targetInputId);
    if (!btn || !input) return;
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        btn.style.display = 'none';
        return;
    }
    
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'pt-BR';
    recognition.interimResults = false;
    
    let isRecording = false;
    
    recognition.onstart = () => {
        isRecording = true;
        btn.classList.add('recording');
        showToast("🎙️ Ouvindo... Fale agora.", "info");
    };
    
    recognition.onend = () => {
        isRecording = false;
        btn.classList.remove('recording');
    };
    
    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        isRecording = false;
        btn.classList.remove('recording');
        if (event.error === 'not-allowed') {
            showToast("⚠️ Permissão de microfone negada.", "warning");
        } else {
            showToast("⚠️ Ocorreu um erro no reconhecimento de voz.", "warning");
        }
    };
    
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript) {
            if (input.tagName === 'TEXTAREA' || input.tagName === 'INPUT') {
                const currentVal = input.value.trim();
                input.value = currentVal ? `${currentVal} ${transcript}` : transcript;
                input.dispatchEvent(new Event('input'));
            }
            showToast("🎙️ Voz transcrita com sucesso!", "success");
        }
    };
    
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (isRecording) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });
}

// ==========================================================================
// MODULE 1.5: MEMORY VAULT MANAGER
// ==========================================================================
async function fetchVaultMemories() {
    const listContainer = document.getElementById('memories-list-vault');
    if (!listContainer) return;
    
    try {
        const res = await fetch('/api/ia-memoria/memorias');
        allMemories = await res.json();
        renderVaultMemories();
    } catch (err) {
        console.error("Error loading memories:", err);
        listContainer.innerHTML = '<div class="vault-empty text-red">Erro ao carregar banco de memórias.</div>';
    }
}

function renderVaultMemories() {
    const listContainer = document.getElementById('memories-list-vault');
    const searchInput = document.getElementById('vault-search');
    const searchVal = searchInput ? searchInput.value.toLowerCase().trim() : '';
    
    if (!listContainer) return;
    listContainer.innerHTML = '';
    
    let filtered = allMemories;
    
    if (vaultActiveCategory !== 'all') {
        filtered = filtered.filter(m => m.categoria.toLowerCase() === vaultActiveCategory.toLowerCase());
    }
    
    if (searchVal) {
        filtered = filtered.filter(m => 
            m.chave.toLowerCase().includes(searchVal) || 
            m.conteudo.toLowerCase().includes(searchVal) ||
            m.categoria.toLowerCase().includes(searchVal)
        );
    }
    
    if (filtered.length === 0) {
        listContainer.innerHTML = '<div class="vault-empty">Nenhuma memória encontrada.</div>';
        return;
    }
    
    filtered.sort((a, b) => b.id - a.id);
    
    filtered.forEach(mem => {
        const card = document.createElement('div');
        card.className = 'memory-card';
        card.dataset.id = mem.id;
        
        const catClass = mem.categoria.toLowerCase().replace(/á/g, 'a').replace(/ç/g, 'c').replace(/õ/g, 'o');
        const formattedContent = mem.conteudo.replace(/\n/g, '<br>');
        
        card.innerHTML = `
            <div class="card-header-row">
                <div class="card-title-group">
                    <span class="card-key">${mem.chave}</span>
                    <span class="card-category-tag tag-${catClass}">${mem.categoria}</span>
                </div>
                <div class="card-actions">
                    <button class="btn-card-action btn-card-edit" title="Editar Memória">✏️</button>
                    <button class="btn-card-action btn-card-delete" title="Excluir Memória">🗑️</button>
                </div>
            </div>
            <div class="card-body-text">${formattedContent}</div>
        `;
        
        card.querySelector('.btn-card-edit').addEventListener('click', () => openMemoryModal(mem));
        card.querySelector('.btn-card-delete').addEventListener('click', () => confirmDeleteMemory(mem));
        
        listContainer.appendChild(card);
    });
}

function setupVaultListeners() {
    const searchInput = document.getElementById('vault-search');
    if (searchInput) {
        searchInput.addEventListener('input', renderVaultMemories);
    }
    
    const chips = document.querySelectorAll('#vault-category-filters .filter-chip');
    chips.forEach(chip => {
        chip.addEventListener('click', () => {
            chips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            vaultActiveCategory = chip.getAttribute('data-category');
            renderVaultMemories();
        });
    });
    
    const addBtn = document.getElementById('btn-add-memory');
    if (addBtn) {
        addBtn.addEventListener('click', () => openMemoryModal());
    }
    
    const cancelBtn = document.getElementById('btn-cancel-modal');
    const closeBtn = document.getElementById('btn-close-modal');
    if (cancelBtn) cancelBtn.addEventListener('click', closeMemoryModal);
    if (closeBtn) closeBtn.addEventListener('click', closeMemoryModal);
    
    const form = document.getElementById('memory-form');
    if (form) {
        form.addEventListener('submit', handleSaveMemory);
    }
}

function openMemoryModal(memory = null) {
    const modal = document.getElementById('memory-modal');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('memory-form');
    
    const idInput = document.getElementById('edit-mem-id');
    const catSelect = document.getElementById('edit-mem-category');
    const keyInput = document.getElementById('edit-mem-key');
    const contentInput = document.getElementById('edit-mem-content');
    
    form.reset();
    
    if (memory) {
        title.textContent = "Editar Memória";
        idInput.value = memory.id;
        catSelect.value = memory.categoria;
        keyInput.value = memory.chave;
        contentInput.value = memory.conteudo;
    } else {
        title.textContent = "Nova Memória";
        idInput.value = '';
    }
    
    modal.classList.add('active');
}

function closeMemoryModal() {
    const modal = document.getElementById('memory-modal');
    if (modal) modal.classList.remove('active');
}

// ==========================================================================
// NLU ACTIVE LEARNING FEEDBACK MODAL
// ==========================================================================
function setupFeedbackListeners() {
    const cancelBtn = document.getElementById('btn-cancel-feedback-modal');
    const closeBtn = document.getElementById('btn-close-feedback-modal');
    if (cancelBtn) cancelBtn.addEventListener('click', closeFeedbackModal);
    if (closeBtn) closeBtn.addEventListener('click', closeFeedbackModal);
    
    const form = document.getElementById('feedback-form');
    if (form) {
        form.addEventListener('submit', handleSaveFeedback);
    }
}

function openFeedbackModal(userMsg) {
    const modal = document.getElementById('feedback-modal');
    document.getElementById('feedback-msg-text').value = userMsg;
    document.getElementById('feedback-original-msg').textContent = `"${userMsg}"`;
    document.getElementById('feedback-details-content').value = '';
    
    const intentSelect = document.getElementById('feedback-correct-intent');
    const detailsLabel = document.getElementById('feedback-details-label');
    const detailsInput = document.getElementById('feedback-details-content');
    
    function adjustFormFields() {
        const intent = intentSelect.value;
        if (intent === 'salvar') {
            detailsLabel.textContent = "Conteúdo que a IA devia ter salvo:";
            detailsInput.placeholder = "Ex: A chave reserva fica na gaveta da entrada";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'buscar') {
            detailsLabel.textContent = "Termo de busca / Assunto procurado:";
            detailsInput.placeholder = "Ex: chave reserva";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'adicionar_lista' || intent === 'remover_lista') {
            detailsLabel.textContent = "Itens da lista (Separados por vírgula):";
            detailsInput.placeholder = "Ex: Café, leite, pão";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'limpar_lista') {
            detailsLabel.textContent = "Itens a manter na lista (Deixe vazio para limpar tudo):";
            detailsInput.placeholder = "Ex: Refrigerante";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'remover_calendario') {
            detailsLabel.textContent = "Título do compromisso a desmarcar (ou data):";
            detailsInput.placeholder = "Ex: Festa junina ou 2026-06-24";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else {
            document.getElementById('feedback-items-group').style.display = 'none';
        }
    }
    
    intentSelect.onchange = adjustFormFields;
    adjustFormFields();
    
    modal.classList.add('active');
}

function closeFeedbackModal() {
    const modal = document.getElementById('feedback-modal');
    if (modal) modal.classList.remove('active');
}

async function handleSaveFeedback(e) {
    e.preventDefault();
    const userMsg = document.getElementById('feedback-msg-text').value;
    const correctIntent = document.getElementById('feedback-correct-intent').value;
    const detailsContent = document.getElementById('feedback-details-content').value.trim();
    
    try {
        const res = await fetch('/api/ia-memoria/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userMsg,
                correct_intent: correctIntent,
                details: detailsContent
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast("Feedback enviado! A ação foi corrigida e a IA está se readequando.", "success");
            closeFeedbackModal();
            fetchVaultMemories();
            fetchCalendarData();
        } else {
            showToast(`Erro ao enviar feedback: ${data.error}`, "warning");
        }
    } catch (err) {
        console.error("Error submitting feedback:", err);
        showToast("Erro de conexão ao enviar feedback.", "warning");
    }
}

async function handleSaveMemory(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit-mem-id').value;
    const categoria = document.getElementById('edit-mem-category').value;
    const chave = document.getElementById('edit-mem-key').value.trim();
    const conteudo = document.getElementById('edit-mem-content').value.trim();
    
    if (!chave || !conteudo) {
        showToast("Por favor, preencha todos os campos obrigatórios.", "warning");
        return;
    }
    
    try {
        const res = await fetch('/api/ia-memoria/memorias/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id ? parseInt(id) : null, categoria, chave, conteudo })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, "success");
            closeMemoryModal();
            fetchVaultMemories();
        } else {
            showToast(`Erro: ${data.error}`, "warning");
        }
    } catch (err) {
        console.error("Error saving memory:", err);
        showToast("Erro de rede ao salvar memória.", "warning");
    }
}

async function confirmDeleteMemory(memory) {
    if (confirm(`Tem certeza que deseja excluir permanentemente a memória sobre "${memory.chave}"?`)) {
        try {
            const res = await fetch('/api/ia-memoria/memorias/excluir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: memory.id })
            });
            const data = await res.json();
            
            if (data.success) {
                showToast("Memória excluída com sucesso!", "success");
                fetchVaultMemories();
            } else {
                showToast(`Erro: ${data.error}`, "warning");
            }
        } catch (err) {
            console.error("Error deleting memory:", err);
            showToast("Erro de rede ao excluir memória.", "warning");
        }
    }
}

// ==========================================================================
// CHAT FUNCTIONALITY (RF001)
// ==========================================================================
function setupChatListeners() {
    const input = document.getElementById('chat-input');
    const sendBtn = document.getElementById('btn-chat-send');
    
    sendBtn.addEventListener('click', triggerChatMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') triggerChatMessage();
    });
}

async function triggerChatMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    lastUserMessage = text;
    
    // Clear input
    input.value = '';
    
    // Append user message
    appendMessage(text, 'user');
    
    // Auto scroll
    scrollChat();
    
    // Append Typing Indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai-message typing-indicator';
    typingDiv.innerHTML = '🤖 <i>Pensando nas memórias da casa...</i>';
    document.getElementById('chat-messages').appendChild(typingDiv);
    scrollChat();
    
    // Send to backend
    try {
        const res = await fetch('/api/ia-memoria/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text })
        });
        const data = await res.json();
        
        // Remove typing
        typingDiv.remove();
        
        // Append AI reply
        if (data && data.reply) {
            appendMessage(data.reply, 'ai');
        } else if (data && data.error) {
            appendMessage(`🤖 Erro do servidor: ${data.error}`, 'ai');
        } else {
            appendMessage("🤖 Desculpe, não consegui obter uma resposta válida da IA.", 'ai');
        }
        
        // Reload Vault in case a memory was saved or lists changed via chat
        fetchVaultMemories();
    } catch (err) {
        typingDiv.remove();
        appendMessage("Desculpe, ocorreu um erro de conexão com a IA.", 'ai');
    }
    
    scrollChat();
}

function appendMessage(content, sender) {
    const msgContainer = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-message`;
    
    if (content === undefined || content === null) {
        content = "Desculpe, ocorreu um erro ao obter a resposta.";
    }
    content = String(content);
    
    // Create text element
    const textSpan = document.createElement('span');
    textSpan.innerHTML = content;
    msgDiv.appendChild(textSpan);
    
    // If it's an AI message, add a WhatsApp share link
    if (sender === 'ai' && !content.includes('Pensando nas memórias')) {
        const shareContainer = document.createElement('div');
        shareContainer.className = 'share-container';
        shareContainer.style.display = 'flex';
        shareContainer.style.gap = '8px';
        shareContainer.style.alignItems = 'center';
        
        const shareBtn = document.createElement('button');
        shareBtn.className = 'btn-share-wa';
        shareBtn.innerHTML = `🟢 Compartilhar WhatsApp`;
        
        // Strip HTML tag helper to format message for WhatsApp
        const cleanText = content
            .replace(/<br\s*\/?>/gi, '\n') // convert breaks to newlines
            .replace(/<\/?[^>]+(>|$)/g, ''); // strip remaining tags
            
        shareBtn.onclick = () => openWaShare(cleanText);
        shareContainer.appendChild(shareBtn);
        
        // Add Correction Button for AI responses
        const isNormalAiMsg = content.includes('Ollama') || content.includes('Encontrei esta informação') || content.includes('Desculpe, não encontrei') || content.includes('Olá! Sou o assistente');
        if (isNormalAiMsg) {
            const feedbackBtn = document.createElement('button');
            feedbackBtn.className = 'btn-msg-feedback';
            feedbackBtn.innerHTML = `👎 Corrigir Entendimento`;
            feedbackBtn.style = "font-size: 0.72rem; color: rgba(255,255,255,0.5); border: 1px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.02); padding: 4px 8px; border-radius: 4px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px;";
            feedbackBtn.onmouseover = () => { feedbackBtn.style.background = "rgba(255,255,255,0.08)"; feedbackBtn.style.color = "white"; };
            feedbackBtn.onmouseout = () => { feedbackBtn.style.background = "rgba(255,255,255,0.02)"; feedbackBtn.style.color = "rgba(255,255,255,0.5)"; };
            
            feedbackBtn.dataset.userMsg = lastUserMessage;
            feedbackBtn.onclick = () => openFeedbackModal(feedbackBtn.dataset.userMsg);
            shareContainer.appendChild(feedbackBtn);
        }
        
        msgDiv.appendChild(shareContainer);
    }
    
    msgContainer.appendChild(msgDiv);
}

async function openWaShare(text) {
    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'wa-modal-overlay';
    overlay.id = 'wa-share-modal';
    
    let contacts = [];
    try {
        const res = await fetch('/api/ia-memoria/contatos');
        contacts = await res.json();
    } catch (e) {
        console.error("Erro ao carregar contatos:", e);
    }
    
    // Populate contact dropdown options
    let optionsHtml = '<option value="">-- Digitar número manualmente --</option>';
    contacts.forEach(c => {
        // Extract only digits from the memory content
        const numberClean = c.conteudo.replace(/\D/g, '');
        if (numberClean.length >= 8) {
            // Get a clean name from the key (e.g. "mario encanador")
            const contactName = c.chave.replace('contato', '').replace('telefone', '').trim().toUpperCase();
            optionsHtml += `<option value="${numberClean}">${contactName} (${numberClean})</option>`;
        }
    });
    
    overlay.innerHTML = `
        <div class="wa-modal glass-panel">
            <div class="wa-modal-header">
                <h3>🟢 Compartilhar no WhatsApp</h3>
            </div>
            <div class="wa-modal-body">
                <div class="form-group-wa">
                    <label>Selecione um contato salvo:</label>
                    <select id="wa-contact-select">
                        ${optionsHtml}
                    </select>
                </div>
                
                <div class="form-group-wa">
                    <label>Ou digite outro número:</label>
                    <input type="text" id="wa-custom-number" placeholder="DDD + Número (ex: 11999999999)">
                </div>
                
                <div class="form-group-wa">
                    <label>Mensagem a ser enviada:</label>
                    <textarea id="wa-msg-text" rows="5">${text}</textarea>
                </div>
            </div>
            <div class="wa-modal-footer">
                <button class="btn btn-secondary btn-sm" id="btn-wa-cancel">Cancelar</button>
                <button class="btn btn-primary btn-sm" id="btn-wa-send">Enviar</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    const select = document.getElementById('wa-contact-select');
    const customInput = document.getElementById('wa-custom-number');
    
    select.addEventListener('change', () => {
        if (select.value) {
            customInput.disabled = true;
            customInput.value = '';
            customInput.style.opacity = '0.5';
        } else {
            customInput.disabled = false;
            customInput.style.opacity = '1';
        }
    });
    
    document.getElementById('btn-wa-cancel').addEventListener('click', () => {
        overlay.remove();
    });
    
    document.getElementById('btn-wa-send').addEventListener('click', () => {
        let phoneNumber = select.value ? select.value : customInput.value.replace(/\D/g, '');
        const msgText = document.getElementById('wa-msg-text').value.trim();
        
        if (!phoneNumber) {
            showToast("Por favor, selecione um contato ou digite um número!", "warning");
            return;
        }
        
        if (!msgText) {
            showToast("A mensagem não pode estar vazia!", "warning");
            return;
        }
        
        // Default to country code 55 (Brazil) if it looks like a local phone number (8 to 11 digits)
        if (phoneNumber.length >= 8 && phoneNumber.length <= 11 && !phoneNumber.startsWith('55')) {
            phoneNumber = '55' + phoneNumber;
        }
        
        const encodedText = encodeURIComponent(msgText);
        const waUrl = `https://wa.me/${phoneNumber}?text=${encodedText}`;
        
        window.open(waUrl, '_blank');
        overlay.remove();
        showToast("Redirecionando para o WhatsApp...", "success");
    });
}

function scrollChat() {
    const msgContainer = document.getElementById('chat-messages');
    msgContainer.scrollTop = msgContainer.scrollHeight;
}

// Global scope helper for chips click
window.sendSuggested = function(text) {
    document.getElementById('chat-input').value = text;
    triggerChatMessage();
};

window.retryLastChatMessage = function() {
    if (lastUserMessage) {
        document.getElementById('chat-input').value = lastUserMessage;
        triggerChatMessage();
    } else {
        showToast("Nenhuma mensagem anterior para tentar novamente.", "warning");
    }
};

// ==========================================================================
// CALENDAR GRID RENDERER (RF003)
// ==========================================================================
function renderCalendarGrid(year, month) {
    const daysContainer = document.getElementById('calendar-days');
    daysContainer.innerHTML = '';
    
    // Get first day of June 2026 (1 is Monday, which is index 1)
    const firstDay = new Date(year, month, 1);
    const startingDayOfWeek = firstDay.getDay(); // 0 is Sunday, 1 is Monday...
    
    // June has 30 days
    const totalDays = 30;
    
    // Fill leading empty days
    for (let i = 0; i < startingDayOfWeek; i++) {
        const emptyDay = document.createElement('div');
        emptyDay.className = 'calendar-day empty';
        daysContainer.appendChild(emptyDay);
    }
    
    // Fill days of the month
    const systemDate = new Date(); // To mock "today" as June 10, 2026
    const mockTodayDay = 10; // Let's mock today as 10th of June
    
    for (let day = 1; day <= totalDays; day++) {
        const dayDiv = document.createElement('div');
        dayDiv.className = 'calendar-day';
        
        // Format ISO String key to check for events: '2026-06-XX'
        const dayString = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        
        // Check if today
        if (day === mockTodayDay) {
            dayDiv.classList.add('today');
        }
        
        // Render Day Number
        const dayNumSpan = document.createElement('span');
        dayNumSpan.className = 'day-num';
        dayNumSpan.textContent = day;
        dayDiv.appendChild(dayNumSpan);
        
        // Check for events on this day and add color dots
        const dayEvents = calendarEvents.filter(e => e.date === dayString);
        if (dayEvents.length > 0) {
            const dotsContainer = document.createElement('div');
            dotsContainer.className = 'day-events-dots';
            
            dayEvents.forEach(evt => {
                const dot = document.createElement('span');
                dot.className = 'event-dot';
                dot.style.backgroundColor = evt.color;
                dot.title = evt.title;
                dotsContainer.appendChild(dot);
            });
            dayDiv.appendChild(dotsContainer);
        }
        
        daysContainer.appendChild(dayDiv);
    }
}

function renderEventsList() {
    const listContainer = document.getElementById('calendar-events-list');
    listContainer.innerHTML = '';
    
    // Sort events by date ascending
    const sortedEvents = [...calendarEvents].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    sortedEvents.forEach(evt => {
        const card = document.createElement('div');
        card.className = 'event-card';
        card.style.borderLeft = `4px solid ${evt.color}`;
        
        // Format date display (e.g. 14 de Junho)
        const dateParts = evt.date.split('-');
        const dateFormatted = `${dateParts[2]}/${dateParts[1]}`;
        
        let metaHtml = `
            <span>🕒 ${evt.time}</span>
            <span>📅 ${dateFormatted}</span>
            <span>👤 ${evt.user}</span>
        `;
        if (evt.localizacao) {
            metaHtml += `<span style="display: block; margin-top: 4px; font-size: 0.75rem; color: rgba(255,255,255,0.75);">📍 ${evt.localizacao}</span>`;
        }
        
        let recurrenceBadge = '';
        if (evt.recorrencia) {
            let label = 'Repete';
            if (evt.recorrencia.includes('FREQ=WEEKLY')) {
                const day_map = {
                    "MO": "seg",
                    "TU": "ter",
                    "WE": "qua",
                    "TH": "qui",
                    "FR": "sex",
                    "SA": "sáb",
                    "SU": "dom"
                };
                let day_found = null;
                for (let code in day_map) {
                    if (evt.recorrencia.includes(`BYDAY=${code}`)) {
                        day_found = day_map[code];
                        break;
                    }
                }
                label = day_found ? `Semanal (${day_found})` : 'Semanal';
            }
            recurrenceBadge = `<span class="tag-difficulty" style="background-color: rgba(255,255,255,0.1); color: #fff; margin-left: 4px;">🔁 ${label}</span>`;
        }
        
        card.innerHTML = `
            <div class="event-card-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div style="display: flex; flex-direction: column; gap: 2px;">
                    <span class="event-card-title" style="font-weight: 600;">${evt.title}</span>
                    <div style="display: flex; align-items: center; gap: 4px; margin-top: 2px;">
                        <span class="tag-difficulty" style="background-color: ${evt.color}20; color: ${evt.color}">${evt.category}</span>
                        ${recurrenceBadge}
                    </div>
                </div>
                <div class="card-actions" style="opacity: 0.8; display: flex; gap: 6px; align-self: flex-start;">
                    <button class="btn-event-edit" title="Editar Evento" style="background: none; border: none; cursor: pointer; padding: 2px; font-size: 0.8rem;">✏️</button>
                    <button class="btn-event-delete" title="Excluir Evento" style="background: none; border: none; cursor: pointer; padding: 2px; font-size: 0.8rem;">🗑️</button>
                </div>
            </div>
            <div class="event-card-meta" style="margin-top: 8px;">
                ${metaHtml}
            </div>
        `;
        
        card.querySelector('.btn-event-edit').addEventListener('click', () => openEventModal(evt));
        card.querySelector('.btn-event-delete').addEventListener('click', () => confirmDeleteEvent(evt));
        
        listContainer.appendChild(card);
    });
}

function openEventModal(event = null) {
    const modal = document.getElementById('event-modal');
    const title = document.getElementById('event-modal-title');
    const form = document.getElementById('event-form');
    
    const idInput = document.getElementById('edit-event-id');
    const titleInput = document.getElementById('edit-event-title');
    const dateInput = document.getElementById('edit-event-date');
    const timeInput = document.getElementById('edit-event-time');
    const userInput = document.getElementById('edit-event-user');
    const catSelect = document.getElementById('edit-event-category');
    const locInput = document.getElementById('edit-event-location');
    const recSelect = document.getElementById('edit-event-recurrence');
    const colorInput = document.getElementById('edit-event-color');
    
    form.reset();
    
    if (event) {
        title.textContent = "Editar Compromisso";
        idInput.value = event.id;
        titleInput.value = event.title;
        dateInput.value = event.date;
        timeInput.value = event.time;
        userInput.value = event.user;
        catSelect.value = event.category;
        locInput.value = event.localizacao || '';
        recSelect.value = event.recorrencia || '';
        colorInput.value = event.color || '#5f27cd';
    } else {
        title.textContent = "Novo Compromisso";
        idInput.value = '';
        colorInput.value = '#5f27cd';
        
        // Default date to today's date in YYYY-MM-DD
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        dateInput.value = `${year}-${month}-${day}`;
        timeInput.value = "12:00";
    }
    
    modal.classList.add('active');
}

function closeEventModal() {
    const modal = document.getElementById('event-modal');
    if (modal) modal.classList.remove('active');
}

async function handleSaveEvent(e) {
    e.preventDefault();
    
    const id = document.getElementById('edit-event-id').value;
    const titulo = document.getElementById('edit-event-title').value.trim();
    const dateVal = document.getElementById('edit-event-date').value;
    const timeVal = document.getElementById('edit-event-time').value;
    const userVal = document.getElementById('edit-event-user').value;
    const categoria = document.getElementById('edit-event-category').value;
    const localizacao = document.getElementById('edit-event-location').value.trim();
    const recorrencia = document.getElementById('edit-event-recurrence').value;
    const cor = document.getElementById('edit-event-color').value;
    
    if (!titulo || !dateVal || !timeVal) {
        showToast("Por favor, preencha todos os campos obrigatórios.", "warning");
        return;
    }
    
    try {
        const res = await fetch('/api/calendario/salvar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id: id ? parseInt(id) : null,
                titulo,
                data: dateVal,
                hora: timeVal,
                responsavel: userVal,
                categoria,
                localizacao,
                recorrencia,
                cor
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast(data.message, "success");
            closeEventModal();
            fetchCalendarData();
        } else {
            showToast(`Erro: ${data.error}`, "warning");
        }
    } catch (err) {
        console.error("Error saving event:", err);
        showToast("Erro de rede ao salvar compromisso.", "warning");
    }
}

async function confirmDeleteEvent(event) {
    if (confirm(`Tem certeza que deseja desmarcar permanentemente o compromisso "${event.title}"?`)) {
        try {
            const res = await fetch('/api/calendario/excluir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: event.id })
            });
            const data = await res.json();
            
            if (data.success) {
                showToast("Compromisso desmarcado com sucesso!", "success");
                fetchCalendarData();
            } else {
                showToast(`Erro: ${data.error}`, "warning");
            }
        } catch (err) {
            console.error("Error deleting event:", err);
            showToast("Erro de rede ao excluir compromisso.", "warning");
        }
    }
}

function setupCalendarListeners() {
    const syncBtn = document.getElementById('cal-sync-btn');
    if (!syncBtn) return;
    
    syncBtn.addEventListener('click', async () => {
        const symbol = document.getElementById('sync-icon-symbol');
        const text = document.getElementById('sync-btn-text');
        
        // Visual loading state
        if (symbol) symbol.classList.add('spin');
        if (text) text.textContent = 'Sincronizando...';
        syncBtn.disabled = true;
        
        try {
            const res = await fetch('/api/calendario/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            
            if (res.ok && data.success) {
                showToast("📅 Sincronização concluída com o Google Agenda!", "success");
                // Reload events
                await fetchCalendarData();
            } else {
                showToast(`⚠️ Sincronização: ${data.error || 'Erro desconhecido'}`, "warning");
            }
        } catch (err) {
            console.error("Erro de sincronização:", err);
            showToast("⚠️ Erro de rede ao sincronizar com o Google Agenda.", "warning");
        } finally {
            if (symbol) symbol.classList.remove('spin');
            if (text) text.textContent = 'Sincronizar Google';
            syncBtn.disabled = false;
        }
    });
    
    // Add Event button listener
    const addEventBtn = document.getElementById('btn-add-event');
    if (addEventBtn) {
        addEventBtn.addEventListener('click', () => openEventModal());
    }
    
    // Close modals
    const cancelBtn = document.getElementById('btn-cancel-event-modal');
    const closeBtn = document.getElementById('btn-close-event-modal');
    if (cancelBtn) cancelBtn.addEventListener('click', closeEventModal);
    if (closeBtn) closeBtn.addEventListener('click', closeEventModal);
    
    // Form submission
    const form = document.getElementById('event-form');
    if (form) {
        form.addEventListener('submit', handleSaveEvent);
    }
}

// ==========================================================================
// TO-DO LIST GAMER LOGIC (RF004)
// ==========================================================================
// ==========================================================================
// TO-DO LIST GAMER LOGIC (RF004)
// ==========================================================================
function setupGamerListeners() {
    // Reset button
    const resetBtn = document.getElementById('btn-reset-quests');
    if (resetBtn) {
        resetBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/todo-gamer/reset', { method: 'POST' });
                const data = await res.json();
                gamerState = data.state;
                updateGamerUI();
                fetchCalendarData();
                showToast("Missões diárias recarregadas!", "info");
            } catch (err) {
                showToast("Erro ao recarregar missões.", "warning");
            }
        });
    }

    // Circular member selector tabs
    const gamerTabs = document.querySelectorAll('.gamer-tab');
    gamerTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            gamerTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            activeGamerMember = tab.getAttribute('data-member');
            updateGamerUI();
        });
    });

    // Reward Modal open/close
    const addRewardBtn = document.getElementById('btn-add-reward');
    const rewardModal = document.getElementById('reward-modal');
    const closeRewardModalBtn = document.getElementById('btn-close-reward-modal');
    const cancelRewardModalBtn = document.getElementById('btn-cancel-reward-modal');
    
    if (addRewardBtn) {
        addRewardBtn.addEventListener('click', () => {
            if (rewardModal) rewardModal.classList.add('active');
        });
    }
    
    const closeRewardModal = () => {
        if (rewardModal) rewardModal.classList.remove('active');
        const form = document.getElementById('reward-form');
        if (form) form.reset();
    };
    
    if (closeRewardModalBtn) closeRewardModalBtn.addEventListener('click', closeRewardModal);
    if (cancelRewardModalBtn) cancelRewardModalBtn.addEventListener('click', closeRewardModal);

    // Reward Form Submission
    const rewardForm = document.getElementById('reward-form');
    if (rewardForm) {
        rewardForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const titulo = document.getElementById('new-reward-title').value.trim();
            const custo = parseInt(document.getElementById('new-reward-cost').value);
            const icone = document.getElementById('new-reward-icon').value.trim();
            
            if (!titulo || isNaN(custo) || !icone) {
                showToast("Por favor, preencha todos os campos corretamente.", "warning");
                return;
            }
            
            try {
                const res = await fetch('/api/todo-gamer/add-reward', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        usuario_nome: activeGamerMember,
                        titulo,
                        custo,
                        icone
                    })
                });
                const data = await res.json();
                
                if (res.ok) {
                    gamerState = data.state;
                    updateGamerUI();
                    closeRewardModal();
                    showToast("Nova recompensa adicionada com sucesso!", "success");
                } else {
                    showToast(`Erro: ${data.error}`, "warning");
                }
            } catch (err) {
                showToast("Erro ao criar nova recompensa.", "warning");
            }
        });
    }
}

function updateGamerUI() {
    if (!gamerState || !gamerState.profiles) return;
    
    // Find active user profile
    const char = gamerState.profiles.find(p => p.nome.toLowerCase() === activeGamerMember.toLowerCase()) || gamerState.character;
    if (!char) return;
    
    // 1. Profile Header
    document.getElementById('gamer-avatar').textContent = char.avatar;
    document.getElementById('gamer-name').textContent = char.nome;
    document.getElementById('gamer-class').textContent = `Classe: ${char.classe}`;
    document.getElementById('gamer-level').textContent = char.nivel;
    document.getElementById('gamer-gold').textContent = char.gold;
    
    // XP Progress Bar
    const xpPercentage = (char.xp / char.xp_to_next_level) * 100;
    document.getElementById('gamer-xp-bar').style.width = `${xpPercentage}%`;
    document.getElementById('gamer-xp-text').textContent = `${char.xp} / ${char.xp_to_next_level} XP`;
    
    // 2. Active Quests
    const questsContainer = document.getElementById('quests-list');
    questsContainer.innerHTML = '';
    
    // Filter quests for the active member
    const memberQuests = gamerState.quests.filter(q => q.usuario_nome.toLowerCase() === activeGamerMember.toLowerCase());
    
    if (memberQuests.length === 0) {
        questsContainer.innerHTML = '<div class="vault-empty">Nenhuma missão ativa para este membro hoje.</div>';
    } else {
        memberQuests.forEach(quest => {
            const card = document.createElement('div');
            card.className = `quest-card ${quest.completed ? 'completed' : ''}`;
            
            const actionHtml = quest.completed 
                ? `<span class="quest-status-checked">⭐ Concluída</span>` 
                : `<button class="btn-complete" onclick="completeQuest(${quest.id})">Concluir</button>`;
                
            card.innerHTML = `
                <div class="quest-details">
                    <span class="quest-title">${quest.titulo}</span>
                    <div class="quest-meta">
                        <span class="tag-difficulty">${quest.dificuldade}</span>
                        <span class="tag-difficulty">${quest.categoria}</span>
                        <div class="rewards-pills-row">
                            <span class="xp-pill">🔵 +${quest.reward_xp} XP</span>
                            <span class="gold-pill">🪙 +${quest.reward_gold} Gold</span>
                        </div>
                    </div>
                </div>
                <div class="quest-actions">
                    ${actionHtml}
                </div>
            `;
            questsContainer.appendChild(card);
        });
    }
    
    // 3. Reward Shop Items
    const rewardsContainer = document.getElementById('rewards-list');
    rewardsContainer.innerHTML = '';
    
    // Filter rewards for the active member
    const memberRewards = gamerState.rewards.filter(r => r.usuario_nome.toLowerCase() === activeGamerMember.toLowerCase());
    
    if (memberRewards.length === 0) {
        rewardsContainer.innerHTML = '<div class="vault-empty">Nenhuma recompensa cadastrada. Crie uma acima!</div>';
    } else {
        memberRewards.forEach(rew => {
            const card = document.createElement('div');
            card.className = `reward-card ${rew.resgatado ? 'completed' : ''}`;
            card.style.opacity = rew.resgatado ? '0.5' : '1';
            
            const btnHtml = rew.resgatado 
                ? `<span class="quest-status-checked" style="font-size: 0.75rem;">🎁 Resgatado</span>`
                : `<button class="btn-redeem" onclick="redeemReward(${rew.id}, ${rew.custo}, '${rew.titulo}')">Resgatar</button>`;
                
            card.innerHTML = `
                <div class="reward-info-group">
                    <span class="reward-card-icon">${rew.icone}</span>
                    <div class="reward-card-details">
                        <span class="reward-card-title">${rew.titulo}</span>
                        <span class="reward-card-cost">🪙 ${rew.custo} Ouro</span>
                    </div>
                </div>
                ${btnHtml}
            `;
            rewardsContainer.appendChild(card);
        });
    }
}

// Global scope handlers for onClick attributes in generated HTML
window.completeQuest = async function(questId) {
    try {
        const res = await fetch('/api/todo-gamer/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quest_id: questId })
        });
        const data = await res.json();
        
        if (data.error) {
            showToast(data.error, "warning");
            return;
        }
        
        gamerState = data.state;
        updateGamerUI();
        fetchCalendarData(); // Refresh calendar checks
        
        // Show success rewards toast
        showToast(`Quest Concluída! Ganhou +${data.reward_xp} XP e +${data.reward_gold} Ouro! ⚔️`, "success");
        
        // Find if user leveled up
        const activeChar = gamerState.profiles.find(p => p.nome.toLowerCase() === activeGamerMember.toLowerCase());
        if (data.leveled_up && activeChar) {
            setTimeout(() => {
                showToast(`🎉 PARABÉNS! ${activeChar.nome} subiu para o Nível ${activeChar.nivel}! ✨ Novos poderes liberados!`, "success");
            }, 1000);
        }
    } catch (err) {
        showToast("Erro ao processar conclusão da missão.", "warning");
    }
};

window.redeemReward = async function(rewardId, cost, title) {
    if (!gamerState) return;
    
    const char = gamerState.profiles.find(p => p.nome.toLowerCase() === activeGamerMember.toLowerCase());
    if (!char) return;
    
    if (char.gold < cost) {
        showToast(`🪙 Ouro insuficiente para resgatar "${title}"! Falta ${cost - char.gold} de ouro.`, "warning");
        return;
    }
    
    try {
        const res = await fetch('/api/todo-gamer/redeem', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reward_id: rewardId })
        });
        const data = await res.json();
        
        if (data.error) {
            showToast(data.error, "warning");
            return;
        }
        
        gamerState = data.state;
        updateGamerUI();
        showToast(`🛒 Recompensa "${title}" resgatada com sucesso! Divirta-se! 🎮`, "success");
    } catch (err) {
        showToast("Erro ao resgatar recompensa.", "warning");
    }
};

// ==========================================================================
// UTILS
// ==========================================================================
function formatCurrency(val) {
    return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
}

// ==========================================================================
// OLLAMA RETRAINING & ONLINE STATUS POLL
// ==========================================================================
async function checkOllamaStatus() {
    const badge = document.getElementById('ai-status-badge');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('btn-chat-send');
    const micBtn = document.getElementById('btn-chat-mic');
    
    if (!badge) return;
    
    try {
        const res = await fetch('/api/ia-memoria/status');
        const data = await res.json();
        
        if (data.status === 'training') {
            badge.textContent = 'Treinando IA... 🧠';
            badge.className = 'badge badge-warning';
            
            if (chatInput) {
                chatInput.disabled = true;
                chatInput.placeholder = 'Aguarde, a IA está se readequando...';
            }
            if (sendBtn) sendBtn.disabled = true;
            if (micBtn) micBtn.disabled = true;
        } else if (data.status === 'offline') {
            badge.textContent = 'Ollama Offline';
            badge.className = 'badge badge-danger';
            
            if (chatInput) {
                chatInput.disabled = true;
                chatInput.placeholder = 'Ollama está offline. Inicie o serviço localmente...';
            }
            if (sendBtn) sendBtn.disabled = true;
            if (micBtn) micBtn.disabled = true;
        } else {
            badge.textContent = 'Online & Aprendendo';
            badge.className = 'badge badge-success';
            
            if (chatInput && chatInput.disabled) {
                chatInput.disabled = false;
                chatInput.placeholder = "Pergunte ex: 'Onde está a chave reserva?' ou 'Qual o contato do encanador?'...";
            }
            if (sendBtn) sendBtn.disabled = false;
            if (micBtn) micBtn.disabled = false;
        }
    } catch (err) {
        console.error("Error polling Ollama status:", err);
        badge.textContent = 'Ollama Offline';
        badge.className = 'badge badge-danger';
        if (chatInput) {
            chatInput.disabled = true;
            chatInput.placeholder = 'Erro ao conectar com o servidor local...';
        }
        if (sendBtn) sendBtn.disabled = true;
        if (micBtn) micBtn.disabled = true;
    }
}

