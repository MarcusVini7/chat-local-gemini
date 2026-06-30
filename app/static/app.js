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
  summaryResult: null,
  editingNoteId: null,
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
    "cancelNote",
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
    "documentActiveFilter",
    "documentList",
    "documentsPanel",
    "emptyState",
    "escalateFilter",
    "fileInput",
    "generateQuestions",
    "generateSummary",
    "historyList",
    "historyPanel",
    "integrityAlert",
    "checkIntegrityBtn",
    "rebuildPlanBtn",
    "rebuildPlanResult",
    "lastApiCheck",
    "messageList",
    "newNote",
    "newStoreForm",
    "noteContent",
    "noteForm",
    "notesList",
    "notesPanel",
    "noteTitle",
    "notice",
    "openSidebar",
    "questionInput",
    "questionCitations",
    "questionsEmpty",
    "refreshDocuments",
    "refreshHistory",
    "refreshNotes",
    "refreshStores",
    "saveNote",
    "saveSummaryNote",
    "saveToken",
    "sendQuestion",
    "sidebar",
    "storeKeyInput",
    "storeList",
    "storeTenant",
    "storeTitle",
    "statActiveDocuments",
    "statIndexedDocuments",
    "statIntegrityOk",
    "statIntegrityMissing",
    "statNotes",
    "statQueries",
    "suggestedQuestions",
    "summaryCitations",
    "summaryEmpty",
    "summaryMeta",
    "summaryResult",
    "summaryText",
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
  elements.refreshDocuments.addEventListener("click", refreshDocumentData);
  elements.documentActiveFilter.addEventListener("change", loadDocuments);
  elements.checkIntegrityBtn.addEventListener("click", checkStoreIntegrity);
  elements.rebuildPlanBtn.addEventListener("click", showRebuildPlan);
  elements.refreshHistory.addEventListener("click", loadHistory);
  elements.confidenceFilter.addEventListener("change", loadHistory);
  elements.escalateFilter.addEventListener("change", loadHistory);
  elements.generateSummary.addEventListener("click", generateStoreSummary);
  elements.saveSummaryNote.addEventListener("click", saveSummaryAsNote);
  elements.generateQuestions.addEventListener("click", generateSuggestedQuestions);
  elements.newNote.addEventListener("click", () => openNoteEditor());
  elements.refreshNotes.addEventListener("click", loadNotes);
  elements.noteForm.addEventListener("submit", saveNote);
  elements.cancelNote.addEventListener("click", closeNoteEditor);
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
  const previousStoreKey = state.selectedStore
    ? `${state.selectedStore.tenantId}:${state.selectedStore.storeKey}`
    : null;
  const nextStoreKey = store ? `${store.tenantId}:${store.storeKey}` : null;
  state.selectedStore = store;
  if (previousStoreKey !== nextStoreKey) {
    resetNotebookSession();
  }
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
    refreshDocumentData();
  } else if (tabName === "history") {
    loadHistory();
  } else if (tabName === "notes") {
    loadNotes();
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
    result.sourceQuestion = question;
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
      const actions = createElement("div", "message-actions");
      const copyButton = createElement("button", "button ghost copy-answer", "Copiar resposta");
      copyButton.type = "button";
      copyButton.addEventListener("click", () => copyAnswer(copyButton, result.answer));
      const saveButton = createElement("button", "button ghost copy-answer", "Salvar como nota");
      saveButton.type = "button";
      saveButton.addEventListener("click", () => saveChatResponseAsNote(saveButton, result));
      actions.append(copyButton, saveButton);
      heading.append(actions);
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

async function refreshDocumentData() {
  await Promise.all([loadDocuments(), loadStoreStats()]);
}

async function loadStoreStats() {
  if (!state.selectedStore) {
    return;
  }
  const query = new URLSearchParams(selectedStorePayload());
  try {
    const stats = await apiRequest(`/stores/stats?${query}`);
    elements.statActiveDocuments.textContent = stats.documents.active;
    elements.statIndexedDocuments.textContent = stats.documents.indexed;
    elements.statQueries.textContent = stats.queries.total;
    elements.statNotes.textContent = stats.notes.total;
    if (stats.integrity) {
      elements.statIntegrityOk.textContent = stats.integrity.ok;
      elements.statIntegrityMissing.textContent = stats.integrity.missingLocalFile;
    }
  } catch (error) {
    ["statActiveDocuments", "statIndexedDocuments", "statQueries", "statNotes",
     "statIntegrityOk", "statIntegrityMissing"].forEach(
      (id) => {
        elements[id].textContent = "—";
      },
    );
    showNotice(error.message);
  }
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
    active: elements.documentActiveFilter.value,
  });
  try {
    const data = await apiRequest(`/documents?${query}`);
    const docs = Array.isArray(data.items) ? data.items : [];
    renderDocuments(docs);
    // Atualiza alerta de integridade baseado nos dados carregados
    const hasMissing = docs.some(
      (d) => d.active && d.integrityStatus === "missing_local_file",
    );
    elements.integrityAlert.classList.toggle("hidden", !hasMissing);
  } catch (error) {
    setLoading(elements.documentList, error.message);
    showNotice(error.message);
  }
}

