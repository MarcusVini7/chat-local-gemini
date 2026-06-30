"use strict";

const STORAGE_KEYS = {
  token: "chatLocalGeminiToken",
  tenantId: "selectedTenantId",
  storeKey: "selectedStoreKey",
  chatMode: "chatLocalGeminiChatMode",
  chatPrefix: "chatLocalGeminiMessages",
};

const state = {
  stores: [],
  selectedStore: null,
  activeTab: "chat",
  chatMode: localStorage.getItem(STORAGE_KEYS.chatMode) || "query",
};

const elements = {};

document.addEventListener("DOMContentLoaded", () => {
  cacheElements();
  bindEvents();
  elements.tokenInput.value = localStorage.getItem(STORAGE_KEYS.token) || "";
  updateTokenStatus(elements.tokenInput.value ? "configured" : "empty");
  setChatMode(state.chatMode);
  checkApiStatus();
  loadStores();
});

function cacheElements() {
  [
    "apiStatus",
    "cancelStoreForm",
    "channelSelect",
    "checkApi",
    "clearChat",
    "chatEmpty",
    "chatForm",
    "chatMode",
    "clearToken",
    "closeSidebar",
    "confidenceFilter",
    "customerOptions",
    "displayNameInput",
    "documentList",
    "documentsPanel",
    "emptyState",
    "escalateFilter",
    "fileInput",
    "historyList",
    "historyPanel",
    "lastApiCheck",
    "messageList",
    "newStoreForm",
    "notice",
    "openSidebar",
    "questionInput",
    "refreshDocuments",
    "refreshHistory",
    "refreshStores",
    "saveToken",
    "sendQuestion",
    "sidebar",
    "storeKeyInput",
    "storeList",
    "storeTenant",
    "storeTitle",
    "testToken",
    "tenantIdInput",
    "toggleStoreForm",
    "tokenInput",
    "tokenStatus",
    "toastRegion",
    "uploadButton",
    "uploadForm",
    "uploadStatus",
  ].forEach((id) => {
    elements[id] = document.getElementById(id);
  });

  elements.chatPanel = document.getElementById("chatPanel");
  elements.tabs = Array.from(document.querySelectorAll(".tab"));
}

function bindEvents() {
  elements.saveToken.addEventListener("click", saveToken);
  elements.clearToken.addEventListener("click", clearToken);
  elements.testToken.addEventListener("click", testToken);
  elements.checkApi.addEventListener("click", () => checkApiStatus(true));
  elements.clearChat.addEventListener("click", clearChat);
  elements.refreshStores.addEventListener("click", loadStores);
  elements.toggleStoreForm.addEventListener("click", () => {
    elements.newStoreForm.classList.toggle("hidden");
  });
  elements.cancelStoreForm.addEventListener("click", () => {
    elements.newStoreForm.classList.add("hidden");
  });
  elements.newStoreForm.addEventListener("submit", createStore);
  elements.chatMode.addEventListener("click", handleModeClick);
  elements.channelSelect.addEventListener("change", syncCustomerStyle);
  elements.chatForm.addEventListener("submit", sendQuestion);
  elements.questionInput.addEventListener("keydown", handleQuestionKeydown);
  elements.uploadForm.addEventListener("submit", uploadDocument);
  elements.refreshDocuments.addEventListener("click", loadDocuments);
  elements.refreshHistory.addEventListener("click", loadHistory);
  elements.confidenceFilter.addEventListener("change", loadHistory);
  elements.escalateFilter.addEventListener("change", loadHistory);
  elements.tabs.forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });
  elements.openSidebar.addEventListener("click", () => elements.sidebar.classList.add("open"));
  elements.closeSidebar.addEventListener("click", () => elements.sidebar.classList.remove("open"));
}

async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = localStorage.getItem(STORAGE_KEYS.token);
  if (token) {
    headers.set("X-Internal-Token", token);
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch (error) {
    setApiStatus(false);
    throw new Error(
      "API local indisponível. Verifique se o serviço está rodando em 127.0.0.1:8765.",
    );
  }

  setApiStatus(true);
  const body = await readResponseBody(response);
  if (response.status === 401 || response.status === 403) {
    throw new Error("Token interno ausente ou inválido.");
  }
  if (!response.ok) {
    throw new Error(getErrorDetail(body, response.status));
  }
  return body;
}

