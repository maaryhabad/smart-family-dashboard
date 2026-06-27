// ==========================================================================
// GLOBALS & STATE
// ==========================================================================
let gamerState = null;
let calendarEvents = [];
let lastUserMessage = "";
let activeGamerMember = "Mari";
let activeRewardTab = "avail";

const goldCoinSvg = `
<svg class="gold-coin-svg" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" fill="url(#goldGradientJS)" stroke="#e1b12c" stroke-width="1.5"/>
    <circle cx="12" cy="12" r="7" fill="none" stroke="#fbc531" stroke-width="1" stroke-dasharray="1.5 1.5"/>
    <path d="M14.5 9.5C14 8.2 12.8 7.5 11.5 7.5C9.3 7.5 7.5 9.3 7.5 12C7.5 14.7 9.3 16.5 11.5 16.5C13.5 16.5 14.5 15.2 14.5 13.5H11.5" stroke="#d35400" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    <defs>
        <radialGradient id="goldGradientJS" cx="12" cy="12" r="10" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stop-color="#feca57"/>
            <stop offset="70%" stop-color="#ffb142"/>
            <stop offset="100%" stop-color="#d35400"/>
        </radialGradient>
    </defs>
</svg>`;


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
    carregarDespesas();

    // Add Event Listeners
    setupChatListeners();
    setupGamerListeners();
    setupVaultListeners();
    setupFeedbackListeners();
    setupCalendarListeners();
    setupDespesasListeners();
    setupTransacoesListeners();
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

    const renderedMessage = message.replace(/🪙/g, goldCoinSvg);
    toast.innerHTML = `<span>${icon}</span> <span>${renderedMessage}</span>`;
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
    'todo-gamer': { title: '🎮 Quadro de Missões Gamer', subtitle: 'Cumpra tarefas domésticas, ganhe XP e suba de nível!' },
    'despesas-recorrentes': { title: '💰 Despesas Recorrentes', subtitle: 'Gerenciamento de despesas e parcelas da casa' }
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

            let statusBadge = '';
            if (tx.pago === 1) {
                statusBadge = '<span class="badge badge-success">Pago</span>';
            } else {
                const parts = tx.date.split('/');
                if (parts.length === 3) {
                    const day = parseInt(parts[0], 10);
                    const month = parseInt(parts[1], 10) - 1;
                    const year = parseInt(parts[2], 10);
                    const txDate = new Date(year, month, day);
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    if (txDate < today) {
                        statusBadge = '<span class="badge badge-danger">Atrasado</span>';
                    } else {
                        statusBadge = '<span class="badge badge-warning">Pendente</span>';
                    }
                } else {
                    statusBadge = '<span class="badge badge-warning">Pendente</span>';
                }
            }

            row.innerHTML = `
                <td><strong>${tx.description}</strong></td>
                <td><span class="tag-difficulty">${tx.category}</span></td>
                <td>${tx.date}</td>
                <td>${tx.user}</td>
                <td>${statusBadge}</td>
                <td class="text-right ${amountClass}"><strong>${prefix}${formatCurrency(tx.amount)}</strong></td>
                <td class="text-center">
                    <button class="btn-delete-transacao" style="cursor: pointer; background: none; border: none; font-size: 1rem;" title="Excluir Transação">🗑️</button>
                </td>
            `;
            const btnDelete = row.querySelector('.btn-delete-transacao');
            btnDelete.addEventListener('click', () => excluirTransacao(tx.id));
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

// 5. RECORRENTES (DESPESAS)
function calcularTotaisDespesas(despesas) {
    let totalPendente = 0;
    let totalPago = 0;
    let qtdPagas = 0;
    
    despesas.forEach(item => {
        const valor = parseFloat(item.valor) || 0;
        if (item.pago === 1) {
            totalPago += valor;
            qtdPagas++;
        } else {
            totalPendente += valor;
        }
    });

    const totalContas = despesas.length;
    const progressoPorcentagem = totalContas > 0 ? Math.round((qtdPagas / totalContas) * 100) : 0;

    const elTotalPendente = document.getElementById('despesas-total-pendente');
    const elTotalPago = document.getElementById('despesas-total-pago');
    const elProgressoBar = document.getElementById('despesas-progresso-bar');
    const elProgressoTexto = document.getElementById('despesas-progresso-texto');

    if (elTotalPendente) elTotalPendente.textContent = `R$ ${totalPendente.toFixed(2)}`;
    if (elTotalPago) elTotalPago.textContent = `R$ ${totalPago.toFixed(2)}`;
    if (elProgressoBar) elProgressoBar.style.width = `${progressoPorcentagem}%`;
    if (elProgressoTexto) elProgressoTexto.textContent = `${qtdPagas} de ${totalContas} (${progressoPorcentagem}%)`;
}

