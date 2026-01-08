<!doctype html>
<html lang="pt-br">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Torneio de Basquete - Inscrição</title>

  <style>
    body { font-family: Arial, sans-serif; background:#f6f7fb; margin:0; padding:0; }
    .wrap { max-width:720px; margin:40px auto; padding:16px; }
    .card { background:#fff; border-radius:14px; padding:22px; box-shadow:0 6px 20px rgba(0,0,0,.08); }
    h1 { margin:0 0 6px; }
    .sub { color:#666; margin:0 0 18px; }
    label { display:block; font-weight:700; margin:14px 0 6px; }
    input { width:100%; padding:12px; border-radius:10px; border:1px solid #d7dbe7; font-size:16px; }
    input:focus { outline:2px solid #6c7cff30; border-color:#6c7cff; }
    .grid { display:grid; grid-template-columns: 1fr 1fr; gap:14px; }
    .grid-3 { display:grid; grid-template-columns: 1fr 1fr 1fr; gap:14px; }
    @media (max-width:640px){ .grid,.grid-3 { grid-template-columns: 1fr; } }
    .btns { display:flex; gap:10px; margin-top:18px; }
    button { cursor:pointer; border:0; border-radius:12px; padding:12px 16px; font-weight:800; font-size:16px; }
    .btn-primary { background:#5b6cff; color:#fff; flex:1; }
    .btn-secondary { background:#efefef; color:#333; }
    .msg { margin:14px 0 0; padding:12px; border-radius:12px; display:none; }
    .msg.ok { display:block; background:#e7fbef; border:1px solid #b7efc7; color:#0a6b2a; }
    .msg.err { display:block; background:#ffe9e9; border:1px solid #ffc3c3; color:#8d0f0f; }
    .hint { color:#777; font-size:12px; margin-top:4px; }
    .row { margin-top:6px; }
  </style>
</head>

<body>
  <div class="wrap">
    <div class="card">
      <h1>Torneio de Basquete</h1>
      <p class="sub">Ferroviário Futebol Clube — Formulário de Inscrição</p>

      <div id="msg" class="msg"></div>

      <form id="form">
        <label for="nome_completo">Nome Completo *</label>
        <input id="nome_completo" name="nome_completo" type="text" placeholder="Ex: João da Silva" required />

        <div class="grid-3">
          <div>
            <label for="idade">Idade *</label>
            <input id="idade" name="idade" type="number" min="5" max="100" placeholder="Ex: 18" required />
          </div>

          <div>
            <label for="telefone">Telefone *</label>
            <input id="telefone" name="telefone" type="text" placeholder="(11) 99999-9999" required />
            <div class="hint">Aceita fixo (10 dígitos) e celular (11 dígitos).</div>
          </div>

          <div>
            <label for="rg">RG *</label>
            <input id="rg" name="rg" type="text" placeholder="12.345.678-9" required />
          </div>
        </div>

        <div id="resp_box" style="display:none;">
          <h3 style="margin:18px 0 6px;">Dados do Responsável (menor de idade)</h3>

          <div class="grid">
            <div>
              <label for="nome_responsavel">Nome do Responsável *</label>
              <input id="nome_responsavel" name="nome_responsavel" type="text" placeholder="Ex: Maria da Silva" />
            </div>

            <div>
              <label for="rg_responsavel">RG do Responsável *</label>
              <input id="rg_responsavel" name="rg_responsavel" type="text" placeholder="12.345.678-9" />
            </div>
          </div>
        </div>

        <div class="btns">
          <button class="btn-secondary" type="button" id="btn_limpar">Limpar</button>
          <button class="btn-primary" type="submit">Realizar Inscrição</button>
        </div>

        <div class="row" style="margin-top:14px;">
          <a href="/api/exportar-excel" target="_blank">📥 Exportar inscritos (Excel)</a>
        </div>
      </form>
    </div>
  </div>

  <script>
    // -------------------------------
    // Utils de máscara (input)
    // -------------------------------
    function onlyDigits(v) { return (v || "").replace(/\D/g, ""); }

    function maskRG(value) {
      const d = onlyDigits(value).slice(0, 9);
      // NN.NNN.NNN-N
      let out = "";
      if (d.length > 0) out += d.slice(0, 2);
      if (d.length >= 3) out += "." + d.slice(2, 5);
      if (d.length >= 6) out += "." + d.slice(5, 8);
      if (d.length >= 9) out += "-" + d.slice(8, 9);
      return out;
    }

    function maskPhone(value) {
      const d = onlyDigits(value).slice(0, 11);
      if (d.length <= 2) return "(" + d;
      const ddd = d.slice(0, 2);
      const rest = d.slice(2);

      // celular 11 -> 5 + 4 | fixo 10 -> 4 + 4
      if (d.length <= 10) {
        const p1 = rest.slice(0, 4);
        const p2 = rest.slice(4, 8);
        return `(${ddd}) ${p1}${p2 ? "-" + p2 : ""}`;
      } else {
        const p1 = rest.slice(0, 5);
        const p2 = rest.slice(5, 9);
        return `(${ddd}) ${p1}${p2 ? "-" + p2 : ""}`;
      }
    }

    // -------------------------------
    // DOM
    // -------------------------------
    const form = document.getElementById("form");
    const msg = document.getElementById("msg");

    const nome = document.getElementById("nome_completo");
    const idade = document.getElementById("idade");
    const telefone = document.getElementById("telefone");
    const rg = document.getElementById("rg");

    const respBox = document.getElementById("resp_box");
    const nomeResp = document.getElementById("nome_responsavel");
    const rgResp = document.getElementById("rg_responsavel");

    const btnLimpar = document.getElementById("btn_limpar");

    function showMsg(type, text) {
      msg.className = "msg " + type;
      msg.textContent = text;
      msg.style.display = "block";
    }
    function hideMsg() {
      msg.style.display = "none";
      msg.textContent = "";
      msg.className = "msg";
    }

    // Menor de idade
    idade.addEventListener("input", () => {
      const v = parseInt(idade.value || "0", 10);
      if (!isNaN(v) && v > 0 && v < 18) {
        respBox.style.display = "block";
        nomeResp.required = true;
        rgResp.required = true;
      } else {
        respBox.style.display = "none";
        nomeResp.required = false;
        rgResp.required = false;
        nomeResp.value = "";
        rgResp.value = "";
      }
    });

    // Máscaras
    rg.addEventListener("input", () => { rg.value = maskRG(rg.value); });
    rgResp.addEventListener("input", () => { rgResp.value = maskRG(rgResp.value); });
    telefone.addEventListener("input", () => { telefone.value = maskPhone(telefone.value); });

    // Limpar
    btnLimpar.addEventListener("click", () => {
      form.reset();
      respBox.style.display = "none";
      nomeResp.required = false;
      rgResp.required = false;
      hideMsg();
    });

    // Submit -> baixa PDF (resposta é PDF)
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      hideMsg();

      const payload = {
        nome_completo: nome.value,
        idade: idade.value,
        telefone: telefone.value,
        rg: rg.value,
        nome_responsavel: nomeResp.value || null,
        rg_responsavel: rgResp.value || null
      };

      try {
        const res = await fetch("/api/inscrever", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });

        if (!res.ok) {
          const data = await res.json().catch(() => null);
          const erro = data?.erro || "Erro ao processar inscrição.";
          showMsg("err", erro);
          return;
        }

        // resposta é PDF -> baixar
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);

        const a = document.createElement("a");
        a.href = url;

        // tenta pegar nome do arquivo do header
        const cd = res.headers.get("Content-Disposition") || "";
        const match = cd.match(/filename="?([^"]+)"?/i);
        a.download = match ? match[1] : "comprovante_inscricao.pdf";

        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        showMsg("ok", "Inscrição realizada com sucesso! O comprovante (PDF) foi baixado.");

        // opcional: limpar após sucesso
        // form.reset();

      } catch (err) {
        console.error(err);
        showMsg("err", "Falha de conexão com o servidor.");
      }
    });
  </script>
</body>
</html>