async function readResponseBody(response) {
  const text = await response.text();
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    if (response.ok) {
      throw new Error("Resposta inválida recebida da API local.");
    }
    return { detail: text };
  }
}

function getErrorDetail(body, status) {
  if (body && typeof body.detail === "string") {
    return body.detail;
  }
  return `A API retornou HTTP ${status}.`;
}

function setApiStatus(online) {
  elements.apiStatus.textContent = online ? "API online" : "API indisponível";
  elements.apiStatus.classList.toggle("online", online);
  elements.apiStatus.classList.toggle("offline", !online);
  elements.lastApiCheck.textContent = `Verificado às ${new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date())}`;
}

async function checkApiStatus(showResult = false) {
  setButtonBusy(elements.checkApi, true, "Verificando...");
  try {
    const response = await fetch("/health", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    setApiStatus(true);
    if (showResult) {
      showToast("API local online.", "success");
    }
  } catch (error) {
    setApiStatus(false);
    if (showResult) {
      showToast(
        "API local indisponível. Verifique se o serviço está rodando com uvicorn em 127.0.0.1:8765.",
        "error",
      );
    }
  } finally {
    setButtonBusy(elements.checkApi, false, "Verificar API");
  }
}

function showNotice(message) {
  elements.notice.textContent = message;
  elements.notice.classList.remove("hidden");
  showToast(message, "error");
}

function clearNotice() {
  elements.notice.textContent = "";
  elements.notice.classList.add("hidden");
}

function saveToken() {
  const token = elements.tokenInput.value.trim();
  if (token) {
    localStorage.setItem(STORAGE_KEYS.token, token);
    updateTokenStatus("configured");
    showToast("Token configurado.", "success");
  } else {
    localStorage.removeItem(STORAGE_KEYS.token);
    updateTokenStatus("empty");
    showToast("Token removido.");
  }
  elements.tokenInput.value = token;
  clearNotice();
  loadStores();
}

function clearToken() {
  localStorage.removeItem(STORAGE_KEYS.token);
  elements.tokenInput.value = "";
  updateTokenStatus("empty");
  clearNotice();
  showToast("Token removido.");
  loadStores();
}

async function testToken() {
  setButtonBusy(elements.testToken, true, "Testando...");
  clearNotice();
  try {
    await apiRequest("/stores");
    updateTokenStatus("valid");
    showToast("Token válido.", "success");
  } catch (error) {
    if (error.message === "Token interno ausente ou inválido.") {
      updateTokenStatus("invalid");
      showToast("Token inválido ou ausente.", "error");
    } else {
      showNotice(error.message);
    }
  } finally {
    setButtonBusy(elements.testToken, false, "Testar token");
  }
}

function updateTokenStatus(status) {
  const labels = {
    configured: "Token configurado",
    empty: "Token não configurado",
    invalid: "Token inválido ou ausente",
    valid: "Token válido",
  };
  elements.tokenStatus.textContent = labels[status];
  elements.tokenStatus.classList.toggle("valid", status === "valid");
  elements.tokenStatus.classList.toggle("invalid", status === "invalid");
}

async function loadStores() {
  setLoading(elements.storeList, "Carregando bases...");
  clearNotice();
  try {
    const data = await apiRequest("/stores");
    state.stores = Array.isArray(data.items) ? data.items : [];
    renderStores();
    restoreSelectedStore();
  } catch (error) {
    if (error.message === "Token interno ausente ou inválido.") {
      updateTokenStatus("invalid");
    }
    state.stores = [];
    renderStores();
    selectStore(null);
    showNotice(error.message);
  }
}

function renderStores() {
  elements.storeList.replaceChildren();
  if (!state.stores.length) {
    setLoading(elements.storeList, "Nenhuma base encontrada.");
    return;
  }
  state.stores.forEach((store) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "store-item";
    button.dataset.tenantId = store.tenantId;
    button.dataset.storeKey = store.storeKey;
    button.addEventListener("click", () => selectStore(store));

    const avatar = createElement("span", "store-avatar", initials(store.displayName));
    const details = document.createElement("span");
    details.append(
      createElement("span", "store-name", store.displayName),
      createElement("span", "store-key", `${store.tenantId} / ${store.storeKey}`),
    );
    button.append(avatar, details);
    elements.storeList.append(button);
  });
}

