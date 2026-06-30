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

## Interface Web Local

Inicie a API:

```bash
cd ~/chat-local-gemini
source .venv/bin/activate

mkdir -p logs
nohup uvicorn app.main:app \
  --host 127.0.0.1 \
  --port 8765 \
  > logs/api.log 2>&1 &

echo $! > .uvicorn.pid
```

Acesse:

```text
http://127.0.0.1:8765/app
```

A interface permite selecionar e criar bases, enviar documentos, consultar o
chat e revisar o histórico. O topo mostra o estado da API, e a sidebar permite
salvar e testar o token interno. A store selecionada e as mensagens locais de
cada store ficam no `localStorage` do navegador.

Na aba **Resumo & Notas**:

- **Gerar resumo** cria uma visão consolidada da base com citações.
- **Gerar perguntas** sugere perguntas fundamentadas que podem ser levadas ao chat.
- **Salvar como nota** registra uma resposta do chat e suas fontes no SQLite local.
- As notas podem ser criadas manualmente, editadas e excluídas pela própria interface.

Se `INTERNAL_API_TOKEN` estiver configurado no `.env`, informe o mesmo token no
campo da interface. Com o token vazio, a interface funciona sem token.

Esta autenticação e o armazenamento no navegador são exclusivos do MVP local.
Mantenha o Uvicorn em `127.0.0.1` e não exponha a interface na internet.

## Rodando como serviço local no Debian

### systemd de usuário

Instale a unit sem usar root:

```bash
cd ~/chat-local-gemini
mkdir -p ~/.config/systemd/user
cp deploy/systemd/chat-local-gemini.service ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable chat-local-gemini
systemctl --user start chat-local-gemini
systemctl --user status chat-local-gemini --no-pager
```

O serviço usa `/home/marcus/chat-local-gemini/.env`, executa o Uvicorn da
`.venv` e escuta somente em `127.0.0.1:8765`.

Comandos operacionais:

```bash
systemctl --user restart chat-local-gemini
systemctl --user stop chat-local-gemini
journalctl --user -u chat-local-gemini -f
```

### Scripts locais

Se não quiser usar systemd:

```bash
cd ~/chat-local-gemini
make start
make status
make restart
make stop
make logs
```

Setup e verificações também estão disponíveis pelo Makefile:

```bash
make setup
make check
make smoke
```

Não execute o serviço systemd e `make start` ao mesmo tempo, pois ambos usam a
porta `8765`. Antes de trocar do modo systemd para scripts:

```bash
systemctl --user stop chat-local-gemini
```

## Autenticação interna

Por padrão, `INTERNAL_API_TOKEN` vazio mantém os endpoints operacionais acessíveis
sem token para desenvolvimento local. Para ativar a proteção:

```bash
INTERNAL_API_TOKEN=$(openssl rand -hex 32)
sed -i "s/^INTERNAL_API_TOKEN=.*/INTERNAL_API_TOKEN=$INTERNAL_API_TOKEN/" .env
export INTERNAL_API_TOKEN
```

Reinicie a API após alterar o `.env`. Envie o token nas chamadas protegidas:

```bash
curl -fsS http://127.0.0.1:8765/stores \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  | python -m json.tool
```

`GET /health` permanece público. Stores, documentos, queries, notas, resumo,
perguntas sugeridas e `/answer/customer` exigem o header quando
`INTERNAL_API_TOKEN` está configurado.

## Endpoints

### Health

```bash
curl http://127.0.0.1:8765/health
```

### Criar store

```bash
curl -X POST http://127.0.0.1:8765/stores \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenantId": "ihx",
    "storeKey": "access-pro",
    "displayName": "Access Pro"
  }'
```

### Listar stores

```bash
curl -fsS "http://127.0.0.1:8765/stores" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/stores?tenantId=marcus" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/stores?tenantId=marcus&storeKey=curso-devops" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
```

### Upload de documento

```bash
curl -X POST http://127.0.0.1:8765/documents/upload \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  -F tenantId=ihx \
  -F storeKey=access-pro \
  -F file=@/caminho/para/Cadastro-de-Colaborador-Access-Pro.pdf
```

### Listar documentos

```bash
curl -fsS "http://127.0.0.1:8765/documents" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus&storeKey=curso-devops" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/documents?tenantId=marcus&storeKey=curso-devops&status=indexed" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
```

### Query interna

```bash
curl -X POST http://127.0.0.1:8765/query \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "tenantId": "ihx",
    "storeKey": "access-pro",
    "question": "Como cadastro um colaborador?"
  }'
```

### Listar histórico de queries

```bash
curl -fsS "http://127.0.0.1:8765/queries" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?tenantId=marcus&storeKey=curso-devops" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?shouldEscalate=true" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?confidence=low" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
curl -fsS "http://127.0.0.1:8765/queries?limit=20" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" | python -m json.tool
```

### Atendimento WhatsApp/e-mail

```bash
curl -X POST http://127.0.0.1:8765/answer/customer \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
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
CHAT_LOCAL_GEMINI_TOKEN="$INTERNAL_API_TOKEN" node examples/node-client.js
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

O smoke test carrega o `.env`, envia `X-Internal-Token` quando configurado e
valida `/health`, as listagens (incluindo notas) e o 404 esperado ao consultar
uma store inexistente. Testes com store/upload/query reais precisam de
`GEMINI_API_KEY` configurada.

### Teste manual da autenticação

Com `INTERNAL_API_TOKEN=` vazio no `.env`, as rotas operacionais funcionam sem
header. Com um token configurado e a API reiniciada:

```bash
curl -sS -o /tmp/no-token.json -w "%{http_code}\n" \
  http://127.0.0.1:8765/stores
cat /tmp/no-token.json

curl -fsS http://127.0.0.1:8765/stores \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  | python -m json.tool
```

A primeira chamada deve retornar `401`; a segunda deve retornar `200`.

## Banco SQLite

Arquivo padrão:

```bash
./data/chat_local_gemini.sqlite
```

Tabelas:

- `stores`
- `documents`
- `queries`
- `notes`

## Observações práticas

- Upload duplicado é detectado por SHA256 dentro da mesma store.
- A indexação aguarda a operação do Gemini File Search terminar.
- Se o cliente pedir humano, `/answer/customer` retorna `shouldEscalate: true` sem chamar Gemini.
- Se a resposta vier sem citação explícita, a confiança cai para `medium`.
- Se as fontes forem insuficientes, a confiança fica `low` e o atendimento deve escalar.