function carregarDespesas() {
    fetch('/api/financas/despesas')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('lista-despesas-recorrentes');
            if (!tbody) return;
            tbody.innerHTML = ''; // Limpa a tabela atual

            // Sort by upcoming day relative to current day of the month
            const todayDay = new Date().getDate();
            data.sort((a, b) => {
                let diffA = a.dia_vencimento - todayDay;
                if (diffA < 0) diffA += 31; // wrap to next month
                let diffB = b.dia_vencimento - todayDay;
                if (diffB < 0) diffB += 31;
                return diffA - diffB;
            });

            // Calculate totals
            calcularTotaisDespesas(data);

            data.forEach(item => {
                const tr = document.createElement('tr');
                if (item.pago === 1) {
                    tr.style.opacity = '0.6';
                }

                // Checklist checkbox column
                const tdStatus = document.createElement('td');
                const label = document.createElement('label');
                label.style.display = 'inline-flex';
                label.style.alignItems = 'center';
                label.style.cursor = 'pointer';
                label.style.gap = '8px';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = item.pago === 1;
                checkbox.style.cursor = 'pointer';
                checkbox.style.accentColor = 'var(--color-green)';
                checkbox.addEventListener('change', async () => {
                    const isPago = checkbox.checked ? 1 : 0;
                    try {
                        const res = await fetch('/api/financas/despesas/pago', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ id: item.id, pago: isPago })
                        });
                        const resData = await res.json();
                        if (res.ok && resData.success) {
                            showToast(isPago ? "Despesa marcada como paga!" : "Despesa marcada como pendente!", "success");
                            item.pago = isPago;
                            if (isPago) {
                                tr.style.opacity = '0.6';
                                tdDesc.style.textDecoration = 'line-through';
                                statusText.style.color = 'var(--color-green)';
                                statusText.textContent = 'Pago';
                            } else {
                                tr.style.opacity = '1';
                                tdDesc.style.textDecoration = 'none';
                                statusText.style.color = 'var(--text-muted)';
                                statusText.textContent = 'Pendente';
                            }
                            calcularTotaisDespesas(data);
                        } else {
                            showToast("Erro ao atualizar status.", "warning");
                            checkbox.checked = !checkbox.checked;
                        }
                    } catch (e) {
                        console.error(e);
                        showToast("Erro de conexão.", "warning");
                        checkbox.checked = !checkbox.checked;
                    }
                });

                const statusText = document.createElement('span');
                statusText.textContent = item.pago === 1 ? 'Pago' : 'Pendente';
                statusText.style.fontSize = '0.85rem';
                statusText.style.fontWeight = '500';
                statusText.style.color = item.pago === 1 ? 'var(--color-green)' : 'var(--text-muted)';

                label.appendChild(checkbox);
                label.appendChild(statusText);
                tdStatus.appendChild(label);
                tr.appendChild(tdStatus);
                
                // Description cell
                const tdDesc = document.createElement('td');
                tdDesc.innerHTML = `<strong>${item.descricao}</strong>`;
                if (item.pago === 1) {
                    tdDesc.style.textDecoration = 'line-through';
                }
                tr.appendChild(tdDesc);

                // Category cell
                const tdCat = document.createElement('td');
                tdCat.innerHTML = `<span class="tag-difficulty">${item.categoria || 'Outros'}</span>`;
                tr.appendChild(tdCat);

                // Value cell
                const tdValue = document.createElement('td');
                tdValue.textContent = `R$ ${parseFloat(item.valor).toFixed(2)}`;
                tr.appendChild(tdValue);

                // Day cell
                const tdDay = document.createElement('td');
                tdDay.textContent = item.dia_vencimento;
                tr.appendChild(tdDay);

                // Type cell
                const tdType = document.createElement('td');
                tdType.textContent = item.tipo;
                tr.appendChild(tdType);

                // Actions cell
                const tdActions = document.createElement('td');
                
                const btnEdit = document.createElement('button');
                btnEdit.innerHTML = '✏️';
                btnEdit.className = 'btn-edit-despesa';
                btnEdit.style.marginRight = '8px';
                btnEdit.style.cursor = 'pointer';
                btnEdit.style.background = 'none';
                btnEdit.style.border = 'none';
                btnEdit.addEventListener('click', () => abrirModalEdicao(item));
                tdActions.appendChild(btnEdit);

                const btnDelete = document.createElement('button');
                btnDelete.innerHTML = '🗑️';
                btnDelete.className = 'btn-delete-despesa';
                btnDelete.style.cursor = 'pointer';
                btnDelete.style.background = 'none';
                btnDelete.style.border = 'none';
                btnDelete.addEventListener('click', () => excluirDespesa(item.id));
                tdActions.appendChild(btnDelete);

                tr.appendChild(tdActions);
                tbody.appendChild(tr);
            });
        });
}

function abrirModalEdicao(despesa = null) {
    const modal = document.getElementById('despesa-modal');
    if (!modal) return;
    const form = document.getElementById('despesa-form');
    if (form) form.reset();

    const titleEl = document.getElementById('despesa-modal-title');
    if (titleEl) {
        titleEl.textContent = despesa ? "Editar Despesa" : "Nova Despesa";
    }

    const idInput = document.getElementById('edit-despesa-id');
    const descInput = document.getElementById('despesa-descricao');
    const valorInput = document.getElementById('despesa-valor');
    const diaInput = document.getElementById('despesa-dia');
    const tipoSelect = document.getElementById('despesa-tipo');
    const catSelect = document.getElementById('despesa-categoria');
    const parcelasInput = document.getElementById('despesa-parcelas');
    const parcelasGroup = document.getElementById('despesa-parcelas-group');

    if (despesa) {
        if (idInput) idInput.value = despesa.id || '';
        if (descInput) descInput.value = despesa.descricao || '';
        if (valorInput) valorInput.value = despesa.valor || '';
        if (diaInput) diaInput.value = despesa.dia_vencimento || '';
        if (tipoSelect) tipoSelect.value = despesa.tipo || 'Recorrente';
        if (catSelect) catSelect.value = despesa.categoria || '';
        if (parcelasInput) parcelasInput.value = despesa.total_parcelas || '';
        
        if (parcelasGroup) {
            if (despesa.tipo === 'Parcelado') {
                parcelasGroup.style.display = 'block';
            } else {
                parcelasGroup.style.display = 'none';
            }
        }
    } else {
        if (idInput) idInput.value = '';
        if (tipoSelect) tipoSelect.value = 'Recorrente';
        if (catSelect) catSelect.value = '';
        if (parcelasGroup) {
            parcelasGroup.style.display = 'none';
        }
        if (parcelasInput) {
            parcelasInput.value = '';
        }
    }

    modal.classList.add('active');
}

async function excluirDespesa(id) {
    if (confirm("Tem certeza que deseja excluir esta despesa?")) {
        try {
            const res = await fetch('/api/financas/despesas/excluir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: id })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                showToast("Despesa excluída com sucesso!", "success");
                carregarDespesas();
                fetchFinanceData();
            } else {
                showToast(`Erro: ${data.error || 'Não foi possível excluir.'}`, "warning");
            }
        } catch (err) {
            console.error("Erro ao excluir despesa:", err);
            showToast("Erro de rede ao excluir despesa.", "warning");
        }
    }
}

