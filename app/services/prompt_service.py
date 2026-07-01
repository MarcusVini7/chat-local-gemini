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


def study_guide_prompt(topic: str, level: str) -> str:
    return f"""
Com base somente nas fontes disponíveis, crie um guia de estudos sobre "{topic}" (nível {level}).
Estruture em 3 seções: 1. Conceitos-chave (bullets objetivos) 2. Exercícios práticos (3 perguntas) 3. Referências (cite os trechos-fonte usados).
Não invente conteúdo que não esteja nas fontes.
Se as fontes não cobrirem o tópico, diga isso claramente.
Não exponha senhas, tokens, chaves, credenciais ou acessos técnicos sensíveis.
""".strip()


def faq_prompt(n_questions: int) -> str:
    return f"""
A partir das fontes disponíveis, identifique os principais tópicos e gere um FAQ com {n_questions} perguntas e respostas.
Formato: "P: pergunta" seguido de "R: resposta objetiva baseada nas fontes", uma dupla por bloco.
Não invente perguntas sobre temas ausentes das fontes.
Não exponha senhas, tokens, chaves, credenciais ou acessos técnicos sensíveis.
""".strip()


def briefing_prompt(audience: str) -> str:
    return f"""
Resuma as fontes disponíveis em um briefing executivo para público {audience}, em até 350 palavras.
Seções obrigatórias: Contexto, Principais pontos (3 a 5 bullets), Implicações, Próximos passos.
Seja direto, sem introduções ou repetições.
Não invente informações fora das fontes.
Não exponha senhas, tokens, chaves, credenciais ou acessos técnicos sensíveis.
""".strip()


def timeline_prompt() -> str:
    return """
Extraia das fontes todos os eventos com datas ou períodos identificáveis e organize-os em uma timeline cronológica.
Agrupe por período (mês/ano) e resuma em 1-2 frases o que ocorreu em cada um.
Formato: "PERÍODO -> resumo do evento", em ordem cronológica.
Se não houver datas nas fontes, diga isso explicitamente e não invente nenhuma.
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