function restoreSelectedStore() {
  const tenantId = localStorage.getItem(STORAGE_KEYS.tenantId);
  const storeKey = localStorage.getItem(STORAGE_KEYS.storeKey);
  const stored = state.stores.find(
    (store) => store.tenantId === tenantId && store.storeKey === storeKey,
  );
  selectStore(stored || state.stores[0] || null);
}

function selectStore(store) {
  state.selectedStore = store;
  document.querySelectorAll(".store-item").forEach((item) => {
    item.classList.toggle(
      "active",
      Boolean(
        store &&
          item.dataset.tenantId === store.tenantId &&
          item.dataset.storeKey === store.storeKey,
      ),
    );
  });

  if (!store) {
    elements.storeTitle.textContent = "Chat Local Gemini";
    elements.storeTenant.textContent = "Nenhuma base selecionada";
    elements.emptyState.classList.remove("hidden");
    hidePanels();
    renderStoredChat();
    return;
  }

  localStorage.setItem(STORAGE_KEYS.tenantId, store.tenantId);
  localStorage.setItem(STORAGE_KEYS.storeKey, store.storeKey);
  elements.storeTitle.textContent = store.displayName;
  elements.storeTenant.textContent = `${store.tenantId} / ${store.storeKey}`;
  elements.emptyState.classList.add("hidden");
  elements.sidebar.classList.remove("open");
  renderStoredChat();
  switchTab(state.activeTab);
}

async function createStore(event) {
  event.preventDefault();
  const submitButton = elements.newStoreForm.querySelector('button[type="submit"]');
  setButtonBusy(submitButton, true, "Criando...");
  clearNotice();
  const payload = {
    tenantId: elements.tenantIdInput.value.trim(),
    storeKey: elements.storeKeyInput.value.trim(),
    displayName: elements.displayNameInput.value.trim(),
  };
  try {
    const store = await apiRequest("/stores", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    localStorage.setItem(STORAGE_KEYS.tenantId, store.tenantId);
    localStorage.setItem(STORAGE_KEYS.storeKey, store.storeKey);
    elements.newStoreForm.classList.add("hidden");
    elements.displayNameInput.value = "";
    await loadStores();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(submitButton, false, "Criar");
  }
}

function switchTab(tabName) {
  state.activeTab = tabName;
  elements.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === tabName));
  hidePanels();
  if (!state.selectedStore) {
    elements.emptyState.classList.remove("hidden");
    return;
  }

  const panel = document.querySelector(`[data-panel="${tabName}"]`);
  panel.classList.remove("hidden");
  if (tabName === "documents") {
    loadDocuments();
  } else if (tabName === "history") {
    loadHistory();
  }
}

function hidePanels() {
  document.querySelectorAll("[data-panel]").forEach((panel) => panel.classList.add("hidden"));
}

function handleModeClick(event) {
  const button = event.target.closest("[data-mode]");
  if (button) {
    setChatMode(button.dataset.mode);
  }
}

function setChatMode(mode) {
  state.chatMode = mode === "customer" ? "customer" : "query";
  localStorage.setItem(STORAGE_KEYS.chatMode, state.chatMode);
  elements.chatMode.querySelectorAll("[data-mode]").forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.chatMode);
  });
  elements.customerOptions.classList.toggle("hidden", state.chatMode !== "customer");
}

function syncCustomerStyle() {
  return elements.channelSelect.value === "email"
    ? "atendimento_email"
    : "atendimento_whatsapp";
}

function handleQuestionKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    elements.chatForm.requestSubmit();
  }
}