function setupDespesasListeners() {
    const addBtn = document.getElementById('btn-add-despesa');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            abrirModalEdicao(null);
        });
    }

    const closeBtn = document.getElementById('btn-close-despesa-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            const modal = document.getElementById('despesa-modal');
            if (modal) modal.classList.remove('active');
        });
    }

    const cancelBtn = document.getElementById('btn-cancel-despesa-modal');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            const modal = document.getElementById('despesa-modal');
            if (modal) modal.classList.remove('active');
        });
    }

    const tipoSelect = document.getElementById('despesa-tipo');
    const parcelasGroup = document.getElementById('despesa-parcelas-group');
    const parcelasInput = document.getElementById('despesa-parcelas');
    if (tipoSelect && parcelasGroup) {
        tipoSelect.addEventListener('change', () => {
            if (tipoSelect.value === 'Parcelado') {
                parcelasGroup.style.display = 'block';
            } else {
                parcelasGroup.style.display = 'none';
                if (parcelasInput) parcelasInput.value = '';
            }
        });
    }

    const form = document.getElementById('despesa-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('edit-despesa-id').value;
            const descricao = document.getElementById('despesa-descricao').value.trim();
            const valor = parseFloat(document.getElementById('despesa-valor').value);
            const dia_vencimento = parseInt(document.getElementById('despesa-dia').value);
            const tipo = document.getElementById('despesa-tipo').value;
            const categoria = document.getElementById('despesa-categoria').value;
            const total_parcelas = tipo === 'Parcelado' ? parseInt(document.getElementById('despesa-parcelas').value || 1) : 1;

            if (!descricao || isNaN(valor) || isNaN(dia_vencimento) || !categoria) {
                showToast("Por favor, preencha todos os campos obrigatórios.", "warning");
                return;
            }

            const url = id ? '/api/financas/despesas/editar' : '/api/financas/despesas';
            const payload = {
                descricao,
                valor,
                dia_vencimento,
                tipo,
                categoria,
                total_parcelas
            };
            if (id) {
                payload.id = parseInt(id);
            }

            try {
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (res.ok && data.success) {
                    showToast(data.message, "success");
                    const modal = document.getElementById('despesa-modal');
                    if (modal) modal.classList.remove('active');
                    carregarDespesas();
                    fetchFinanceData();
                } else {
                    showToast(`Erro: ${data.error || 'Não foi possível salvar.'}`, "warning");
                }
            } catch (err) {
                console.error("Erro ao salvar despesa:", err);
                showToast("Erro de rede ao salvar despesa.", "warning");
            }
        });
    }
}

function setupTransacoesListeners() {
    const addBtn = document.getElementById('btn-add-transacao');
    if (addBtn) {
        addBtn.addEventListener('click', () => {
            abrirModalTransacao();
        });
    }

    const closeBtn = document.getElementById('btn-close-transacao-modal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            const modal = document.getElementById('transacao-modal');
            if (modal) modal.classList.remove('active');
        });
    }

    const cancelBtn = document.getElementById('btn-cancel-transacao-modal');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            const modal = document.getElementById('transacao-modal');
            if (modal) modal.classList.remove('active');
        });
    }

    const tipoSelect = document.getElementById('transacao-tipo');
    const catSelect = document.getElementById('transacao-categoria');
    if (tipoSelect && catSelect) {
        tipoSelect.addEventListener('change', () => {
            if (tipoSelect.value === 'entrada') {
                catSelect.value = 'Receita';
            } else {
                if (catSelect.value === 'Receita') {
                    catSelect.value = 'Outros';
                }
            }
        });
    }

    const form = document.getElementById('transacao-form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const descricao = document.getElementById('transacao-descricao').value.trim();
            const valor = parseFloat(document.getElementById('transacao-valor').value);
            const dataVal = document.getElementById('transacao-data').value;
            const categoria = catSelect.value;
            const responsavel = document.getElementById('transacao-responsavel').value;
            const pago = parseInt(document.getElementById('transacao-pago').value);
            const tipo = tipoSelect.value;

            if (!descricao || isNaN(valor) || !dataVal || !categoria || !responsavel) {
                showToast("Por favor, preencha todos os campos obrigatórios.", "warning");
                return;
            }

            const payload = {
                descricao,
                valor,
                data: dataVal,
                categoria,
                responsavel,
                pago,
                tipo
            };

            try {
                const res = await fetch('/api/financas/transacoes', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const resData = await res.json();

                if (res.ok && resData.success) {
                    showToast(resData.message, "success");
                    const modal = document.getElementById('transacao-modal');
                    if (modal) modal.classList.remove('active');
                    fetchFinanceData();
                    carregarDespesas(); // Refresh checklist too since linked status could have changed
                } else {
                    showToast(`Erro: ${resData.error || 'Não foi possível salvar.'}`, "warning");
                }
            } catch (err) {
                console.error("Erro ao salvar transação:", err);
                showToast("Erro de rede ao salvar transação.", "warning");
            }
        });
    }
}

function abrirModalTransacao() {
    const modal = document.getElementById('transacao-modal');
    if (!modal) return;
    const form = document.getElementById('transacao-form');
    if (form) form.reset();

    // Default data to today's date
    const dateInput = document.getElementById('transacao-data');
    if (dateInput) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        dateInput.value = `${yyyy}-${mm}-${dd}`;
    }

    // Default category to Receita (for Entrada default)
    const catSelect = document.getElementById('transacao-categoria');
    if (catSelect) catSelect.value = 'Receita';

    modal.classList.add('active');
}

