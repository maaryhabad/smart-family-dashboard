from flask import Blueprint, jsonify, request
import datetime

financas_bp = Blueprint('financas', __name__)

@financas_bp.route('/api/financas')
def get_financas():
    from modules.ia_memoria.database import get_all_transactions
    transactions = get_all_transactions()
    
    # Calculate summary dynamically
    income = sum(t["amount"] for t in transactions if t["amount"] > 0 and t.get("pago", 1) == 1)
    expenses = sum(abs(t["amount"]) for t in transactions if t["amount"] < 0 and t.get("pago", 1) == 1)
    savings = income - expenses
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0.0
    
    # Categories breakdown
    categories_map = {
        "Habitação (Aluguel/Contas)": {"value": 0.0, "color": "#ff4d4d"},
        "Educação": {"value": 0.0, "color": "#111827"},
        "Alimentação e Supermercado": {"value": 0.0, "color": "#ff9f43"},
        "Saúde e Planos": {"value": 0.0, "color": "#00d2d3"},
        "Transporte/Combustível": {"value": 0.0, "color": "#54a0ff"},
        "Lazer e Streaming": {"value": 0.0, "color": "#5f27cd"},
        "Outros": {"value": 0.0, "color": "#c8d6e5"}
    }
    
    category_mapping = {
        "habitação": "Habitação (Aluguel/Contas)",
        "habitacao": "Habitação (Aluguel/Contas)",
        "educação": "Educação",
        "educacao": "Educação",
        "alimentação": "Alimentação e Supermercado",
        "alimentacao": "Alimentação e Supermercado",
        "saúde": "Saúde e Planos",
        "saude": "Saúde e Planos",
        "transporte": "Transporte/Combustível",
        "lazer": "Lazer e Streaming",
        "outros": "Outros"
    }
    
    for t in transactions:
        if t["amount"] < 0 and t.get("pago", 1) == 1:
            cat_key = category_mapping.get(t["category"].lower(), "Outros")
            categories_map[cat_key]["value"] += abs(t["amount"])
            
    # Format categories list
    categories_list = []
    total_expense = sum(c["value"] for c in categories_map.values())
    for name, info in categories_map.items():
        percentage = round((info["value"] / total_expense * 100)) if total_expense > 0 else 0
        categories_list.append({
            "name": name,
            "value": round(info["value"], 2),
            "percentage": percentage,
            "color": info["color"]
        })
        
    savings_goals = [
        {"title": "Viagem de Fim de Ano", "target": 8000.00, "current": min(5400.00 + max(0.0, savings - 4079.50), 8000.00), "percentage": 0.0},
        {"title": "Reforma do Escritório", "target": 3500.00, "current": 1200.00, "percentage": 34.2}
    ]
    savings_goals[0]["percentage"] = round((savings_goals[0]["current"] / savings_goals[0]["target"] * 100), 1)
    
    financial_data = {
        "summary": {
            "income": round(income, 2),
            "expenses": round(expenses, 2),
            "savings": round(savings, 2),
            "savings_rate": savings_rate
        },
        "categories": categories_list,
        "savings_goals": savings_goals,
        "recent_transactions": transactions[:10]
    }
    return jsonify(financial_data)

@financas_bp.route('/api/financas/despesas', methods=['GET', 'POST'])
def gerenciar_despesas():
    from modules.ia_memoria.database import get_all_despesas, save_despesa
    
    if request.method == 'POST':
        data = request.json
        save_despesa(
            data['descricao'], 
            data['valor'], 
            data['categoria'], 
            data['dia_vencimento'], 
            data['tipo'], 
            data.get('total_parcelas', 1)
        )
        return jsonify({"success": True, "message": "Despesa registrada!"})
    
    return jsonify(get_all_despesas())

@financas_bp.route('/api/financas/despesas/editar', methods=['POST'])
def editar_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import update_despesa
        update_despesa(
            data['id'], data['descricao'], data['valor'], data['categoria'], 
            data['dia_vencimento'], data['tipo'], data.get('total_parcelas', 1)
        )
        return jsonify({"success": True, "message": "Despesa atualizada!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@financas_bp.route('/api/financas/despesas/excluir', methods=['POST'])
def excluir_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import delete_despesa
        delete_despesa(data['id'])
        return jsonify({"success": True, "message": "Despesa excluída!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@financas_bp.route('/api/financas/despesas/pago', methods=['POST'])
def toggle_pago_despesa():
    data = request.json
    try:
        from modules.ia_memoria.database import toggle_despesa_pago
        toggle_despesa_pago(data['id'], data['pago'])
        return jsonify({"success": True, "message": "Status de pagamento atualizado!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@financas_bp.route('/api/financas/transacoes', methods=['POST'])
def adicionar_transacao_manual():
    data = request.json
    try:
        from modules.ia_memoria.database import save_transaction_to_db
        
        descricao = data['descricao'].strip()
        valor = float(data['valor'])
        tipo = data['tipo'] # 'entrada' or 'saida'
        categoria = data['categoria']
        responsavel = data.get('responsavel', 'Família')
        pago = int(data.get('pago', 1))
        
        if tipo == 'saida':
            valor = -abs(valor)
        else:
            valor = abs(valor)
            
        raw_date = data.get('data') # e.g. "2026-06-22"
        if raw_date:
            try:
                dt = datetime.datetime.strptime(raw_date, '%Y-%m-%d')
                date_str = dt.strftime('%d/%m/%Y')
            except Exception:
                date_str = datetime.date.today().strftime('%d/%m/%Y')
        else:
            date_str = datetime.date.today().strftime('%d/%m/%Y')
            
        save_transaction_to_db(descricao, valor, categoria, date_str, responsavel, pago)
        return jsonify({"success": True, "message": "Transação registrada com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@financas_bp.route('/api/financas/transacoes/excluir', methods=['POST'])
def excluir_transacao_manual():
    data = request.json
    try:
        from modules.ia_memoria.database import delete_transaction_from_db
        delete_transaction_from_db(data['id'])
        return jsonify({"success": True, "message": "Transação excluída com sucesso!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