async function checkStoreIntegrity() {
  if (!state.selectedStore) {
    return;
  }
  setButtonBusy(elements.checkIntegrityBtn, true, "Verificando...");
  clearNotice();
  try {
    await apiRequest("/stores/integrity-check", {
      method: "POST",
      body: JSON.stringify(selectedStorePayload()),
    });
    showToast("Integridade verificada e atualizada.", "success");
    await refreshDocumentData();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(elements.checkIntegrityBtn, false, "Verificar integridade");
  }
}

async function showRebuildPlan() {
  if (!state.selectedStore) {
    return;
  }
  setButtonBusy(elements.rebuildPlanBtn, true, "Analisando...");
  elements.rebuildPlanResult.classList.add("hidden");
  elements.rebuildPlanResult.replaceChildren();
  clearNotice();
  try {
    const plan = await apiRequest("/stores/rebuild-plan", {
      method: "POST",
      body: JSON.stringify(selectedStorePayload()),
    });
    renderRebuildPlan(plan);
    elements.rebuildPlanResult.classList.remove("hidden");
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(elements.rebuildPlanBtn, false, "Plano de rebuild");
  }
}

function renderRebuildPlan(plan) {
  const container = elements.rebuildPlanResult;
  container.replaceChildren();

  const header = createElement("div", "rebuild-header");
  const statusClass = plan.canRebuildSafely ? "ok" : "missing_local_file";
  const statusText = plan.canRebuildSafely
    ? "✅ Pode reconstruir com segurança"
    : "⚠️ Não é seguro reconstruir agora";
  header.append(
    createElement("strong", `integrity-badge ${statusClass}`, statusText),
    createElement("span", "rebuild-reason", `Motivo: ${plan.reason}`),
  );
  container.append(header);

  if (plan.activeAvailableDocuments.length) {
    const section = createElement("div", "rebuild-section");
    section.append(createElement("h4", "", `Ativos disponíveis (${plan.activeAvailableDocuments.length})`));
    plan.activeAvailableDocuments.forEach((doc) => {
      section.append(createElement("div", "rebuild-item ok", `✓ ${doc.originalFilename}`));
    });
    container.append(section);
  }

  if (plan.activeMissingDocuments.length) {
    const section = createElement("div", "rebuild-section");
    section.append(createElement("h4", "", `Ativos com arquivo ausente (${plan.activeMissingDocuments.length})`));
    plan.activeMissingDocuments.forEach((doc) => {
      section.append(createElement("div", "rebuild-item missing", `✗ ${doc.originalFilename}`));
    });
    container.append(section);
  }

  if (plan.inactiveDocuments.length) {
    const section = createElement("div", "rebuild-section");
    section.append(createElement("h4", "", `Inativos (${plan.inactiveDocuments.length})`));
    plan.inactiveDocuments.forEach((doc) => {
      section.append(createElement("div", "rebuild-item inactive", `— ${doc.originalFilename}`));
    });
    container.append(section);
  }

  const closeBtn = createElement("button", "button ghost", "Fechar plano");
  closeBtn.type = "button";
  closeBtn.addEventListener("click", () => {
    container.classList.add("hidden");
    container.replaceChildren();
  });
  container.append(closeBtn);
}

