from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import re

app = Flask(__name__)
CORS(app)

# ===============================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torneio_basquete.db")


def get_conn():
    """Abre conexão SQLite (com row_factory para facilitar dict)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria tabela se não existir."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            idade INTEGER NOT NULL,
            rg TEXT NOT NULL UNIQUE,
            eh_menor BOOLEAN NOT NULL,
            nome_responsavel TEXT,
            rg_responsavel TEXT,
            data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pendente'
        )
    """)
    conn.commit()
    conn.close()


# ✅ IMPORTANTE: roda quando o módulo é importado pelo gunicorn
init_db()

# ===============================
# VALIDADORES
# ===============================

def limpar_rg(rg: str) -> str:
    if rg is None:
        return ""
    return re.sub(r"\D", "", str(rg))


def validar_rg(rg: str) -> bool:
    rg_limpo = limpar_rg(rg)
    return 7 <= len(rg_limpo) <= 12


def validar_idade(idade) -> bool:
    try:
        idade_int = int(idade)
        return 5 <= idade_int <= 100
    except Exception:
        return False


# ===============================
# ROTAS HTML
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    return render_template("admin.html")


# ===============================
# API
# ===============================

@app.route("/api/inscrever", methods=["POST"])
def inscrever():
    """
    Espera JSON:
    {
      "nome_completo": "...",
      "idade": 25,
      "rg": "1234567",
      "nome_responsavel": "... (se menor)",
      "rg_responsavel": "... (se menor)"
    }
    """
    try:
        dados = request.get_json(force=True, silent=True) or {}

        nome_completo = (dados.get("nome_completo") or "").strip()
        idade = dados.get("idade")
        rg = limpar_rg(dados.get("rg"))
        nome_responsavel = (dados.get("nome_responsavel") or "").strip()
        rg_responsavel = limpar_rg(dados.get("rg_responsavel"))

        # Validações básicas
        if not nome_completo:
            return jsonify({"sucesso": False, "erro": "Nome completo é obrigatório"}), 400

        if not validar_idade(idade):
            return jsonify({"sucesso": False, "erro": "Idade inválida"}), 400

        if not validar_rg(rg):
            return jsonify({"sucesso": False, "erro": "RG inválido"}), 400

        idade_int = int(idade)
        eh_menor = 1 if idade_int < 18 else 0

        # Validação de menor
        if eh_menor:
            if not nome_responsavel:
                return jsonify({"sucesso": False, "erro": "Nome do responsável é obrigatório"}), 400
            if not validar_rg(rg_responsavel):
                return jsonify({"sucesso": False, "erro": "RG do responsável inválido"}), 400
        else:
            # padroniza para não gravar lixo
            nome_responsavel = None
            rg_responsavel = None

        # Garantia extra: tabela existe (caso de reboot raro)
        init_db()

        # Inserção
        conn = get_conn()
        cur = conn.cursor()

        try:
            cur.execute("""
                INSERT INTO inscricoes
                    (nome_completo, idade, rg, eh_menor, nome_responsavel, rg_responsavel)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (nome_completo, idade_int, rg, eh_menor, nome_responsavel, rg_responsavel))
            conn.commit()
        except sqlite3.IntegrityError:
            # RG duplicado (UNIQUE)
            return jsonify({"sucesso": False, "erro": "RG já cadastrado. Verifique se você já se inscreveu."}), 409
        finally:
            conn.close()

        return jsonify({"sucesso": True, "mensagem": "Inscrição realizada com sucesso!"}), 200

    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"Erro interno: {str(e)}"}), 500


@app.route("/api/inscritos", methods=["GET"])
def listar_inscritos():
    """Lista inscritos (mais recentes primeiro)."""
    try:
        init_db()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT
                id, nome_completo, idade, rg, eh_menor,
                nome_responsavel, rg_responsavel,
                data_inscricao, status
            FROM inscricoes
            ORDER BY datetime(data_inscricao) DESC, id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        inscritos = []
        for r in rows:
            inscritos.append({
                "id": r["id"],
                "nome_completo": r["nome_completo"],
                "idade": r["idade"],
                "rg": r["rg"],
                "eh_menor": int(r["eh_menor"]),
                "nome_responsavel": r["nome_responsavel"],
                "rg_responsavel": r["rg_responsavel"],
                "data_inscricao": r["data_inscricao"],
                "status": r["status"],
            })

        return jsonify(inscritos), 200

    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao listar inscritos: {str(e)}"}), 500


@app.route("/api/estatisticas", methods=["GET"])
def estatisticas():
    """Retorna total, menores e maiores."""
    try:
        init_db()
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM inscricoes")
        total = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS menores FROM inscricoes WHERE eh_menor = 1")
        menores = cur.fetchone()["menores"]

        maiores = total - menores

        conn.close()

        return jsonify({
            "total_inscritos": int(total),
            "menores_de_18": int(menores),
            "maiores_de_18": int(maiores),
        }), 200

    except Exception as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao calcular estatísticas: {str(e)}"}), 500


# ===============================
# EXECUÇÃO LOCAL
# ===============================
if __name__ == "__main__":
    # Local: python torneio_app.py
    # Produção (Render): gunicorn torneio_app:app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
