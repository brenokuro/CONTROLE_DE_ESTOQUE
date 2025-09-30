
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
from io import BytesIO
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET')
if not app.secret_key:
    raise ValueError("SESSION_SECRET environment variable must be set")

app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

users = {
    'bar1': generate_password_hash('usuariocomum'),
    'bar2': generate_password_hash('usuariocomum'),
    'bar3': generate_password_hash('usuariocomum'),
    'adminriver': generate_password_hash('admin123river')
}

inventory = {
    'Cerveja Lata': {'quantity': 50, 'unit': 'unidades'},
    'Cerveja Garrafa': {'quantity': 30, 'unit': 'unidades'},
    'Refrigerante': {'quantity': 40, 'unit': 'unidades'},
    'Água': {'quantity': 60, 'unit': 'unidades'},
    'Gelo': {'quantity': 8, 'unit': 'kg'},
    'Limão': {'quantity': 3, 'unit': 'kg'},
    'Energético': {'quantity': 15, 'unit': 'unidades'},
    'Taças': {'quantity': 20, 'unit': 'unidades'},
    'Copos Descartáveis': {'quantity': 100, 'unit': 'unidades'},
    'Guardanapos': {'quantity': 200, 'unit': 'unidades'}
}

movements_history = []

## ...existing code...

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuário ou senha inválidos'})
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])

@app.route('/api/inventory')
def get_inventory():
    if 'username' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    low_stock_items = []
    is_admin = session['username'] == 'adminriver'
    if is_admin:
        low_stock_items = [item for item, data in inventory.items() if data['quantity'] <= 5]
    
    return jsonify({
        'inventory': inventory,
        'low_stock_items': low_stock_items,
        'is_admin': is_admin
    })

@app.route('/api/update_inventory', methods=['POST'])
def update_inventory():
    if 'username' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    data = request.get_json()
    item = data.get('item')
    new_quantity = data.get('quantity')
    
    if item not in inventory:
        return jsonify({'success': False, 'message': 'Item não encontrado'}), 400
    
    try:
        new_quantity = int(new_quantity)
        if new_quantity < 0:
            return jsonify({'success': False, 'message': 'Quantidade não pode ser negativa'}), 400
    except (TypeError, ValueError):
        return jsonify({'success': False, 'message': 'Quantidade inválida'}), 400
    
    old_quantity = inventory[item]['quantity']
    inventory[item]['quantity'] = new_quantity
    
    if new_quantity < old_quantity:
        difference = old_quantity - new_quantity
        movements_history.append({
            'item': item,
            'quantity': difference,
            'user': session['username'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'saída'
        })
    elif new_quantity > old_quantity:
        difference = new_quantity - old_quantity
        movements_history.append({
            'item': item,
            'quantity': difference,
            'user': session['username'],
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': 'entrada'
        })
    
    return jsonify({'success': True})

@app.route('/api/report')
def generate_report():
    if 'username' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    title = Paragraph("Relatório de Saída de Itens do Estoque", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    date_info = Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}", styles['Normal'])
    elements.append(date_info)
    elements.append(Spacer(1, 12))
    
    saidas = [m for m in movements_history if m['type'] == 'saída']
    
    if saidas:
        data = [['Data', 'Hora', 'Item', 'Quantidade', 'Usuário']]
        
        for movement in saidas:
            data.append([
                movement['date'],
                movement['time'],
                movement['item'],
                str(movement['quantity']),
                movement['user']
            ])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
    else:
        no_data = Paragraph("Nenhuma movimentação registrada até o momento.", styles['Normal'])
        elements.append(no_data)
    
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"relatorio_estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')

@app.route('/api/create_item', methods=['POST'])
def create_item():
    if 'username' not in session:
        return jsonify({'error': 'Não autenticado'}), 401
    
    # Somente o admin pode criar novos produtos
    if session['username'] != 'adminriver':
        return jsonify({'success': False, 'message': 'Apenas administradores podem criar novos itens'}), 403

    data = request.get_json()
    item = data.get('item')
    quantity = data.get('quantity')
    unit = data.get('unit')

    if not item or not quantity or not unit:
        return jsonify({'success': False, 'message': 'Preencha todos os campos (item, quantity, unit)'}), 400

    if item in inventory:
        return jsonify({'success': False, 'message': 'Item já existe no estoque'}), 400

    try:
        quantity = int(quantity)
        if quantity < 0:
            return jsonify({'success': False, 'message': 'Quantidade não pode ser negativa'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Quantidade inválida'}), 400

    inventory[item] = {'quantity': quantity, 'unit': unit}

    # Registrar histórico como "entrada"
    movements_history.append({
        'item': item,
        'quantity': quantity,
        'user': session['username'],
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'type': 'entrada'
    })

    return jsonify({'success': True, 'message': f'Item "{item}" criado com sucesso!'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)