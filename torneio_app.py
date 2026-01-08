from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
import re
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

app = Flask(__name__)
CORS(app)

# ===============================
# CONFIG / DB
# ===============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torneio_basquete.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            idade INTEGER NOT NULL,
            rg TEXT NOT NULL UNIQUE,
            telefone TEXT NOT NULL,
            eh_menor BOOLEAN NOT NULL,
            nome_responsavel TEXT,
            rg_responsavel TEXT,
            data_inscricao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pendente'
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ===============================
# HELPERS / VALIDATION
# ===============================

def limpar_rg(rg):
    return re.sub(r"\D", "", str(rg or ""))


def validar_rg(rg):
    d = limpar_rg(rg)
    return 7 <= len(d) <= 12


def formatar_rg(rg):
    d = limpar_rg(rg)
    if len(d) == 9:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}-{d[8]}"
    return rg


def limpar_telefone(tel):
    return re.sub(r"\D", "", str(tel or ""))


def validar_telefone(tel):
    d = limpar_telefone(tel)
    return len(d) in (10, 11)  # ✅ fixo ou celular


def formatar_telefone(tel):
    d = limpar_telefone(tel)
    if len(d) == 10:
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) == 11:
        return f"({d[0:2]}) {d[2:7]}-{d[7:11]}"
    return tel


def validar_idade(idade):
    try:
        i = int(idade)
        return 5 <= i <= 100
    except:
        return False


def gerar_pdf(row):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 70, "Comprovante de Inscrição - Torneio de Basquete")

    c.setFont("Helvetica", 12)
    c.drawString(50, h - 95, "Ferroviário FC")
    c.line(50, h - 110, w - 50, h - 110)

    y = h - 150
    c.setFont("Helvetica", 12)

    c.drawString(50, y, f"Nº Inscrição: {row['id']}")
    y -= 22
    c.drawString(50, y, f"Nome: {row['nome_completo']}")
    y -= 22
    c.drawString(50, y, f"Idade: {row['idade']}")
    y -= 22
    c.drawString(50, y, f"RG: {formatar_rg(row['rg'])}")
    y -= 22
    c.drawString(50, y, f"Telefone: {formatar_telefone(row['telefone'])}")
    y -= 22
    c.drawString(50, y, f"Data/Hora: {row['data_inscricao']}")
    y -= 22
    c.drawString(50, y, f"Status: {row['status']}")

    if int(row["eh_menor"]) == 1:
        y -= 30
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Responsável (menor de idade)")
        y -= 22
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Nome: {row['nome_responsavel']}")
        y -= 22
        c.drawString(50, y, f"RG: {formatar_rg(row['rg_responsavel'])}")

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 50, "Guarde este comprovante para o credenciamento.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ===============================
# ROUTES
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/inscrever", methods=["POST"])
def inscrever():
    dados = request.get_json() or {}

    nome = dados.get("nome_completo", "").strip()
    idade = dados.get("idade")
    rg = limpar_rg(dados.get("rg"))
    telefone = limpar_telefone(dados.get("telefone"))

    nome_resp = dados.get("nome_responsavel", "").strip()
    rg_resp = limpar_rg(dados.get("rg_responsavel"))

    if not nome:
        return jsonify({"erro": "Nome obrigatório"}), 400
    if not validar_idade(idade):
        return jsonify({"erro": "Idade inválida"}), 400
    if not validar_rg(rg):
        return jsonify({"erro": "RG inválido"}), 400
    if not validar_telefone(telefone):
        return jsonify({"erro": "Telefone inválido. Use (NN) NNNN-NNNN ou (NN) NNNNN-NNNN"}), 400

    idade = int(idade)
    eh_menor = 1 if idade < 18 else 0

    if eh_menor:
        if not nome_resp or not validar_rg(rg_resp):
            return jsonify({"erro": "Dados do responsável obrigatórios"}), 400
    else:
        nome_resp = None
        rg_resp = None

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO inscricoes
            (nome_completo, idade, rg, telefone, eh_menor, nome_responsavel, rg_responsavel)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome, idade, rg, telefone, eh_menor, nome_resp, rg_resp))
        conn.commit()
        new_id = cur.lastrowid
    except sqlite3.IntegrityError:
        return jsonify({"erro": "RG já cadastrado"}), 409
    finally:
        conn.close()

    return jsonify({
        "sucesso": True,
        "comprovante_url": f"/api/comprovante/{new_id}"
    })


@app.route("/api/comprovante/<int:id>")
def comprovante(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM inscricoes WHERE id=?", (id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return "Não encontrado", 404

    pdf = gerar_pdf(row)
    return send_file(pdf, as_attachment=True,
                     download_name=f"comprovante_{id}.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