async function excluirTransacao(id) {
    if (confirm("Tem certeza que deseja excluir esta transação?")) {
        try {
            const res = await fetch('/api/financas/transacoes/excluir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id })
            });
            const data = await res.json();

            if (res.ok && data.success) {
                showToast("Transação excluída com sucesso!", "success");
                fetchFinanceData();
                carregarDespesas(); // Refresh despesas since toggling linked transactions changes despesa status
            } else {
                showToast(`Erro: ${data.error || 'Não foi possível excluir.'}`, "warning");
            }
        } catch (err) {
            console.error("Erro ao excluir transação:", err);
            showToast("Erro de rede ao excluir transação.", "warning");
        }
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
        } else if (intent === 'composto_lista') {
            detailsLabel.textContent = "Itens a adicionar e a remover (detalhado):";
            detailsInput.placeholder = "Ex: Adicionar café, remover pão";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'agendar_calendario') {
            detailsLabel.textContent = "Detalhes do compromisso (Título, Data, Hora):";
            detailsInput.placeholder = "Ex: Dentista às 14:00 em 2026-06-25";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'remover_calendario') {
            detailsLabel.textContent = "Título do compromisso a desmarcar (ou data):";
            detailsInput.placeholder = "Ex: Festa junina ou 2026-06-24";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'completar_tarefa') {
            detailsLabel.textContent = "Tarefa a concluir (e membro responsável):";
            detailsInput.placeholder = "Ex: Lavar louça por Cassi";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'resgatar_recompensa') {
            detailsLabel.textContent = "Recompensa a resgatar (e membro):";
            detailsInput.placeholder = "Ex: Videogame por Mari";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'salvar_receita') {
            detailsLabel.textContent = "Nome da receita, ingredientes e modo de preparo:";
            detailsInput.placeholder = "Ex: Bolo de cenoura com ingredientes e passos...";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'deletar_receita' || intent === 'comprar_receita') {
            detailsLabel.textContent = "Nome da receita:";
            detailsInput.placeholder = "Ex: Bolo de cenoura";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'listar_tarefas' || intent === 'listar_recompensas_resgatadas') {
            detailsLabel.textContent = "Membro da família (Opcional):";
            detailsInput.placeholder = "Ex: Isa, Cassi, Mari";
            document.getElementById('feedback-items-group').style.display = 'block';
        } else if (intent === 'adicionar_transacao') {
            detailsLabel.textContent = "Despesa ou Receita (Descrição, valor e categoria):";
            detailsInput.placeholder = "Ex: despesa de 150 no Carrefour ou receita de 1200";
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
            fetchFinanceData();
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
    textSpan.innerHTML = content.replace(/🪙/g, goldCoinSvg);
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
window.sendSuggested = function (text) {
    document.getElementById('chat-input').value = text;
    triggerChatMessage();
};

window.retryLastChatMessage = function () {
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
    const systemDate = new Date();
    const actualYear = systemDate.getFullYear();
    const actualMonth = systemDate.getMonth();
    const actualDay = systemDate.getDate();
    const isCurrentMonthYear = (year === actualYear && month === actualMonth);

    for (let day = 1; day <= totalDays; day++) {
        const dayDiv = document.createElement('div');
        dayDiv.className = 'calendar-day';

        // Format ISO String key to check for events: '2026-06-XX'
        const dayString = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

        // Check if today
        if (isCurrentMonthYear && day === actualDay) {
            dayDiv.classList.add('today');
        }

        // Render Day Number
        const dayNumSpan = document.createElement('span');
        dayNumSpan.className = 'day-num';
        dayNumSpan.textContent = day;
        dayDiv.appendChild(dayNumSpan);

        // Check for events on this day and add color dots (excluding tasks)
        const dayEvents = calendarEvents.filter(e => {
            if (e.is_task) return false;
            const start = e.date;
            const end = e.data_fim || e.date;
            return dayString >= start && dayString <= end;
        });
        if (dayEvents.length > 0) {
            const dotsContainer = document.createElement('div');
            dotsContainer.className = 'day-events-dots';

            dayEvents.forEach(evt => {
                const dot = document.createElement('span');
                dot.className = 'event-dot';
                if (evt.is_task) {
                    dot.classList.add('task-dot');
                    if (evt.completed) {
                        dot.classList.add('completed');
                    }
                }
                dot.style.backgroundColor = evt.color;
                const typePrefix = evt.is_task ? '📋 [Missão] ' : '📅 [Evento] ';
                dot.title = typePrefix + evt.title;
                dotsContainer.appendChild(dot);
            });
            dayDiv.appendChild(dotsContainer);
        }

        daysContainer.appendChild(dayDiv);
    }
}

function renderEventsList() {
    const eventsListContainer = document.getElementById('calendar-events-list');
    const tasksListContainer = document.getElementById('calendar-tasks-list');

    if (eventsListContainer) eventsListContainer.innerHTML = '';
    if (tasksListContainer) tasksListContainer.innerHTML = '';

    // Use current system date dynamically (e.g. June 19, 2026)
    const systemDate = new Date();
    const todayStr = `${systemDate.getFullYear()}-${String(systemDate.getMonth() + 1).padStart(2, '0')}-${String(systemDate.getDate()).padStart(2, '0')}`;
    const todayDate = new Date(systemDate);
    todayDate.setHours(0,0,0,0);
    const maxDate = new Date(todayDate);
    maxDate.setDate(todayDate.getDate() + 8);
    const maxDateStr = maxDate.toISOString().split('T')[0];

    // ----------------------------------------------------
    // 1. RENDER APPOINTMENTS (Next 8 days, de-duplicated)
    // ----------------------------------------------------
    if (eventsListContainer) {
        // Filter regular events (not tasks) within next 8 days [todayStr, maxDateStr]
        const filteredEvents = calendarEvents.filter(evt => {
            if (evt.is_task) return false;
            const start = evt.date;
            const end = evt.data_fim || evt.date;
            return start <= maxDateStr && end >= todayStr;
        });

        // Sort by date then time
        filteredEvents.sort((a, b) => {
            const dateDiff = new Date(a.date) - new Date(b.date);
            if (dateDiff !== 0) return dateDiff;
            return a.time.localeCompare(b.time);
        });

        // De-duplicate by title (case-insensitive) to collapse recurring events
        const uniqueEvents = [];
        const seenTitles = new Set();
        filteredEvents.forEach(evt => {
            const cleanTitle = evt.title.toLowerCase().trim();
            if (!seenTitles.has(cleanTitle)) {
                seenTitles.add(cleanTitle);
                uniqueEvents.push(evt);
            }
        });

        if (uniqueEvents.length === 0) {
            eventsListContainer.innerHTML = '<div class="vault-empty" style="padding: 10px; font-size: 0.85rem; color: var(--text-muted);">Sem compromissos nos próximos 8 dias.</div>';
        } else {
            uniqueEvents.forEach(evt => {
                const card = document.createElement('div');
                card.className = 'event-card';
                card.style.borderLeft = `4px solid ${evt.color}`;

                const dateParts = evt.date.split('-');
                let dateFormatted = `${dateParts[2]}/${dateParts[1]}`;
                if (evt.data_fim && evt.data_fim !== evt.date) {
                    const endParts = evt.data_fim.split('-');
                    dateFormatted += ` a ${endParts[2]}/${endParts[1]}`;
                }

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

                eventsListContainer.appendChild(card);
            });
        }
    }

    // ----------------------------------------------------
    // 2. RENDER TODAY'S TASKS (Missões de Hoje)
    // ----------------------------------------------------
    if (tasksListContainer) {
        const rawTodayTasks = calendarEvents.filter(evt => evt.is_task && (evt.date === todayStr || (evt.date < todayStr && !evt.completed)));

        // Sort oldest first to filter duplicates keeping oldest
        rawTodayTasks.sort((a, b) => a.date.localeCompare(b.date));

        const todayTasks = [];
        const seenTodayTitles = new Set();
        rawTodayTasks.forEach(evt => {
            const titleLower = evt.title.toLowerCase().trim();
            if (!seenTodayTitles.has(titleLower)) {
                seenTodayTitles.add(titleLower);
                todayTasks.push(evt);
            }
        });

        // Special rule for Isa: if she has both "Banho" and "Banho e lavar cabelo" / "Banho e lavar o cabelo", keep only the latter.
        const hasIsaHairWash = todayTasks.some(evt => {
            if (evt.user && evt.user.toLowerCase() === 'isa') {
                const t = evt.title.toLowerCase().trim();
                return t === 'banho e lavar cabelo' || t === 'banho e lavar o cabelo';
            }
            return false;
        });
        if (hasIsaHairWash) {
            const banhoIdx = todayTasks.findIndex(evt => 
                evt.user && evt.user.toLowerCase() === 'isa' && evt.title.toLowerCase().trim() === 'banho'
            );
            if (banhoIdx !== -1) {
                todayTasks.splice(banhoIdx, 1);
            }
        }

        // Sort by time
        todayTasks.sort((a, b) => a.time.localeCompare(b.time));

        if (todayTasks.length === 0) {
            tasksListContainer.innerHTML = '<div class="vault-empty" style="padding: 10px; font-size: 0.85rem; color: var(--text-muted);">🎉 Nenhuma missão pendente para hoje!</div>';
        } else {
            todayTasks.forEach(evt => {
                const card = document.createElement('div');
                card.className = `event-card task-card ${evt.completed ? 'completed' : ''}`;

                const isOverdue = evt.date < todayStr;
                const statusIcon = evt.completed ? '✅' : (isOverdue ? '⚠️' : '⏳');
                const statusText = evt.completed ? 'Concluída' : (isOverdue ? 'Acumulada' : 'Pendente');
                const statusClass = evt.completed ? 'text-green' : (isOverdue ? 'text-red' : 'text-highlight');

                card.innerHTML = `
                    <div class="event-card-header" style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div style="display: flex; flex-direction: column; gap: 2px; width: 100%;">
                            <span class="event-card-title" style="font-weight: 600;">${evt.title}</span>
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; font-size: 0.75rem;">
                                <span class="${statusClass}" style="font-weight: 500;">${statusIcon} ${statusText}</span>
                                <span style="color: var(--color-yellow); font-weight: 600; display: inline-flex; align-items: center; gap: 2px;">🔵 ${evt.reward_xp} XP | ${goldCoinSvg} ${evt.reward_gold} G</span>
                            </div>
                        </div>
                    </div>
                    <div class="event-card-meta" style="margin-top: 8px; font-size: 0.75rem; color: var(--text-muted); display: flex; justify-content: space-between;">
                        <span>🕒 ${evt.time}</span>
                        <span>👤 Responsável: <strong>${evt.user}</strong></span>
                    </div>
                `;
                tasksListContainer.appendChild(card);
            });
        }
    }
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

    // Member Modal open/close
    const addMemberBtn = document.getElementById('btn-add-member');
    const memberModal = document.getElementById('member-modal');
    const closeMemberModalBtn = document.getElementById('btn-close-member-modal');
    const cancelMemberModalBtn = document.getElementById('btn-cancel-member-modal');

    const openMemberModal = () => {
        if (memberModal) memberModal.classList.add('active');
    };

    const closeMemberModal = () => {
        if (memberModal) memberModal.classList.remove('active');
        const form = document.getElementById('member-form');
        if (form) form.reset();
    };

    if (addMemberBtn) addMemberBtn.addEventListener('click', openMemberModal);
    if (closeMemberModalBtn) closeMemberModalBtn.addEventListener('click', closeMemberModal);
    if (cancelMemberModalBtn) cancelMemberModalBtn.addEventListener('click', closeMemberModal);

    // Reward Modal open/close
    const addRewardBtn = document.getElementById('btn-add-reward');
    const rewardModal = document.getElementById('reward-modal');
    const closeRewardModalBtn = document.getElementById('btn-close-reward-modal');
    const cancelRewardModalBtn = document.getElementById('btn-cancel-reward-modal');

    if (addRewardBtn) {
        addRewardBtn.addEventListener('click', () => {
            openRewardModal();
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
            const id = document.getElementById('edit-reward-id').value;
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
                        id: id ? parseInt(id) : null,
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
                    showToast(id ? "Recompensa atualizada com sucesso!" : "Nova recompensa adicionada com sucesso!", "success");
                } else {
                    showToast(`Erro: ${data.error}`, "warning");
                }
            } catch (err) {
                showToast(id ? "Erro ao atualizar recompensa." : "Erro ao criar nova recompensa.", "warning");
            }
        });
    }

    // Quest Modal open/close
    const addQuestBtn = document.getElementById('btn-add-quest');
    const questModal = document.getElementById('quest-modal');
    const closeQuestModalBtn = document.getElementById('btn-close-quest-modal');
    const cancelQuestModalBtn = document.getElementById('btn-cancel-quest-modal');

    if (addQuestBtn) {
        addQuestBtn.addEventListener('click', () => openQuestModal());
    }

    const closeQuestModal = () => {
        if (questModal) questModal.classList.remove('active');
        const form = document.getElementById('quest-form');
        if (form) form.reset();
    };

    if (closeQuestModalBtn) closeQuestModalBtn.addEventListener('click', closeQuestModal);
    if (cancelQuestModalBtn) cancelQuestModalBtn.addEventListener('click', closeQuestModal);

    // Quest Form difficulty auto-suggest values
    const diffSelect = document.getElementById('edit-quest-difficulty');
    if (diffSelect) {
        diffSelect.addEventListener('change', () => {
            const diff = diffSelect.value;
            const xpInput = document.getElementById('edit-quest-xp');
            const goldInput = document.getElementById('edit-quest-gold');
            if (diff === 'Fácil') {
                xpInput.value = 10;
                goldInput.value = 1;
            } else if (diff === 'Médio') {
                xpInput.value = 15;
                goldInput.value = 3;
            } else if (diff === 'Difícil') {
                xpInput.value = 25;
                goldInput.value = 5;
            } else if (diff === 'Ultra') {
                xpInput.value = 40;
                goldInput.value = 10;
            }
        });
    }

    // Quest Form Submission
    const questForm = document.getElementById('quest-form');
    if (questForm) {
        questForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const idVal = document.getElementById('edit-quest-id').value;
            const titulo = document.getElementById('edit-quest-title').value.trim();
            const user = document.getElementById('edit-quest-user').value;
            const category = document.getElementById('edit-quest-category').value;
            const difficulty = document.getElementById('edit-quest-difficulty').value;
            const dateVal = document.getElementById('edit-quest-date').value;
            const timeVal = document.getElementById('edit-quest-time').value;
            const xpVal = parseInt(document.getElementById('edit-quest-xp').value);
            const goldVal = parseInt(document.getElementById('edit-quest-gold').value);

            if (!titulo || !dateVal || !timeVal || isNaN(xpVal) || isNaN(goldVal)) {
                showToast("Por favor, preencha todos os campos corretamente.", "warning");
                return;
            }

            try {
                const res = await fetch('/api/todo-gamer/salvar', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        id: idVal ? parseInt(idVal) : null,
                        usuario_nome: user,
                        titulo,
                        categoria: category,
                        dificuldade: difficulty,
                        reward_xp: xpVal,
                        reward_gold: goldVal,
                        data: dateVal,
                        hora: timeVal
                    })
                });
                const data = await res.json();

                if (data.success) {
                    gamerState = data.state;
                    updateGamerUI();
                    closeQuestModal();
                    fetchCalendarData();
                    showToast(data.message, "success");
                } else {
                    showToast(`Erro: ${data.error}`, "warning");
                }
            } catch (err) {
                showToast("Erro ao salvar missão.", "warning");
            }
        });
    }
}

