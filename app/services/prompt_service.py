from typing import Any


def query_prompt(question: str) -> str:
    return f"""
Responda em portugues do Brasil usando somente as fontes recuperadas pelo File Search.
Se as fontes nao tiverem informacao suficiente, diga que nao ha informacao suficiente nas fontes.
Nao invente detalhes, links, politicas, passos ou valores.
Nao responda sobre senhas, tokens, chaves, credenciais ou acessos tecnicos sensiveis.
Pergunta: {question}
""".strip()


def store_summary_prompt() -> str:
    return """
Faça um resumo objetivo desta base de conhecimento usando somente as fontes disponíveis.
Organize em:
1. Visão geral
2. Conceitos principais
3. Procedimentos ou práticas importantes
4. Pontos de atenção
Se não houver informação suficiente nas fontes, informe isso claramente.
Não invente informações.
Não exponha senhas, tokens, chaves, credenciais ou acessos técnicos sensíveis.
""".strip()


def suggested_questions_prompt() -> str:
    return """
Com base somente nas fontes disponíveis, gere de 5 a 8 perguntas úteis que um estudante faria sobre este material.
Retorne apenas uma lista objetiva de perguntas, com uma pergunta por linha.
Não invente temas que não estejam nas fontes.
Não gere perguntas sobre senhas, tokens, chaves, credenciais ou acessos técnicos sensíveis.
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
Se a fonte nao tiver informacao suficiente, nao invente.
Se nao houver base clara nas fontes, diga que a situacao precisa ser analisada por um responsavel.
Nao prometa verificar depois se nao houver base nas fontes.
Nunca informe senhas, tokens, chaves, credenciais, acessos root, acessos SSH ou dados sensiveis.
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