async function sendQuestion(event) {
  event.preventDefault();
  if (!state.selectedStore) {
    showNotice("Crie ou selecione uma base para começar.");
    return;
  }
  const question = elements.questionInput.value.trim();
  if (!question) {
    return;
  }

  clearNotice();
  appendMessage("user", { answer: question });
  elements.questionInput.value = "";
  setButtonBusy(elements.sendQuestion, true, "Gerando...");
  const loadingMessage = appendLoadingMessage();
  const store = state.selectedStore;
  let path;
  let payload;

  if (state.chatMode === "customer") {
    path = "/answer/customer";
    payload = {
      tenantId: store.tenantId,
      channel: elements.channelSelect.value,
      storeKey: store.storeKey,
      customerMessage: question,
      ticketContext: { lastMessages: [] },
      style: syncCustomerStyle(),
    };
  } else {
    path = "/query";
    payload = {
      tenantId: store.tenantId,
      storeKey: store.storeKey,
      question,
    };
  }

  try {
    const result = await apiRequest(path, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    loadingMessage.remove();
    appendMessage("assistant", result);
  } catch (error) {
    loadingMessage.remove();
    appendMessage("assistant", {
      answer: error.message,
      citations: [],
      confidence: "low",
      reason: "request_failed",
      shouldEscalate: false,
      isError: true,
    });
  } finally {
    setButtonBusy(elements.sendQuestion, false, "Enviar");
    elements.questionInput.focus();
  }
}

function appendLoadingMessage() {
  elements.chatEmpty.classList.add("hidden");
  const message = createElement("div", "message assistant");
  const content = createElement("div", "message-content");
  content.append(
    createElement("div", "message-label", "Resposta"),
    createElement("p", "message-text loading", "Gerando resposta..."),
  );
  message.append(content);
  elements.messageList.append(message);
  scrollMessages();
  return message;
}

function appendMessage(role, result, persist = true) {
  elements.chatEmpty.classList.add("hidden");
  const message = createElement("article", `message ${role}`);
  const content = createElement("div", "message-content");
  if (role === "assistant") {
    const heading = createElement("div", "message-heading");
    heading.append(createElement("div", "message-label", result.isError ? "Erro" : "Resposta"));
    if (!result.isError && result.answer) {
      const copyButton = createElement("button", "button ghost copy-answer", "Copiar resposta");
      copyButton.type = "button";
      copyButton.addEventListener("click", () => copyAnswer(copyButton, result.answer));
      heading.append(copyButton);
    }
    content.append(heading);
  }
  content.append(createElement("p", "message-text", result.answer || ""));

  if (role === "assistant") {
    const meta = createElement("div", "message-meta");
    if (result.confidence) {
      meta.append(createBadge(`Confiança: ${translateConfidence(result.confidence)}`, result.confidence));
    }
    if (result.reason) {
      meta.append(createBadge(result.reason));
    }
    if (result.shouldEscalate) {
      meta.append(createBadge("Escalar para humano", "escalate"));
    }
    content.append(meta);
    content.append(renderCitations(result.citations));
  }

  message.append(content);
  elements.messageList.append(message);
  if (persist) {
    persistChatMessage(role, result);
  }
  scrollMessages();
  return message;
}

function renderCitations(citations) {
  if (!Array.isArray(citations) || !citations.length) {
    return createElement("div", "no-citations", "Nenhuma citação retornada.");
  }
  const details = createElement("details", "citations-details");
  details.open = true;
  details.append(createElement("summary", "", `Citações (${citations.length})`));
  const container = createElement("div", "citations");
  citations.forEach((citation) => {
    const item = createElement("div", "citation");
    item.append(createElement("strong", "", `Fonte: ${citation.source || "Não informada"}`));
    if (citation.snippet) {
      item.append(createElement("span", "", `Trecho: ${citation.snippet}`));
    }
    if (citation.page !== null && citation.page !== undefined) {
      item.append(createElement("span", "", `Página: ${citation.page}`));
    }
    container.append(item);
  });
  details.append(container);
  return details;
}

async function loadDocuments() {
  if (!state.selectedStore) {
    return;
  }
  setLoading(elements.documentList, "Carregando documentos...");
  clearNotice();
  const query = new URLSearchParams({
    tenantId: state.selectedStore.tenantId,
    storeKey: state.selectedStore.storeKey,
  });
  try {
    const data = await apiRequest(`/documents?${query}`);
    renderDocuments(Array.isArray(data.items) ? data.items : []);
  } catch (error) {
    setLoading(elements.documentList, error.message);
    showNotice(error.message);
  }
}

function renderDocuments(documents) {
  elements.documentList.replaceChildren();
  if (!documents.length) {
    setLoading(elements.documentList, "Nenhum documento nesta base.");
    return;
  }
  documents.forEach((documentItem) => {
    const row = createElement("article", "data-row document-row");
    const info = document.createElement("div");
    info.append(createElement("div", "document-name", documentItem.originalFilename));
    const meta = createElement("div", "document-meta");
    meta.append(
      createElement("span", "", formatBytes(documentItem.sizeBytes)),
      createElement("span", "", `Criado em ${formatDate(documentItem.createdAt)}`),
    );
    if (documentItem.indexedAt) {
      meta.append(createElement("span", "", `Indexado em ${formatDate(documentItem.indexedAt)}`));
    }
    info.append(meta);
    row.append(info, createBadge(translateStatus(documentItem.status), documentItem.status));
    elements.documentList.append(row);
  });
}

async function uploadDocument(event) {
  event.preventDefault();
  if (!state.selectedStore || !elements.fileInput.files.length) {
    return;
  }
  const formData = new FormData();
  formData.append("tenantId", state.selectedStore.tenantId);
  formData.append("storeKey", state.selectedStore.storeKey);
  formData.append("file", elements.fileInput.files[0]);
  elements.uploadStatus.textContent = "Enviando e indexando...";
  elements.fileInput.disabled = true;
  setButtonBusy(elements.uploadButton, true, "Processando...");
  clearNotice();

  try {
    const result = await apiRequest("/documents/upload", {
      method: "POST",
      body: formData,
    });
    elements.uploadStatus.textContent = result.status === "indexed" ? "Indexado" : result.status;
    elements.fileInput.value = "";
    await loadDocuments();
  } catch (error) {
    elements.uploadStatus.textContent = "Erro";
    showNotice(error.message);
  } finally {
    elements.fileInput.disabled = false;
    setButtonBusy(elements.uploadButton, false, "Enviar documento");
  }
}

async function loadHistory() {
  if (!state.selectedStore) {
    return;
  }
  setLoading(elements.historyList, "Carregando histórico...");
  clearNotice();
  const query = new URLSearchParams({
    tenantId: state.selectedStore.tenantId,
    storeKey: state.selectedStore.storeKey,
    limit: "50",
  });
  if (elements.confidenceFilter.value) {
    query.set("confidence", elements.confidenceFilter.value);
  }
  if (elements.escalateFilter.value) {
    query.set("shouldEscalate", elements.escalateFilter.value);
  }

  try {
    const data = await apiRequest(`/queries?${query}`);
    renderHistory(Array.isArray(data.items) ? data.items : []);
  } catch (error) {
    setLoading(elements.historyList, error.message);
    showNotice(error.message);
  }
}

function renderHistory(items) {
  elements.historyList.replaceChildren();
  if (!items.length) {
    setLoading(elements.historyList, "Nenhuma consulta encontrada.");
    return;
  }
  items.forEach((item) => {
    const row = createElement("article", "history-item");
    row.append(createElement("div", "history-question", item.question));
    const answer = createElement("p", "history-answer", item.answer);
    row.append(answer);
    if (String(item.answer || "").length > 240) {
      const expandButton = createElement("button", "button ghost history-expand", "Ver mais");
      expandButton.type = "button";
      expandButton.addEventListener("click", () => {
        const expanded = answer.classList.toggle("expanded");
        expandButton.textContent = expanded ? "Ver menos" : "Ver mais";
      });
      row.append(expandButton);
    }
    const meta = createElement("div", "history-meta");
    meta.append(
      createBadge(`Confiança: ${translateConfidence(item.confidence)}`, item.confidence),
      createBadge(item.reason || "Motivo não registrado"),
      createElement("span", "badge", formatDate(item.createdAt)),
    );
    if (item.shouldEscalate) {
      meta.append(createBadge("Escalar para humano", "escalate"));
    }
    row.append(meta, renderCitations(item.citations));
    elements.historyList.append(row);
  });
}

function createBadge(text, variant = "") {
  return createElement("span", `badge ${variant}`.trim(), text);
}

function createElement(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text !== "") {
    element.textContent = text;
  }
  return element;
}

