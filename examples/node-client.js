const BASE_URL = process.env.CHAT_LOCAL_GEMINI_URL || "http://127.0.0.1:8765";

async function askAnaContext() {
  const response = await fetch(`${BASE_URL}/answer/customer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tenantId: "ihx",
      channel: "whatsapp",
      storeKey: "access-pro",
      customerMessage: "Como cadastro um colaborador?",
      ticketContext: { lastMessages: [] },
      style: "atendimento_whatsapp",
    }),
  });

  if (!response.ok) {
    throw new Error(`chat-local-gemini ${response.status}: ${await response.text()}`);
  }

  return response.json();
}

askAnaContext()
  .then((result) => {
    console.log("Resposta para Ana usar antes de enviar ao cliente:");
    console.log(JSON.stringify(result, null, 2));
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