function renderDocuments(documents) {
  elements.documentList.replaceChildren();
  if (!documents.length) {
    setLoading(elements.documentList, "Nenhum documento nesta base.");
    return;
  }
  documents.forEach((documentItem) => {
    const row = createElement(
      "article",
      `data-row document-row ${documentItem.active ? "" : "inactive"}`.trim(),
    );
    const header = createElement("div", "document-header");
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
    // Integridade no meta
    if (documentItem.integrityStatus && documentItem.integrityStatus !== "unknown") {
      const intMsg = documentItem.integrityMessage
        ? ` — ${documentItem.integrityMessage}`
        : "";
      meta.append(
        createElement("span", "", `Integridade verificada em ${formatDate(documentItem.integrityCheckedAt)}${intMsg}`),
      );
    }
    info.append(meta);
    if (documentItem.notes) {
      info.append(createElement("p", "document-notes-preview", documentItem.notes));
    }

    const badges = createElement("div", "document-badges");
    badges.append(
      createBadge(documentItem.active ? "Ativo" : "Inativo", documentItem.active ? "indexed" : "failed"),
      createBadge(translateStatus(documentItem.status), documentItem.status),
    );
    // Badge de integridade
    if (documentItem.integrityStatus) {
      badges.append(
        createBadge(
          translateIntegrityStatus(documentItem.integrityStatus),
          `integrity-badge ${documentItem.integrityStatus}`,
        ),
      );
    }
    header.append(info, badges);
    row.append(header);

    const details = createElement("div", "document-details hidden");
    const actions = createElement("div", "document-actions");
    const detailsButton = createElement("button", "button secondary", "Detalhes");
    detailsButton.type = "button";
    detailsButton.addEventListener("click", () => {
      toggleDocumentDetails(documentItem, details, detailsButton);
    });

    // Botão verificar integridade individual
    const integrityButton = createElement("button", "button ghost", "Verificar este documento");
    integrityButton.type = "button";
    integrityButton.addEventListener("click", () =>
      checkSingleDocumentIntegrity(documentItem.id, integrityButton),
    );

    const activeButton = createElement(
      "button",
      `button ghost ${documentItem.active ? "danger" : ""}`.trim(),
      documentItem.active ? "Marcar inativo" : "Reativar",
    );
    activeButton.type = "button";
    activeButton.addEventListener("click", () => toggleDocumentActive(documentItem, activeButton));

    const replaceButton = createElement("button", "button ghost", "Substituir");
    replaceButton.type = "button";
    replaceButton.addEventListener("click", () => chooseReplacementFile(documentItem, replaceButton));

    actions.append(detailsButton, integrityButton, activeButton, replaceButton);
    row.append(actions, details);
    elements.documentList.append(row);
  });
}

async function checkSingleDocumentIntegrity(documentId, button) {
  setButtonBusy(button, true, "Verificando...");
  try {
    const result = await apiRequest(`/documents/${documentId}/integrity-check`, {
      method: "POST",
    });
    showToast(
      `${result.originalFilename}: ${translateIntegrityStatus(result.integrityStatus)}`,
      result.integrityStatus === "ok" ? "success" : "error",
    );
    await refreshDocumentData();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(button, false, "Verificar este documento");
  }
}

async function toggleDocumentDetails(documentItem, container, button) {
  if (!container.classList.contains("hidden")) {
    container.classList.add("hidden");
    button.textContent = "Detalhes";
    return;
  }

  setButtonBusy(button, true, "Carregando...");
  try {
    const details = await apiRequest(`/documents/${documentItem.id}`);
    renderDocumentDetails(details, container);
    container.classList.remove("hidden");
    button.textContent = "Fechar detalhes";
  } catch (error) {
    showNotice(error.message);
    button.textContent = "Detalhes";
  } finally {
    button.disabled = false;
  }
}

function renderDocumentDetails(documentItem, container) {
  const grid = createElement("div", "document-detail-grid");
  const values = [
    `ID: ${documentItem.id}`,
    `MIME: ${documentItem.mimeType || "Não informado"}`,
    `SHA256: ${documentItem.sha256}`,
    `Tamanho: ${formatBytes(documentItem.sizeBytes)}`,
    `Criado: ${formatDate(documentItem.createdAt)}`,
    `Indexado: ${formatDate(documentItem.indexedAt)}`,
    `Removido: ${documentItem.deletedAt ? formatDate(documentItem.deletedAt) : "Não"}`,
    `Substituído por: ${documentItem.replacedByDocumentId || "Não"}`,
    `Arquivo local existe: ${documentItem.localFileExists === true ? "Sim" : documentItem.localFileExists === false ? "Não" : "Não verificado"}`,
    `Status de integridade: ${translateIntegrityStatus(documentItem.integrityStatus || "unknown")}`,
    `Integridade verificada em: ${formatDate(documentItem.integrityCheckedAt)}`,
    `Mensagem: ${documentItem.integrityMessage || "—"}`,
  ];
  values.forEach((value) => grid.append(createElement("span", "", value)));

  const editor = createElement("div", "document-note-editor");
  const field = document.createElement("textarea");
  field.rows = 3;
  field.placeholder = "Notas locais sobre este documento";
  field.value = documentItem.notes || "";
  const saveButton = createElement("button", "button primary", "Salvar notas");
  saveButton.type = "button";
  saveButton.addEventListener("click", () => {
    saveDocumentNotes(documentItem.id, field.value, saveButton);
  });
  editor.append(field, saveButton);
  container.replaceChildren(grid, editor);
}

