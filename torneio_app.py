from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# Configurar banco de dados
DB_PATH = 'torneio_basquete.db'

def init_db():
    """Inicializa o banco de dados SQLite"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Tabela de inscrições
    c.execute('''CREATE TABLE IF NOT EXISTS inscricoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome_completo TEXT NOT NULL,
        idade INTEGER NOT NULL,
        rg TEXT NOT NULL UNIQUE,
        eh_menor BOOLEAN NOT NULL,
        nome_responsavel TEXT,
        rg_responsavel TEXT,
        data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pendente'
    )''')
    
    conn.commit()
    conn.close()

def validar_rg(rg):
    """Valida formato básico do RG brasileiro"""
    # Remove caracteres especiais
    rg_limpo = re.sub(r'\D', '', rg)
    # Valida se tem entre 7 e 12 dígitos
    return len(rg_limpo) >= 7

def validar_idade(idade):
    """Valida se a idade é um número válido"""
    try:
        idade_int = int(idade)
        return 5 <= idade_int <= 100
    except:
        return False

@app.route('/')
def index():
    """Página principal com o formulário"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Painel administrativo"""
    return render_template('admin.html')

@app.route('/api/inscrever', methods=['POST'])
def inscrever():
    """Endpoint para processar inscrição"""
    try:
        dados = request.json
        
        # Validações
        if not dados.get('nome_completo'):
            return jsonify({'sucesso': False, 'erro': 'Nome completo é obrigatório'}), 400
        
        if not validar_idade(dados.get('idade')):
            return jsonify({'sucesso': False, 'erro': 'Idade inválida'}), 400
        
        if not validar_rg(dados.get('rg')):
            return jsonify({'sucesso': False, 'erro': 'RG inválido'}), 400
        
        idade = int(dados['idade'])
        eh_menor = idade < 18
        
        # Se é menor, validar dados do responsável
        if eh_menor:
            if not dados.get('nome_responsavel'):
                return jsonify({'sucesso': False, 'erro': 'Nome do responsável é obrigatório'}), 400
            if not validar_rg(dados.get('rg_responsavel')):
                return jsonify({'sucesso': False, 'erro': 'RG do responsável inválido'}), 400
        
        # Inserir no banco de dados
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute('''INSERT INTO inscricoes 
                        (nome_completo, idade, rg, eh_menor, nome_responsavel, rg_responsavel)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (dados['nome_completo'].strip(),
                      idade,
                      dados['rg'].strip(),
                      eh_menor,
                      dados.get('nome_responsavel', '').strip() if eh_menor else None,
                      dados.get('rg_responsavel', '').strip() if eh_menor else None))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'sucesso': True, 
                'mensagem': 'Inscrição realizada com sucesso!'
            }), 201
        
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'sucesso': False, 'erro': 'Este RG já foi inscrito'}), 400
    
    except Exception as e:
        return jsonify({'sucesso': False, 'erro': str(e)}), 500

@app.route('/api/inscritos', methods=['GET'])
def listar_inscritos():
    """Endpoint para listar todas as inscrições (para admin)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        c.execute('SELECT * FROM inscricoes ORDER BY data_inscricao DESC')
        inscritos = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(inscritos), 200
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/estatisticas', methods=['GET'])
def obter_estatisticas():
    """Endpoint para obter estatísticas das inscrições"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM inscricoes')
        total = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM inscricoes WHERE eh_menor = 1')
        menores = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_inscritos': total,
            'menores_de_18': menores,
            'maiores_de_18': total - menores
        }), 200
    
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='localhost', port=5000)