function updateGamerUI() {
    if (!gamerState || !gamerState.profiles) return;

    // Render gamer selector tabs dynamically
    const tabsRow = document.querySelector('.gamer-tabs-row');
    if (tabsRow) {
        tabsRow.innerHTML = '';
        gamerState.profiles.forEach(p => {
            const btn = document.createElement('button');
            btn.className = `gamer-tab ${activeGamerMember.toLowerCase() === p.nome.toLowerCase() ? 'active' : ''}`;
            btn.setAttribute('data-member', p.nome);
            btn.innerHTML = `${p.avatar} ${p.nome}`;
            btn.addEventListener('click', () => {
                tabsRow.querySelectorAll('.gamer-tab').forEach(t => t.classList.remove('active'));
                btn.classList.add('active');
                activeGamerMember = p.nome;
                updateGamerUI();
            });
            tabsRow.appendChild(btn);
        });
    }

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

    // Use current system date dynamically
    const systemDate = new Date();
    const todayStr = `${systemDate.getFullYear()}-${String(systemDate.getMonth() + 1).padStart(2, '0')}-${String(systemDate.getDate()).padStart(2, '0')}`;
    const rawMemberQuests = gamerState.quests.filter(q =>
        q.usuario_nome.toLowerCase() === activeGamerMember.toLowerCase() &&
        (q.data === todayStr || (q.data < todayStr && !q.completed))
    );

    // Sort oldest first so that the oldest uncompleted task accumulates rollover bonus
    rawMemberQuests.sort((a, b) => a.data.localeCompare(b.data));

    const memberQuests = [];
    const seenQuestTitles = new Set();
    rawMemberQuests.forEach(quest => {
        const titleLower = quest.titulo.toLowerCase().trim();
        if (!seenQuestTitles.has(titleLower)) {
            seenQuestTitles.add(titleLower);
            memberQuests.push(quest);
        }
    });

    // Special rule for Isa: if she has both "Banho" and "Banho e lavar cabelo" / "Banho e lavar o cabelo", keep only the latter.
    if (activeGamerMember.toLowerCase() === 'isa') {
        const hasHairWash = memberQuests.some(q => {
            const t = q.titulo.toLowerCase().trim();
            return t === 'banho e lavar cabelo' || t === 'banho e lavar o cabelo';
        });
        if (hasHairWash) {
            const banhoIdx = memberQuests.findIndex(q => q.titulo.toLowerCase().trim() === 'banho');
            if (banhoIdx !== -1) {
                memberQuests.splice(banhoIdx, 1);
            }
        }
    }

    if (memberQuests.length === 0) {
        questsContainer.innerHTML = '<div class="vault-empty">Nenhuma missão ativa para este membro hoje.</div>';
    } else {
        memberQuests.forEach(quest => {
            const card = document.createElement('div');
            card.className = `quest-card ${quest.completed ? 'completed' : ''}`;

            const actionHtml = quest.completed
                ? `<span class="quest-status-checked">⭐ Concluída</span>`
                : `<button class="btn-complete" onclick="completeQuest(${quest.id})">Concluir</button>
                   <button class="btn-complete skip-btn" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; padding: 6px 10px; border-radius: 6px; font-size: 0.8rem; color: #ff7675;" onclick="completeQuest(${quest.id}, true)">Pular</button>`;

            const isOverdue = quest.data < todayStr && !quest.completed;
            const overdueBadge = isOverdue ? '<span class="tag-difficulty" style="background-color: rgba(235, 94, 40, 0.15); color: #ff7675; border-color: rgba(235, 94, 40, 0.25);">⚠️ Acumulada</span>' : '';

            card.innerHTML = `
                <div class="quest-details">
                    <span class="quest-title">${quest.titulo}</span>
                    <div class="quest-meta">
                        <span class="tag-difficulty">${quest.dificuldade}</span>
                        <span class="tag-difficulty">${quest.categoria}</span>
                        ${overdueBadge}
                        <div class="rewards-pills-row">
                            <span class="xp-pill">🔵 +${quest.reward_xp} XP</span>
                            <span class="gold-pill" style="display: inline-flex; align-items: center; gap: 2px;">${goldCoinSvg} +${quest.reward_gold} Gold</span>
                        </div>
                    </div>
                </div>
                <div class="quest-actions" style="display: flex; align-items: center; gap: 8px;">
                    ${actionHtml}
                    <div class="quest-card-controls" style="display: flex; gap: 4px;">
                        <button class="btn-quest-edit" title="Editar Missão" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; padding: 4px 6px; border-radius: 4px; font-size: 0.75rem; color: white;">✏️</button>
                        <button class="btn-quest-delete" title="Excluir Missão" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; padding: 4px 6px; border-radius: 4px; font-size: 0.75rem; color: white;">🗑️</button>
                    </div>
                </div>
            `;

            const editBtn = card.querySelector('.btn-quest-edit');
            const deleteBtn = card.querySelector('.btn-quest-delete');
            if (editBtn) editBtn.addEventListener('click', (e) => { e.stopPropagation(); openQuestModal(quest); });
            if (deleteBtn) deleteBtn.addEventListener('click', (e) => { e.stopPropagation(); confirmDeleteQuest(quest); });

            questsContainer.appendChild(card);
        });
    }

    // 3. Reward Shop Items
    const rewardsContainer = document.getElementById('rewards-list');
    rewardsContainer.innerHTML = '';

    // Filter rewards for the active member
    const memberRewards = gamerState.rewards.filter(r => r.usuario_nome.toLowerCase() === activeGamerMember.toLowerCase());

    const displayedRewards = memberRewards.filter(r => {
        if (activeRewardTab === 'avail') {
            return r.resgatado === 0;
        } else if (activeRewardTab === 'redeemed') {
            return r.resgatado === 1;
        } else {
            return r.resgatado === 2;
        }
    });

    if (displayedRewards.length === 0) {
        if (activeRewardTab === 'avail') {
            rewardsContainer.innerHTML = '<div class="vault-empty">Nenhuma recompensa disponível. Crie uma acima!</div>';
        } else if (activeRewardTab === 'redeemed') {
            rewardsContainer.innerHTML = '<div class="vault-empty">Nenhuma recompensa resgatada pendente de entrega.</div>';
        } else {
            rewardsContainer.innerHTML = '<div class="vault-empty">Nenhuma recompensa concluída ainda.</div>';
        }
    } else {
        displayedRewards.forEach(rew => {
            const card = document.createElement('div');
            card.className = `reward-card ${rew.resgatado === 2 ? 'completed' : ''}`;
            card.style.opacity = rew.resgatado === 2 ? '0.6' : (rew.resgatado === 1 ? '0.85' : '1');

            let btnHtml = '';
            if (rew.resgatado === 0) {
                btnHtml = `<button class="btn-redeem" onclick="redeemReward(${rew.id}, ${rew.custo}, '${rew.titulo}')">Resgatar</button>`;
            } else if (rew.resgatado === 1) {
                btnHtml = `
                    <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 4px;">
                        <span class="quest-status-checked" style="font-size: 0.72rem; color: #ffeaa7;">🎁 Resgatado</span>
                        <button class="btn-complete-reward" onclick="completeReward(${rew.id})" style="background: rgba(46, 204, 113, 0.15); border: 1px solid #2ecc71; color: #2ecc71; cursor: pointer; font-size: 0.72rem; padding: 3px 6px; border-radius: 4px; font-weight: 600; transition: all 0.2s;">Marcar Entregue</button>
                    </div>
                `;
            } else if (rew.resgatado === 2) {
                btnHtml = `<span class="quest-status-checked" style="font-size: 0.72rem; color: #2ecc71;">✅ Entregue</span>`;
            }

            card.innerHTML = `
                <div class="reward-info-group">
                    <span class="reward-card-icon">${rew.icone}</span>
                    <div class="reward-card-details">
                        <span class="reward-card-title">${rew.titulo}</span>
                        <span class="reward-card-cost" style="display: inline-flex; align-items: center; gap: 2px;">${goldCoinSvg} ${rew.custo} Ouro</span>
                    </div>
                </div>
                <div class="reward-actions" style="display: flex; align-items: center; gap: 8px;">
                    ${btnHtml}
                    ${rew.resgatado === 0 ? `
                    <div class="reward-card-controls" style="display: flex; gap: 4px;">
                        <button class="btn-reward-edit" title="Editar Recompensa" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; padding: 4px 6px; border-radius: 4px; font-size: 0.75rem; color: white;">✏️</button>
                        <button class="btn-reward-delete" title="Excluir Recompensa" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); cursor: pointer; padding: 4px 6px; border-radius: 4px; font-size: 0.75rem; color: white;">🗑️</button>
                    </div>
                    ` : ''}
                </div>
            `;

            if (rew.resgatado === 0) {
                const editBtn = card.querySelector('.btn-reward-edit');
                const deleteBtn = card.querySelector('.btn-reward-delete');
                if (editBtn) editBtn.addEventListener('click', (e) => { e.stopPropagation(); openRewardModal(rew); });
                if (deleteBtn) deleteBtn.addEventListener('click', (e) => { e.stopPropagation(); confirmDeleteReward(rew); });
            }

            rewardsContainer.appendChild(card);
        });
    }
}