async function saveDocumentNotes(documentId, notes, button) {
  setButtonBusy(button, true, "Salvando...");
  try {
    await apiRequest(`/documents/${documentId}`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
    showToast("Notas do documento atualizadas.", "success");
    await refreshDocumentData();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(button, false, "Salvar notas");
  }
}

async function toggleDocumentActive(documentItem, button) {
  const action = documentItem.active ? "inativar" : "reativar";
  if (
    documentItem.active &&
    !window.confirm(
      "Marcar este documento como inativo? O índice remoto Gemini não será removido.",
    )
  ) {
    return;
  }

  setButtonBusy(button, true, documentItem.active ? "Inativando..." : "Reativando...");
  try {
    if (documentItem.active) {
      await apiRequest(`/documents/${documentItem.id}`, { method: "DELETE" });
    } else {
      await apiRequest(`/documents/${documentItem.id}`, {
        method: "PATCH",
        body: JSON.stringify({ active: true }),
      });
    }
    showToast(`Documento ${action === "inativar" ? "inativado" : "reativado"}.`, "success");
    await refreshDocumentData();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(
      button,
      false,
      documentItem.active ? "Marcar inativo" : "Reativar",
    );
  }
}

function chooseReplacementFile(documentItem, button) {
  const input = document.createElement("input");
  input.type = "file";
  input.className = "hidden";
  input.addEventListener(
    "change",
    async () => {
      if (input.files.length) {
        await replaceDocument(documentItem, input.files[0], button);
      }
      input.remove();
    },
    { once: true },
  );
  document.body.append(input);
  input.click();
}

async function replaceDocument(documentItem, file, button) {
  const formData = new FormData();
  formData.append("file", file);
  setButtonBusy(button, true, "Substituindo...");
  try {
    await apiRequest(`/documents/${documentItem.id}/replace`, {
      method: "POST",
      body: formData,
    });
    showToast("Documento substituído e indexado.", "success");
    await refreshDocumentData();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(button, false, "Substituir");
  }
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
    await refreshDocumentData();
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

async function generateStoreSummary() {
  if (!state.selectedStore) {
    showToast("Selecione uma base para gerar o resumo.", "error");
    return;
  }
  setButtonBusy(elements.generateSummary, true, "Gerando resumo...");
  elements.summaryEmpty.textContent = "Gerando resumo...";
  elements.summaryEmpty.classList.remove("hidden");
  elements.summaryResult.classList.add("hidden");
  clearNotice();

  try {
    const result = await apiRequest("/stores/summary", {
      method: "POST",
      body: JSON.stringify(selectedStorePayload()),
    });
    state.summaryResult = result;
    elements.summaryText.textContent = result.summary || "";
    elements.summaryMeta.replaceChildren(
      createBadge(`Confiança: ${translateConfidence(result.confidence)}`, result.confidence),
      createBadge(result.reason || "Motivo não informado"),
    );
    elements.summaryCitations.replaceChildren(renderCitations(result.citations));
    elements.summaryEmpty.classList.add("hidden");
    elements.summaryResult.classList.remove("hidden");
  } catch (error) {
    state.summaryResult = null;
    elements.summaryEmpty.textContent = "Não foi possível gerar o resumo.";
    showNotice(error.message);
  } finally {
    setButtonBusy(elements.generateSummary, false, "Gerar resumo");
  }
}

async function saveSummaryAsNote() {
  if (!state.summaryResult || !state.selectedStore) {
    return;
  }
  setButtonBusy(elements.saveSummaryNote, true, "Salvando...");
  try {
    await createNote({
      title: `Resumo - ${state.selectedStore.displayName}`.slice(0, 200),
      content: contentWithSources(
        state.summaryResult.summary,
        state.summaryResult.citations,
      ),
      sourceType: "summary",
      sourceQueryId: null,
    });
    showToast("Resumo salvo como nota.", "success");
    await loadNotes();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(elements.saveSummaryNote, false, "Salvar resumo como nota");
  }
}

async function generateSuggestedQuestions() {
  if (!state.selectedStore) {
    showToast("Selecione uma base para gerar perguntas.", "error");
    return;
  }
  setButtonBusy(elements.generateQuestions, true, "Gerando perguntas...");
  elements.questionsEmpty.textContent = "Gerando perguntas...";
  elements.questionsEmpty.classList.remove("hidden");
  elements.suggestedQuestions.classList.add("hidden");
  elements.questionCitations.replaceChildren();
  clearNotice();

  try {
    const result = await apiRequest("/stores/suggest-questions", {
      method: "POST",
      body: JSON.stringify(selectedStorePayload()),
    });
    renderSuggestedQuestions(result.questions);
    elements.questionCitations.replaceChildren(renderCitations(result.citations));
  } catch (error) {
    elements.questionsEmpty.textContent = "Não foi possível gerar perguntas.";
    showNotice(error.message);
  } finally {
    setButtonBusy(elements.generateQuestions, false, "Gerar perguntas");
  }
}

function renderSuggestedQuestions(questions) {
  elements.suggestedQuestions.replaceChildren();
  if (!Array.isArray(questions) || !questions.length) {
    elements.questionsEmpty.textContent = "Nenhuma pergunta foi retornada pelas fontes.";
    elements.questionsEmpty.classList.remove("hidden");
    elements.suggestedQuestions.classList.add("hidden");
    return;
  }

  questions.forEach((question) => {
    const row = createElement("div", "suggested-question");
    const askButton = createElement("button", "button secondary", "Perguntar no chat");
    askButton.type = "button";
    askButton.addEventListener("click", () => {
      switchTab("chat");
      elements.questionInput.value = question;
      elements.questionInput.focus();
    });
    row.append(createElement("span", "", question), askButton);
    elements.suggestedQuestions.append(row);
  });
  elements.questionsEmpty.classList.add("hidden");
  elements.suggestedQuestions.classList.remove("hidden");
}

async function loadNotes() {
  if (!state.selectedStore) {
    return;
  }
  setLoading(elements.notesList, "Carregando notas...");
  const query = new URLSearchParams(selectedStorePayload());
  try {
    const data = await apiRequest(`/notes?${query}`);
    renderNotes(Array.isArray(data.items) ? data.items : []);
  } catch (error) {
    setLoading(elements.notesList, error.message);
    showNotice(error.message);
  }
}

function renderNotes(notes) {
  elements.notesList.replaceChildren();
  if (!notes.length) {
    setLoading(elements.notesList, "Nenhuma nota salva nesta base.");
    return;
  }

  notes.forEach((note) => {
    const item = createElement("article", "note-item");
    item.append(
      createElement("div", "note-title", note.title),
      createElement("p", "note-content", note.content),
      createElement(
        "div",
        "note-meta",
        `${note.sourceType || "manual"} · Atualizada em ${formatDate(note.updatedAt)}`,
      ),
    );
    const actions = createElement("div", "note-actions");
    const editButton = createElement("button", "button ghost", "Editar");
    editButton.type = "button";
    editButton.addEventListener("click", () => openNoteEditor(note));
    const deleteButton = createElement("button", "button ghost danger", "Excluir");
    deleteButton.type = "button";
    deleteButton.addEventListener("click", () => deleteNote(note));
    actions.append(editButton, deleteButton);
    item.append(actions);
    elements.notesList.append(item);
  });
}

function openNoteEditor(note = null) {
  state.editingNoteId = note ? note.id : null;
  elements.noteTitle.value = note ? note.title : "";
  elements.noteContent.value = note ? note.content : "";
  elements.saveNote.textContent = note ? "Atualizar nota" : "Salvar nota";
  elements.noteForm.classList.remove("hidden");
  elements.noteTitle.focus();
}

function closeNoteEditor() {
  state.editingNoteId = null;
  elements.noteForm.reset();
  elements.saveNote.textContent = "Salvar nota";
  elements.noteForm.classList.add("hidden");
}

async function saveNote(event) {
  event.preventDefault();
  if (!state.selectedStore) {
    return;
  }
  const title = elements.noteTitle.value.trim();
  const content = elements.noteContent.value.trim();
  if (!title || !content) {
    showToast("Informe título e conteúdo da nota.", "error");
    return;
  }

  setButtonBusy(elements.saveNote, true, "Salvando...");
  try {
    if (state.editingNoteId) {
      await apiRequest(`/notes/${state.editingNoteId}`, {
        method: "PATCH",
        body: JSON.stringify({ title, content }),
      });
      showToast("Nota atualizada.", "success");
    } else {
      await createNote({
        title,
        content,
        sourceType: "manual",
        sourceQueryId: null,
      });
      showToast("Nota criada.", "success");
    }
    closeNoteEditor();
    await loadNotes();
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(
      elements.saveNote,
      false,
      state.editingNoteId ? "Atualizar nota" : "Salvar nota",
    );
  }
}

async function deleteNote(note) {
  if (!window.confirm(`Excluir a nota "${note.title}"?`)) {
    return;
  }
  try {
    await apiRequest(`/notes/${note.id}`, { method: "DELETE" });
    if (state.editingNoteId === note.id) {
      closeNoteEditor();
    }
    showToast("Nota excluída.", "success");
    await loadNotes();
  } catch (error) {
    showNotice(error.message);
  }
}

async function createNote(note) {
  return apiRequest("/notes", {
    method: "POST",
    body: JSON.stringify({
      ...selectedStorePayload(),
      ...note,
    }),
  });
}

async function saveChatResponseAsNote(button, result) {
  if (!state.selectedStore) {
    return;
  }
  setButtonBusy(button, true, "Salvando...");
  try {
    await createNote({
      title: suggestedNoteTitle(result.sourceQuestion),
      content: contentWithSources(result.answer, result.citations),
      sourceType: "chat",
      sourceQueryId: null,
    });
    showToast("Resposta salva como nota.", "success");
    if (state.activeTab === "notes") {
      await loadNotes();
    }
  } catch (error) {
    showNotice(error.message);
  } finally {
    setButtonBusy(button, false, "Salvar como nota");
  }
}

function selectedStorePayload() {
  return {
    tenantId: state.selectedStore.tenantId,
    storeKey: state.selectedStore.storeKey,
  };
}

function suggestedNoteTitle(question) {
  const title = String(question || "Resposta do chat")
    .split(/\r?\n/, 1)[0]
    .trim();
  return title.slice(0, 120) || "Resposta do chat";
}

function contentWithSources(content, citations) {
  const lines = [String(content || "").trim()];
  if (Array.isArray(citations) && citations.length) {
    lines.push("", "Fontes:");
    citations.forEach((citation) => {
      const snippet = citation.snippet ? `: ${citation.snippet}` : "";
      const page =
        citation.page !== null && citation.page !== undefined
          ? ` (página ${citation.page})`
          : "";
      lines.push(`- ${citation.source || "Fonte não informada"}${page}${snippet}`);
    });
  }
  return lines.join("\n");
}

function resetNotebookSession() {
  state.summaryResult = null;
  state.editingNoteId = null;
  if (!elements.summaryEmpty) {
    return;
  }
  elements.summaryEmpty.textContent = "Nenhum resumo gerado nesta sessão.";
  elements.summaryEmpty.classList.remove("hidden");
  elements.summaryResult.classList.add("hidden");
  elements.summaryText.textContent = "";
  elements.summaryMeta.replaceChildren();
  elements.summaryCitations.replaceChildren();
  elements.questionsEmpty.textContent = "Nenhuma pergunta gerada nesta sessão.";
  elements.questionsEmpty.classList.remove("hidden");
  elements.suggestedQuestions.classList.add("hidden");
  elements.suggestedQuestions.replaceChildren();
  elements.questionCitations.replaceChildren();
  closeNoteEditor();
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
      sourceQuestion: result.sourceQuestion || null,
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

function translateIntegrityStatus(value) {
  return {
    ok: "OK",
    missing_local_file: "Arquivo ausente",
    inactive: "Inativo",
    remote_only: "Apenas remoto",
    unknown: "Não verificado",
    failed: "Falha",
  }[value] || value || "Não verificado";
}
