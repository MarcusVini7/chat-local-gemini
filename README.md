# chat-local-gemini

API local leve para consultar uma base Gemini File Search antes da Ana responder clientes no WhatsApp/e-mail.

Sem LLM local, sem Ollama, sem ChromaDB, sem Qdrant, sem vLLM. O Debian roda só FastAPI + SQLite.

## Setup Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
cd ~/chat-local-gemini
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python scripts/init_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Preencha `GEMINI_API_KEY` no `.env`.

## Endpoints

### Health

```bash
curl http://127.0.0.1:8765/health
```

### Criar store

```bash
curl -X POST http://127.0.0.1:8765/stores \
  -H 'Content-Type: application/json' \
  -d '{
    "tenantId": "ihx",
    "storeKey": "access-pro",
    "displayName": "Access Pro"
  }'
```

### Listar stores

```bash
curl -fsS "http://127.0.0.1:8765/stores" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/stores?tenantId=marcus" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/stores?tenantId=marcus&storeKey=curso-devops" | python -m json.tool
```

### Upload de documento

```bash
curl -X POST http://127.0.0.1:8765/documents/upload \
  -F tenantId=ihx \
  -F storeKey=access-pro \
  -F file=@/caminho/para/Cadastro-de-Colaborador-Access-Pro.pdf
```

### Listar documentos

```bash
curl -fsS "http://127.0.0.1:8765/documents" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus&storeKey=curso-devops" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus&storeKey=curso-devops&status=indexed" | python -m json.tool
```

### Query interna

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H 'Content-Type: application/json' \
  -d '{
    "tenantId": "ihx",
    "storeKey": "access-pro",
    "question": "Como cadastro um colaborador?"
  }'
```

### Listar histórico de queries

```bash
curl -fsS "http://127.0.0.1:8765/queries" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?tenantId=marcus&storeKey=curso-devops" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?shouldEscalate=true" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?confidence=low" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?limit=20" | python -m json.tool
```

### Atendimento WhatsApp/e-mail

```bash
curl -X POST http://127.0.0.1:8765/answer/customer \
  -H 'Content-Type: application/json' \
  -d '{
    "tenantId": "ihx",
    "channel": "whatsapp",
    "storeKey": "access-pro",
    "customerMessage": "Como cadastro um colaborador?",
    "ticketContext": {
      "lastMessages": []
    },
    "style": "atendimento_whatsapp"
  }'
```

## Exemplo Node.js

```bash
node examples/node-client.js
```

O retorno esperado para a plataforma:

```json
{
  "answer": "Para cadastrar um colaborador no Access Pro, acesse ...",
  "citations": [
    {
      "source": "Cadastro de Colaborador Access Pro.pdf",
      "page": 3
    }
  ],
  "confidence": "high",
  "shouldEscalate": false,
  "reason": "answer_grounded_in_sources"
}
```

## Smoke test

Em outro terminal, com o servidor rodando:

```bash
cd ~/chat-local-gemini
source .venv/bin/activate
python scripts/smoke_test.py
```

O smoke test valida `/health` e o 404 esperado ao consultar uma store inexistente. Testes com store/upload/query reais precisam de `GEMINI_API_KEY` configurada.

## Banco SQLite

Arquivo padrão:

```bash
./data/chat_local_gemini.sqlite
```

Tabelas:

- `stores`
- `documents`
- `queries`

## Observações práticas

- Upload duplicado é detectado por SHA256 dentro da mesma store.
- A indexação aguarda a operação do Gemini File Search terminar.
- Se o cliente pedir humano, `/answer/customer` retorna `shouldEscalate: true` sem chamar Gemini.
- Se a resposta vier sem citação explícita, a confiança cai para `medium`.
- Se as fontes forem insuficientes, a confiança fica `low` e o atendimento deve escalar.
