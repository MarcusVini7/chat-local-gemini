const CHAT_LOCAL_GEMINI_URL =
  process.env.CHAT_LOCAL_GEMINI_URL || "http://127.0.0.1:8765";
const CHAT_LOCAL_GEMINI_TOKEN =
  process.env.CHAT_LOCAL_GEMINI_TOKEN || "";
const REQUEST_TIMEOUT_MS = 15000;

async function answerCustomer(payload) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  const headers = { "Content-Type": "application/json" };

  if (CHAT_LOCAL_GEMINI_TOKEN) {
    headers["X-Internal-Token"] = CHAT_LOCAL_GEMINI_TOKEN;
  }

  try {
    const response = await fetch(
      `${CHAT_LOCAL_GEMINI_URL}/answer/customer`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: controller.signal,
      },
    );
    const body = await response.text();

    if (!response.ok) {
      throw new Error(
        `chat-local-gemini request failed: status=${response.status} body=${body}`,
      );
    }

    return JSON.parse(body);
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        `chat-local-gemini request timed out after ${REQUEST_TIMEOUT_MS}ms`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

if (require.main === module) {
  answerCustomer({
    tenantId: "marcus",
    channel: "whatsapp",
    storeKey: "curso-devops",
    customerMessage: "O que é rollback?",
    ticketContext: { lastMessages: [] },
    style: "atendimento_whatsapp",
  })
    .then((result) => {
      console.log(JSON.stringify(result, null, 2));
    })
    .catch((error) => {
      console.error(error.message);
      process.exit(1);
    });
}

module.exports = { answerCustomer };
