from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
import re
from io import BytesIO

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

import pandas as pd

app = Flask(__name__)
CORS(app)

# ==========================================================
# CONFIG
# ==========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torneio_basquete.db")


# ==========================================================
# DB HELPERS
# ==========================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria tabela e aplica migrações simples (ex: adiciona coluna telefone)."""
    conn = get_conn()
    c = conn.cursor()

    # cria tabela se não existir
    c.execute("""
        CREATE TABLE IF NOT EXISTS inscricoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            idade INTEGER NOT NULL,
            telefone TEXT NOT NULL,
            rg TEXT NOT NULL UNIQUE,
            eh_menor INTEGER NOT NULL,
            nome_responsavel TEXT,
            rg_responsavel TEXT,
            data_inscricao TEXT DEFAULT (datetime('now')),
            status TEXT DEFAULT 'pendente'
        )
    """)

    # migração: garantir coluna telefone (caso DB antigo)
    cols = [row[1] for row in c.execute("PRAGMA table_info(inscricoes)").fetchall()]
    if "telefone" not in cols:
        c.execute("ALTER TABLE inscricoes ADD COLUMN telefone TEXT")
        # opcional: setar vazio em registros antigos
        c.execute("UPDATE inscricoes SET telefone = COALESCE(telefone, '')")

    conn.commit()
    conn.close()


# ==========================================================
# VALIDATIONS / FORMATTERS
# ==========================================================
def only_digits(s: str) -> str:
    return re.sub(r"\D", "", (s or ""))


def format_rg(rg: str) -> str:
    d = only_digits(rg)
    # aceita 7 a 12 dígitos, mas formata padrão 9 se tiver 9
    # padrão pedido: NN.NNN.NNN-N (9 dígitos)
    if len(d) == 9:
        return f"{d[0:2]}.{d[2:5]}.{d[5:8]}-{d[8:9]}"
    return d


def format_phone(phone: str) -> str:
    d = only_digits(phone)
    if len(d) == 10:  # fixo
        return f"({d[0:2]}) {d[2:6]}-{d[6:10]}"
    if len(d) == 11:  # celular
        return f"({d[0:2]}) {d[2:7]}-{d[7:11]}"
    return d


def validar_rg(rg: str) -> bool:
    d = only_digits(rg)
    return 7 <= len(d) <= 12


def validar_idade(idade) -> bool:
    try:
        i = int(idade)
        return 5 <= i <= 100
    except:
        return False


def validar_telefone(telefone: str) -> bool:
    d = only_digits(telefone)
    return len(d) in (10, 11)


# ==========================================================
# PDF
# ==========================================================
def gerar_pdf_comprovante(registro: dict) -> BytesIO:
    """
    Gera PDF em memória (BytesIO) com comprovante.
    """
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Cabeçalho
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 2.5 * cm, "Comprovante de Inscrição")

    c.setFont("Helvetica", 12)
    c.drawString(2 * cm, height - 3.3 * cm, "Torneio de Basquete - Ferroviário Futebol Clube")

    # Linha
    c.line(2 * cm, height - 3.7 * cm, width - 2 * cm, height - 3.7 * cm)

    y = height - 5 * cm
    line_h = 0.8 * cm

    def row(label, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, f"{label}:")
        c.setFont("Helvetica", 11)
        c.drawString(6 * cm, y, value if value else "-")
        y -= line_h

    row("Número", str(registro.get("id", "")))
    row("Nome", registro.get("nome_completo", ""))
    row("Idade", str(registro.get("idade", "")))
    row("Telefone", registro.get("telefone", ""))
    row("RG", registro.get("rg", ""))
    row("Data/Hora", registro.get("data_inscricao", ""))
    row("Status", registro.get("status", "pendente"))

    if registro.get("eh_menor") == 1:
        y -= 0.3 * cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Dados do Responsável")
        y -= 0.8 * cm
        row("Responsável", registro.get("nome_responsavel", ""))
        row("RG Responsável", registro.get("rg_responsavel", ""))

    # Rodapé
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(2 * cm, 2 * cm, "Guarde este comprovante. Em caso de dúvidas, fale com a organização.")

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


# ==========================================================
# ROUTES
# ==========================================================
@app.route("/")
def index():
    init_db()
    return render_template("index.html")