function setLoading(container, text) {
  container.replaceChildren(createElement("div", "list-empty", text));
}

function setButtonBusy(button, busy, label) {
  button.disabled = busy;
  button.textContent = label;
}

function chatStorageKey() {
  if (!state.selectedStore) {
    return null;
  }
  return [
    STORAGE_KEYS.chatPrefix,
    state.selectedStore.tenantId,
    state.selectedStore.storeKey,
  ].join(":");
}

function readStoredMessages() {
  const key = chatStorageKey();
  if (!key) {
    return [];
  }
  try {
    const value = JSON.parse(localStorage.getItem(key) || "[]");
    return Array.isArray(value) ? value : [];
  } catch (error) {
    localStorage.removeItem(key);
    return [];
  }
}

function persistChatMessage(role, result) {
  const key = chatStorageKey();
  if (!key) {
    return;
  }
  const messages = readStoredMessages();
  messages.push({
    role,
    result: {
      answer: String(result.answer || ""),
      citations: Array.isArray(result.citations) ? result.citations : [],
      confidence: result.confidence || null,
      reason: result.reason || null,
      shouldEscalate: Boolean(result.shouldEscalate),
      isError: Boolean(result.isError),
    },
  });
  try {
    localStorage.setItem(key, JSON.stringify(messages.slice(-50)));
  } catch (error) {
    showToast("Não foi possível salvar o chat local.", "error");
  }
}