window.setRewardsFilter = function(filter) {
    activeRewardTab = filter;
    
    // Update button active styling
    const btnAvail = document.getElementById('btn-rewards-avail');
    const btnRedeemed = document.getElementById('btn-rewards-redeemed');
    const btnCompleted = document.getElementById('btn-rewards-completed');
    
    const tabs = [
        { el: btnAvail, name: 'avail' },
        { el: btnRedeemed, name: 'redeemed' },
        { el: btnCompleted, name: 'completed' }
    ];
    
    tabs.forEach(t => {
        if (t.el) {
            if (t.name === filter) {
                t.el.style.borderBottom = '2px solid var(--color-primary)';
                t.el.style.color = 'var(--text-white)';
                t.el.classList.add('active');
            } else {
                t.el.style.borderBottom = 'none';
                t.el.style.color = 'var(--text-muted)';
                t.el.classList.remove('active');
            }
        }
    });
    
    updateGamerUI();
};

window.completeReward = async function(rewardId) {
    try {
        const res = await fetch('/api/todo-gamer/complete-reward', {
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
        showToast("Recompensa entregue e concluída! 🎉", "success");
    } catch (err) {
        console.error("Erro ao concluir recompensa:", err);
        showToast("Erro ao concluir recompensa.", "warning");
    }
};

// Global scope handlers for onClick attributes in generated HTML
window.completeQuest = async function (questId, skip = false) {
    try {
        const res = await fetch('/api/todo-gamer/complete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ quest_id: questId, skip: skip })
        });
        const data = await res.json();

        if (data.error) {
            showToast(data.error, "warning");
            return;
        }

        gamerState = data.state;
        updateGamerUI();
        fetchCalendarData(); // Refresh calendar checks

        if (skip) {
            showToast("Quest marcada como concluída/pulada (sem ganhar ouro/XP). 🕒", "info");
        } else {
            // Show success rewards toast
            showToast(`Quest Concluída! Ganhou +${data.reward_xp} XP e +${data.reward_gold} Ouro! ⚔️`, "success");
        }

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

window.redeemReward = async function (rewardId, cost, title) {
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

function openQuestModal(quest = null) {
    const modal = document.getElementById('quest-modal');
    const title = document.getElementById('quest-modal-title');
    const form = document.getElementById('quest-form');

    const idInput = document.getElementById('edit-quest-id');
    const titleInput = document.getElementById('edit-quest-title');
    const userInput = document.getElementById('edit-quest-user');
    const catSelect = document.getElementById('edit-quest-category');
    const diffSelect = document.getElementById('edit-quest-difficulty');
    const dateInput = document.getElementById('edit-quest-date');
    const timeInput = document.getElementById('edit-quest-time');
    const xpInput = document.getElementById('edit-quest-xp');
    const goldInput = document.getElementById('edit-quest-gold');

    form.reset();

    if (quest) {
        title.textContent = "Editar Missão";
        idInput.value = quest.id;
        titleInput.value = quest.titulo;
        userInput.value = quest.usuario_nome;
        catSelect.value = quest.categoria;
        diffSelect.value = quest.dificuldade;
        dateInput.value = quest.data;
        timeInput.value = quest.hora;
        xpInput.value = quest.reward_xp;
        goldInput.value = quest.reward_gold;
    } else {
        title.textContent = "Nova Missão";
        idInput.value = '';

        // Defaults
        userInput.value = activeGamerMember; // Mariana, Cassi, Isa
        catSelect.value = "Limpeza";
        diffSelect.value = "Fácil";
        xpInput.value = 10;
        goldInput.value = 3;

        // Set date to current date: YYYY-MM-DD
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        dateInput.value = `${year}-${month}-${day}`;
        timeInput.value = "12:00";
    }

    modal.classList.add('active');
}

async function confirmDeleteQuest(quest) {
    if (confirm(`Tem certeza que deseja excluir permanentemente a missão "${quest.titulo}"?`)) {
        try {
            const res = await fetch('/api/todo-gamer/excluir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: quest.id })
            });
            const data = await res.json();

            if (data.success) {
                gamerState = data.state;
                updateGamerUI();
                fetchCalendarData();
                showToast("Missão excluída com sucesso!", "success");
            } else {
                showToast(`Erro: ${data.error}`, "warning");
            }
        } catch (err) {
            console.error("Error deleting quest:", err);
            showToast("Erro de conexão ao excluir missão.", "warning");
        }
    }
}

window.openRewardModal = function (reward = null) {
    const modal = document.getElementById('reward-modal');
    const title = document.getElementById('reward-modal-title');
    const idInput = document.getElementById('edit-reward-id');
    const titleInput = document.getElementById('new-reward-title');
    const costInput = document.getElementById('new-reward-cost');
    const iconInput = document.getElementById('new-reward-icon');
    const submitBtn = document.getElementById('btn-save-reward');

    if (reward) {
        title.textContent = "Editar Recompensa";
        idInput.value = reward.id;
        titleInput.value = reward.titulo;
        costInput.value = reward.custo;
        iconInput.value = reward.icone;
        if (submitBtn) submitBtn.textContent = "Salvar Alterações";
    } else {
        title.textContent = "Nova Recompensa";
        idInput.value = '';
        titleInput.value = '';
        costInput.value = '';
        iconInput.value = '';
        if (submitBtn) submitBtn.textContent = "Criar Recompensa";
    }
    modal.classList.add('active');
};

window.confirmDeleteReward = async function (reward) {
    if (confirm(`Tem certeza que deseja excluir permanentemente a recompensa "${reward.titulo}"?`)) {
        try {
            const res = await fetch('/api/todo-gamer/excluir-recompensa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: reward.id })
            });
            const data = await res.json();

            if (data.success) {
                gamerState = data.state;
                updateGamerUI();
                showToast("Recompensa excluída com sucesso!", "success");
            } else {
                showToast(`Erro: ${data.error}`, "warning");
            }
        } catch (err) {
            console.error("Error deleting reward:", err);
            showToast("Erro de conexão ao excluir recompensa.", "warning");
        }
    }
};

// Member Form Submission
window.submitMemberForm = async function () {
    const nome = document.getElementById('member-name-input').value.trim();
    const avatar = document.getElementById('member-avatar-input').value.trim();
    const classe = document.getElementById('member-class-input').value.trim();
    const idade = document.getElementById('member-age-input').value.trim();
    const telefone = document.getElementById('member-phone-input').value.trim();

    if (!nome) {
        showToast("Por favor, preencha o nome do jogador.", "warning");
        return;
    }

    try {
        const res = await fetch('/api/todo-gamer/usuario/cadastrar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nome: nome,
                avatar: avatar,
                classe: classe,
                idade: idade || null,
                telefone: telefone || null
            })
        });
        const data = await res.json();

        if (data.success) {
            gamerState.profiles = data.profiles;
            activeGamerMember = nome; // select the newly created user
            updateGamerUI();
            
            // Hide modal & reset form
            const memberModal = document.getElementById('member-modal');
            if (memberModal) memberModal.classList.remove('active');
            const form = document.getElementById('member-form');
            if (form) form.reset();
            
            showToast("Jogador cadastrado com sucesso! 🎉", "success");
        } else {
            showToast(`Erro: ${data.error}`, "warning");
        }
    } catch (err) {
        console.error("Error creating member:", err);
        showToast("Erro de conexão ao cadastrar jogador.", "warning");
    }
};