@app.route("/api/inscrever", methods=["POST"])
def inscrever():
    try:
        init_db()

        dados = request.get_json(silent=True) or {}

        nome = (dados.get("nome_completo") or "").strip()
        idade = dados.get("idade")
        telefone = (dados.get("telefone") or "").strip()
        rg = (dados.get("rg") or "").strip()

        # validações básicas
        if not nome:
            return jsonify({"sucesso": False, "erro": "Nome completo é obrigatório"}), 400

        if not validar_idade(idade):
            return jsonify({"sucesso": False, "erro": "Idade inválida"}), 400

        if not validar_telefone(telefone):
            return jsonify({"sucesso": False, "erro": "Telefone inválido (use 10 ou 11 dígitos)"}), 400

        if not validar_rg(rg):
            return jsonify({"sucesso": False, "erro": "RG inválido"}), 400

        idade_int = int(idade)
        eh_menor = 1 if idade_int < 18 else 0

        # normalizar/formatar
        telefone_fmt = format_phone(telefone)
        rg_fmt = format_rg(rg)
        rg_digits = only_digits(rg)

        nome_resp = (dados.get("nome_responsavel") or "").strip()
        rg_resp = (dados.get("rg_responsavel") or "").strip()

        if eh_menor == 1:
            if not nome_resp:
                return jsonify({"sucesso": False, "erro": "Nome do responsável é obrigatório"}), 400
            if not validar_rg(rg_resp):
                return jsonify({"sucesso": False, "erro": "RG do responsável inválido"}), 400

        rg_resp_fmt = format_rg(rg_resp) if rg_resp else ""

        conn = get_conn()
        c = conn.cursor()

        # checar duplicidade por RG (considerando só dígitos)
        # como no DB está salvo formatado, fazemos comparação por dígitos
        existing = c.execute("SELECT rg FROM inscricoes").fetchall()
        for row in existing:
            if only_digits(row["rg"]) == rg_digits:
                conn.close()
                return jsonify({"sucesso": False, "erro": "RG já cadastrado"}), 409

        c.execute("""
            INSERT INTO inscricoes
            (nome_completo, idade, telefone, rg, eh_menor, nome_responsavel, rg_responsavel, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            nome,
            idade_int,
            telefone_fmt,
            rg_fmt,
            eh_menor,
            nome_resp if eh_menor == 1 else None,
            rg_resp_fmt if eh_menor == 1 else None,
            "pendente"
        ))

        conn.commit()
        new_id = c.lastrowid

        # buscar registro para gerar comprovante
        row = c.execute("SELECT * FROM inscricoes WHERE id = ?", (new_id,)).fetchone()
        conn.close()

        registro = dict(row)
        # data_inscricao no SQLite pode vir sem timezone; ok
        pdf_buffer = gerar_pdf_comprovante(registro)

        filename = f"comprovante_inscricao_{new_id}.pdf"

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype="application/pdf"
        )

    except Exception as e:
        print("ERRO /api/inscrever:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": "Erro interno no servidor"}), 500


@app.route("/api/inscritos", methods=["GET"])
def listar_inscritos():
    try:
        init_db()
        conn = get_conn()
        c = conn.cursor()
        rows = c.execute("""
            SELECT id, nome_completo, idade, telefone, rg, eh_menor, nome_responsavel, rg_responsavel, data_inscricao, status
            FROM inscricoes
            ORDER BY datetime(data_inscricao) DESC, id DESC
        """).fetchall()
        conn.close()

        return jsonify([dict(r) for r in rows])

    except Exception as e:
        print("ERRO /api/inscritos:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": "Erro interno no servidor"}), 500


@app.route("/api/estatisticas", methods=["GET"])
def estatisticas():
    try:
        init_db()
        conn = get_conn()
        c = conn.cursor()

        total = c.execute("SELECT COUNT(*) AS n FROM inscricoes").fetchone()["n"]
        menores = c.execute("SELECT COUNT(*) AS n FROM inscricoes WHERE eh_menor = 1").fetchone()["n"]
        maiores = total - menores

        conn.close()

        return jsonify({
            "total_inscritos": total,
            "menores_de_18": menores,
            "maiores_de_18": maiores
        })

    except Exception as e:
        print("ERRO /api/estatisticas:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": "Erro interno no servidor"}), 500


@app.route("/api/exportar-excel", methods=["GET"])
def exportar_excel():
    try:
        init_db()
        conn = get_conn()

        df = pd.read_sql_query("""
            SELECT
                id AS "ID",
                nome_completo AS "Nome Completo",
                idade AS "Idade",
                telefone AS "Telefone",
                rg AS "RG",
                CASE WHEN eh_menor = 1 THEN 'Sim' ELSE 'Não' END AS "Menor de Idade",
                COALESCE(nome_responsavel, '') AS "Nome do Responsável",
                COALESCE(rg_responsavel, '') AS "RG do Responsável",
                data_inscricao AS "Data de Inscrição",
                status AS "Status"
            FROM inscricoes
            ORDER BY datetime(data_inscricao) DESC, id DESC
        """, conn)

        conn.close()

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Inscritos")

            ws = writer.sheets["Inscritos"]
            for col in ws.columns:
                max_len = 0
                for cell in col:
                    v = "" if cell.value is None else str(cell.value)
                    if len(v) > max_len:
                        max_len = len(v)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 60)

        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="inscritos_torneio_basquete.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        print("ERRO /api/exportar-excel:", repr(e), flush=True)
        return jsonify({"sucesso": False, "erro": "Erro interno no servidor"}), 500


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)