function renderStoredChat() {
  elements.messageList.replaceChildren(elements.chatEmpty);
  elements.chatEmpty.classList.remove("hidden");
  if (!state.selectedStore) {
    return;
  }
  readStoredMessages().forEach((message) => {
    if (message && ["user", "assistant"].includes(message.role) && message.result) {
      appendMessage(message.role, message.result, false);
    }
  });
}

function clearChat() {
  const key = chatStorageKey();
  if (!key) {
    showToast("Nenhuma base selecionada.", "error");
    return;
  }
  localStorage.removeItem(key);
  renderStoredChat();
  showToast("Chat local limpo.", "success");
}

async function copyAnswer(button, answer) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(answer);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = answer;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.append(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    button.textContent = "Copiado";
    showToast("Resposta copiada.", "success");
    window.setTimeout(() => {
      button.textContent = "Copiar resposta";
    }, 1600);
  } catch (error) {
    showToast("Não foi possível copiar a resposta.", "error");
  }
}

function showToast(message, type = "") {
  const toast = createElement("div", `toast ${type}`.trim());
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.append(createElement("span", "", message));
  const closeButton = createElement("button", "icon-button", "×");
  closeButton.type = "button";
  closeButton.setAttribute("aria-label", "Fechar notificação");
  closeButton.addEventListener("click", () => toast.remove());
  toast.append(closeButton);
  elements.toastRegion.append(toast);
  window.setTimeout(() => toast.remove(), 5000);
}

function scrollMessages() {
  elements.messageList.scrollTop = elements.messageList.scrollHeight;
}

function initials(value) {
  return String(value || "Base")
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join("");
}

function formatBytes(bytes) {
  const value = Number(bytes);
  if (!Number.isFinite(value) || value < 0) {
    return "Tamanho desconhecido";
  }
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  if (!value) {
    return "Data não informada";
  }
  const normalized = String(value).includes("T") ? value : `${value.replace(" ", "T")}Z`;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function translateConfidence(value) {
  return { high: "alta", medium: "média", low: "baixa" }[value] || value;
}

function translateStatus(value) {
  return {
    indexed: "Indexado",
    uploaded: "Enviado",
    failed: "Erro",
  }[value] || value;
}
