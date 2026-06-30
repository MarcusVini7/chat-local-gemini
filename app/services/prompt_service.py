from typing import Any


def query_prompt(question: str) -> str:
    return f"""
Responda em portugues do Brasil usando somente as fontes recuperadas pelo File Search.
Se as fontes nao tiverem informacao suficiente, diga que nao ha informacao suficiente nas fontes.
Nao invente detalhes, links, politicas, passos ou valores.
Pergunta: {question}
""".strip()


def customer_prompt(
    customer_message: str,
    channel: str,
    style: str,
    ticket_context: dict[str, Any],
) -> str:
    last_messages = ticket_context.get("lastMessages", [])
    tone = (
        "Resposta curta, natural e objetiva para WhatsApp."
        if channel == "whatsapp"
        else "Resposta formal, clara e estruturada para e-mail."
    )
    return f"""
Voce responde clientes em portugues do Brasil.
Use somente as fontes recuperadas pelo File Search.
Se a fonte nao tiver informacao suficiente, nao invente: peca esclarecimento ou informe que sera necessario verificar.
Se houver ambiguidade, peca esclarecimento.
Nao exponha detalhes tecnicos de RAG, busca, fontes internas ou modelo.
Nao diga que e uma IA.
Nao use menu numerico.
Nao use tom robotico.
Nao use as frases "Ana por aqui" nem "Voce por aqui".
Prefira a palavra "situacao" em vez de "problema".
{tone}

Estilo: {style}
Historico recente: {last_messages}
Mensagem do cliente: {customer_message}
""".strip()


def customer_requested_human(message: str) -> bool:
    lowered = message.lower()
    terms = [
        "humano",
        "atendente",
        "pessoa",
        "suporte humano",
        "falar com alguem",
        "falar com alguém",
    ]
    return any(term in lowered for term in terms)
