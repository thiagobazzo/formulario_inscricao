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
# CONFIGURAÇÃO DO BANCO
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torneio_basquete.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Cria tabela e faz migração simples (adiciona coluna telefone se faltar).
    Isso evita erro 500 quando você tinha um DB antigo sem a coluna.
    """
    conn = get_conn()
    cur = conn.cursor()

    # 1) garante tabela (estrutura nova já inclui telefone)
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

    # 2) migração: se a tabela já existia sem telefone, adiciona
    cur.execute("PRAGMA table_info(inscricoes)")
    cols = [row["name"] for row in cur.fetchall()]
    if "telefone" not in cols:
        cur.execute("ALTER TABLE inscricoes ADD COLUMN telefone TEXT")
        conn.commit()

        # opcional: preencher null antigos com string vazia (evita quebra em formatação)
        cur.execute("UPDATE inscricoes SET telefone = '' WHERE telefone IS NULL")
        conn.commit()

    conn.close()


# ✅ roda ao subir (gunicorn importa o módulo)
init_db()

# ===============================
# HELPERS / VALIDADORES
# ===============================

def limpar_rg(rg) -> str:
    return re.sub(r"\D", "", str(rg or ""))


def validar_rg(rg) -> bool:
    d = limpar_rg(rg)
    return 7 <= len(d) <= 12


def formatar_rg(rg) -> str:
    d = limpar_rg(rg)
    # Formato pedido: NN.NNN.NNN-N (9 dígitos)
    if len(d) == 9:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}-{d[8]}"
    return rg


def limpar_telefone(tel) -> str:
    return re.sub(r"\D", "", str(tel or ""))


def validar_telefone(tel) -> bool:
    d = limpar_telefone(tel)
    # ✅ aceita fixo (10) e celular (11)
    return len(d) in (10, 11)


def formatar_telefone(tel) -> str:
    d = limpar_telefone(tel)
    if len(d) == 10:
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) == 11:
        return f"({d[0:2]}) {d[2:7]}-{d[7:11]}"
    return tel


def validar_idade(idade) -> bool:
    try:
        i = int(idade)
        return 5 <= i <= 100
    except Exception:
        return False


# ===============================
# PDF
# ===============================

def gerar_pdf_comprovante(row: sqlite3.Row) -> BytesIO:
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
    c.drawString(50, y, f"Telefone: {formatar_telefone(row['telefone'] or '')}")
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
        c.drawString(50, y, f"Nome: {row['nome_responsavel'] or ''}")
        y -= 22
        c.drawString(50, y, f"RG: {formatar_rg(row['rg_responsavel'] or '')}")

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 50, "Guarde este comprovante. Apresente no credenciamento se necessário.")
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


# ===============================
# PÁGINAS
# ===============================

@app.route("/")
def index():
    return render_template("index.html")


# opcional
@app.route("/admin")
def admin():
    return render_template("admin.html")


# ===============================
# API
# ===============================

@app.route("/api/inscrever", methods=["POST"])
def inscrever():
    try:
        init_db()  # ✅ garante migração antes do insert

        dados = request.get_json(force=True, silent=True) or {}

        nome = (dados.get("nome_completo") or "").strip()
        idade = dados.get("idade")
        rg = limpar_rg(dados.get("rg"))
        telefone = limpar_telefone(dados.get("telefone"))

        nome_resp = (dados.get("nome_responsavel") or "").strip()
        rg_resp = limpar_rg(dados.get("rg_responsavel"))

        # validações
        if not nome:
            return jsonify({"sucesso": False, "erro": "Nome completo é obrigatório"}), 400

        if not validar_idade(idade):
            return jsonify({"sucesso": False, "erro": "Idade inválida"}), 400

        if not validar_rg(rg):
            return jsonify({"sucesso": False, "erro": "RG inválido"}), 400

        if not validar_telefone(telefone):
            return jsonify({"sucesso": False, "erro": "Telefone inválido. Use (NN) NNNN-NNNN ou (NN) NNNNN-NNNN"}), 400

        idade_int = int(idade)
        eh_menor = 1 if idade_int < 18 else 0

        if eh_menor:
            if not nome_resp:
                return jsonify({"sucesso": False, "erro": "Nome do responsável é obrigatório"}), 400
            if not validar_rg(rg_resp):
                return jsonify({"sucesso": False, "erro": "RG do responsável inválido"}), 400
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
            """, (nome, idade_int, rg, telefone, eh_menor, nome_resp, rg_resp))
            conn.commit()
            new_id = cur.lastrowid
        except sqlite3.IntegrityError:
            return jsonify({"sucesso": False, "erro": "RG já cadastrado. Verifique se você já se inscreveu."}), 409
        finally:
            conn.close()

        return jsonify({
            "sucesso": True,
            "mensagem": "Inscrição realizada com sucesso!",
            "comprovante_url": f"/api/comprovante/{new_id}"
        }), 200

    except Exception as e:
        # log no Render
        print("ERRO /api/inscrever:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/comprovante/<int:inscricao_id>", methods=["GET"])
def comprovante(inscricao_id: int):
    try:
        init_db()

        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM inscricoes WHERE id = ?", (inscricao_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return jsonify({"sucesso": False, "erro": "Inscrição não encontrada"}), 404

        pdf_buffer = gerar_pdf_comprovante(row)
        filename = f"comprovante_inscricao_{inscricao_id}.pdf"
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    except Exception as e:
        print("ERRO /api/comprovante:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/inscritos", methods=["GET"])
def inscritos():
    try:
        init_db()
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, nome_completo, idade, rg, telefone, eh_menor,
                   nome_responsavel, rg_responsavel, data_inscricao, status
            FROM inscricoes
            ORDER BY datetime(data_inscricao) DESC, id DESC
        """)
        rows = cur.fetchall()
        conn.close()

        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "nome_completo": r["nome_completo"],
                "idade": r["idade"],
                "rg": r["rg"],
                "telefone": r["telefone"],
                "eh_menor": int(r["eh_menor"]),
                "nome_responsavel": r["nome_responsavel"],
                "rg_responsavel": r["rg_responsavel"],
                "data_inscricao": r["data_inscricao"],
                "status": r["status"],
            })

        return jsonify(out), 200

    except Exception as e:
        print("ERRO /api/inscritos:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": str(e)}), 500


@app.route("/api/estatisticas", methods=["GET"])
def estatisticas():
    try:
        init_db()
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) AS total FROM inscricoes")
        total = int(cur.fetchone()["total"])

        cur.execute("SELECT COUNT(*) AS menores FROM inscricoes WHERE eh_menor = 1")
        menores = int(cur.fetchone()["menores"])

        conn.close()

        return jsonify({
            "total_inscritos": total,
            "menores_de_18": menores,
            "maiores_de_18": total - menores
        }), 200

    except Exception as e:
        print("ERRO /api/estatisticas:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": str(e)}), 500


# ===============================
# LOCAL
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)


