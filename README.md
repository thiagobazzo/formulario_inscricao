# 🏀 Sistema de Inscrição - Torneio de Basquete Ferroviário FC

## Descrição
Sistema completo de inscrição para torneio de basquete com formulário responsivo, validações e armazenamento em SQLite.

## Características

✅ **Formulário Inteligente**
- Validação em tempo real
- Campos obrigatórios destacados
- Formatação automática de RG
- Design responsivo (mobile, tablet, desktop)

✅ **Dados de Menores de Idade**
- Campo de responsável aparece automaticamente quando idade < 18
- Validação de dados do responsável
- RG único (evita duplicação)

✅ **Banco de Dados SQLite**
- Armazenamento seguro de dados
- RG como chave única
- Registro de data/hora da inscrição
- Status de inscrição

✅ **API REST**
- Endpoint para inscrições: POST /api/inscrever
- Listagem de inscritos: GET /api/inscritos
- Estatísticas: GET /api/estatisticas

## Estrutura do Projeto

```
torneio-basquete/
├── torneio_app.py           # Aplicação Flask (backend)
├── requirements.txt          # Dependências Python
├── templates/
│   └── index.html           # Formulário (frontend)
└── torneio_basquete.db      # Banco de dados SQLite (criado automaticamente)
```

## Instalação

### 1. Clonar/Copiar os arquivos
Coloque os arquivos na seguinte estrutura:
```
seu-projeto/
├── torneio_app.py
├── requirements.txt
└── templates/
    └── index.html
```

### 2. Criar ambiente virtual (recomendado)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

## Como Executar

### Iniciar o servidor
```bash
python torneio_app.py
```

O servidor estará disponível em: **http://localhost:5000**

Você verá algo como:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Acessar o formulário
Abra seu navegador e acesse:
```
http://localhost:5000
```

## Fluxo de Inscrição

1. **Participante acessa o formulário**
2. **Preenche dados básicos:**
   - Nome completo
   - Idade
   - RG

3. **Se idade < 18:**
   - Sistema mostra campos adicionais
   - Pede dados do responsável legal

4. **Valida dados:**
   - RG deve ter pelo menos 7 dígitos
   - RG não pode ser duplicado
   - Campos obrigatórios

5. **Sucesso!**
   - Dados salvos no SQLite
   - Mensagem de confirmação

## Banco de Dados

### Tabela: inscricoes
```sql
CREATE TABLE inscricoes (
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
```

### Acessar dados do SQLite

**Com Python:**
```python
import sqlite3

conn = sqlite3.connect('torneio_basquete.db')
c = conn.cursor()
c.execute('SELECT * FROM inscricoes')
for row in c.fetchall():
    print(row)
conn.close()
```

**Com CLI:**
```bash
sqlite3 torneio_basquete.db
sqlite> SELECT * FROM inscricoes;
sqlite> SELECT COUNT(*) FROM inscricoes;
```

## APIs Disponíveis

### 1. Realizar Inscrição
```
POST /api/inscrever
Content-Type: application/json

{
    "nome_completo": "João Silva",
    "idade": 25,
    "rg": "123456789",
    "nome_responsavel": null,
    "rg_responsavel": null
}

Resposta (sucesso):
{
    "sucesso": true,
    "mensagem": "Inscrição realizada com sucesso!"
}
```

### 2. Listar Inscritos
```
GET /api/inscritos

Resposta:
[
    {
        "id": 1,
        "nome_completo": "João Silva",
        "idade": 25,
        "rg": "123456789",
        "eh_menor": 0,
        "data_inscricao": "2024-01-15 10:30:45",
        "status": "pendente"
    }
]
```

### 3. Obter Estatísticas
```
GET /api/estatisticas

Resposta:
{
    "total_inscritos": 50,
    "menores_de_18": 12,
    "maiores_de_18": 38
}
```

## Compartilhar o Link

Para compartilhar com participantes por WhatsApp ou email:

**URL Local (na sua rede):**
```
http://seu-ip-local:5000
```

**Exemplo:**
- Se seu IP é 192.168.1.100:
- Link: http://192.168.1.100:5000

**Para hospedar na internet (recomendado):**
- Use Heroku, PythonAnywhere, ou servidor próprio
- Substitua localhost pelo domínio

## Validações Implementadas

✅ RG deve ter pelo menos 7 dígitos
✅ RG não pode ser duplicado
✅ Idade deve ser entre 5 e 100 anos
✅ Nome completo obrigatório
✅ Responsável obrigatório para menores de 18
✅ Formatação automática de RG (remove caracteres especiais)

## Segurança

- Validação de entrada no frontend e backend
- Dados sanitizados antes de armazenar
- RG como chave única (evita duplicação)
- Sem autenticação (aberto para inscrições públicas)

**Para produção, adicione:**
- Rate limiting para evitar spam
- CAPTCHA
- Confirmação de email/WhatsApp
- Autenticação para acesso ao painel admin

## Troubleshooting

### "Porta 5000 já está em uso"
```bash
# Altere a porta no torneio_app.py
app.run(debug=True, host='localhost', port=5001)
```

### "Módulo Flask não encontrado"
```bash
pip install -r requirements.txt
```

### "Banco de dados corrompido"
```bash
# Delete o arquivo e deixe recriar
rm torneio_basquete.db
python torneio_app.py
```

## Próximas Melhorias

- [ ] Painel admin com senha
- [ ] Exportar inscritos para Excel/CSV
- [ ] Integração com WhatsApp para confirmação
- [ ] Upload de comprovante (foto do RG)
- [ ] Categorias de idade (Sub-12, Sub-15, Sub-18, Adulto)
- [ ] Email de confirmação
- [ ] Limite de vagas
- [ ] Sistema de equipes

## Suporte

Em caso de dúvidas, revise:
1. Se Flask está instalado corretamente
2. Se a porta 5000 está disponível
3. Se os arquivos estão na pasta correta
4. Verifique o console para mensagens de erro

---

**Versão:** 1.0
**Última atualização:** Janeiro 2025
**Desenvolvido para:** Ferroviário Futebol Clube
