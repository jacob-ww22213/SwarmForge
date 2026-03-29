const state = {
  examples: [],
  history: [],
  latestResult: null,
  selectedRunId: null,
};

const exampleSelect = document.querySelector("#example-select");
const taskInput = document.querySelector("#task-input");
const providerSelect = document.querySelector("#provider-select");
const topKInput = document.querySelector("#top-k-input");
const baseUrlInput = document.querySelector("#base-url-input");
const modelInput = document.querySelector("#model-input");
const apiKeyInput = document.querySelector("#api-key-input");
const runButton = document.querySelector("#run-button");
const runStatus = document.querySelector("#run-status");
const emptyState = document.querySelector("#empty-state");
const resultsEl = document.querySelector("#results");
const historyList = document.querySelector("#history-list");
const historyEmpty = document.querySelector("#history-empty");

function listHtml(items) {
  if (!items || items.length === 0) {
    return "<li>暂无内容</li>";
  }
  return items.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("");
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatDateTime(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

async function loadExamples() {
  const response = await fetch("/api/examples");
  const data = await response.json();
  state.examples = data.examples || [];

  for (const example of state.examples) {
    const option = document.createElement("option");
    option.value = example.id;
    option.textContent = example.name;
    exampleSelect.append(option);
  }

  const defaultExample = state.examples[0];
  if (defaultExample) {
    exampleSelect.value = defaultExample.id;
    taskInput.value = defaultExample.content;
  }
}

async function loadHistory() {
  const response = await fetch("/api/history");
  const data = await response.json();
  state.history = data.runs || [];
  renderHistory();
}

function updateStatus(text, isError = false) {
  runStatus.textContent = text;
  runStatus.style.color = isError ? "#b8452d" : "";
}

function renderHistory() {
  if (!state.history.length) {
    historyEmpty.classList.remove("hidden");
    historyList.innerHTML = "";
    return;
  }

  historyEmpty.classList.add("hidden");
  historyList.innerHTML = state.history
    .map(
      (item) => `
        <button class="history-item ${item.run_id === state.selectedRunId ? "active" : ""}" data-run-id="${escapeHtml(item.run_id)}">
          <div class="row-top">
            <strong>${escapeHtml(formatDateTime(item.created_at))}</strong>
            <span class="confidence-chip">${escapeHtml(item.provider_mode || "-")}</span>
          </div>
          <div class="row-meta">
            <span>top-k=${escapeHtml(String(item.top_k ?? "-"))}</span>
            <span>${escapeHtml(item.run_id)}</span>
          </div>
          <p>${escapeHtml(item.task_preview || "无任务预览")}</p>
        </button>
      `
    )
    .join("");
}

function renderProfile(trace) {
  const cards = [
    { label: "语言", value: trace.profile.language },
    { label: "领域", value: trace.profile.domains.join(", ") },
    { label: "动作", value: trace.profile.actions.join(", ") },
    { label: "风险等级", value: trace.profile.risk_level },
  ];
  document.querySelector("#profile-cards").innerHTML = cards
    .map(
      (card) => `
        <article class="profile-card">
          <span class="label">${escapeHtml(card.label)}</span>
          <strong>${escapeHtml(card.value)}</strong>
        </article>
      `
    )
    .join("");
}

function renderRoutedExperts(trace) {
  document.querySelector("#routed-experts").innerHTML = trace.routed
    .map(
      (expert) => `
        <article class="route-card">
          <span class="label">${escapeHtml(expert.key)}</span>
          <strong>${escapeHtml(expert.name)}</strong>
          <p>${escapeHtml(expert.role || "No role")}</p>
          <div class="score">score=${Number(expert.score).toFixed(3)}</div>
        </article>
      `
    )
    .join("");
}

function renderProposals(trace) {
  document.querySelector("#proposal-cards").innerHTML = trace.proposals
    .map(
      (proposal) => `
        <article class="proposal-card">
          <h4>${escapeHtml(proposal.expert_name)}</h4>
          <div class="proposal-meta">
            <span>${escapeHtml(proposal.role)}</span>
            <span class="confidence-chip">conf ${Number(proposal.confidence).toFixed(2)}</span>
          </div>
          <p>${escapeHtml(proposal.summary)}</p>
          <div>
            <strong>Recommendations</strong>
            <ul>${listHtml(proposal.recommendations)}</ul>
          </div>
          <div>
            <strong>Risks</strong>
            <ul>${listHtml(proposal.risks)}</ul>
          </div>
        </article>
      `
    )
    .join("");
}

function renderBaseline(payload) {
  const baseline = payload.baseline;
  const trace = payload.trace;

  if (!baseline) {
    document.querySelector("#baseline-expert-name").textContent = "暂无 baseline";
    document.querySelector("#baseline-expert-score").textContent = "-";
    document.querySelector("#baseline-summary").textContent = "当前结果没有 baseline。";
    document.querySelector("#baseline-recommendations").innerHTML = listHtml([]);
    document.querySelector("#baseline-risks").innerHTML = listHtml([]);
    document.querySelector("#baseline-notes").innerHTML = listHtml([]);
  } else {
    const notes = [
      `置信度 ${Number(baseline.confidence || 0).toFixed(2)}`,
      `建议数 ${baseline.recommendations?.length || 0}`,
      `风险数 ${baseline.risks?.length || 0}`,
    ];
    document.querySelector("#baseline-expert-name").textContent = "Generalist Baseline";
    document.querySelector("#baseline-expert-score").textContent =
      `conf ${Number(baseline.confidence || 0).toFixed(2)}`;
    document.querySelector("#baseline-summary").textContent = baseline.summary || "";
    document.querySelector("#baseline-recommendations").innerHTML = listHtml(baseline.recommendations || []);
    document.querySelector("#baseline-risks").innerHTML = listHtml(baseline.risks || []);
    document.querySelector("#baseline-notes").innerHTML = listHtml(notes);
  }

  document.querySelector("#collaboration-experts-count").textContent = `协作专家数 ${trace.routed.length}`;
  document.querySelector("#collaboration-critique-count").textContent = `focus ${trace.critique.focus.length}`;
  document.querySelector("#collaboration-summary").textContent = trace.aggregate.final_summary;
  document.querySelector("#comparison-consensus").innerHTML = listHtml(trace.aggregate.consensus);
  document.querySelector("#comparison-risks").innerHTML = listHtml(trace.aggregate.key_risks);
}

function renderCritique(trace) {
  document.querySelector("#critic-focus").innerHTML = listHtml(trace.critique.focus);
  document.querySelector("#critic-duplicates").innerHTML = listHtml(trace.critique.duplicates);
  document.querySelector("#critic-checks").innerHTML = listHtml(trace.critique.next_checks);
}

function renderAggregate(trace) {
  document.querySelector("#final-summary").textContent = trace.aggregate.final_summary;
  document.querySelector("#aggregate-consensus").innerHTML = listHtml(trace.aggregate.consensus);
  document.querySelector("#aggregate-next-steps").innerHTML = listHtml(trace.aggregate.next_steps);
  document.querySelector("#aggregate-risks").innerHTML = listHtml(trace.aggregate.key_risks);
}

function renderRawReports(payload) {
  document.querySelector("#console-report").textContent = payload.console_report || "";
  document.querySelector("#markdown-report").textContent = payload.markdown_report || "";
}

function renderResult(payload) {
  state.latestResult = payload;
  state.selectedRunId = payload.run_id || null;
  emptyState.classList.add("hidden");
  resultsEl.classList.remove("hidden");
  renderProfile(payload.trace);
  renderRoutedExperts(payload.trace);
  renderProposals(payload.trace);
  renderBaseline(payload);
  renderCritique(payload.trace);
  renderAggregate(payload.trace);
  renderRawReports(payload);
  renderHistory();
}

async function runDemo() {
  const task = taskInput.value.trim();
  if (!task) {
    updateStatus("请先输入任务描述。", true);
    taskInput.focus();
    return;
  }

  runButton.disabled = true;
  updateStatus("正在运行 workflow...");

  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task,
        provider: providerSelect.value,
        top_k: Number(topKInput.value || 3),
        base_url: baseUrlInput.value.trim() || undefined,
        model: modelInput.value.trim() || undefined,
        api_key: apiKeyInput.value.trim() || undefined,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "运行失败");
    }
    renderResult(payload);
    await loadHistory();
    updateStatus(`运行完成，provider=${payload.provider_mode}`);
  } catch (error) {
    updateStatus(error.message || "运行失败", true);
  } finally {
    runButton.disabled = false;
  }
}

async function loadHistoryRecord(runId) {
  updateStatus("正在载入历史记录...");
  try {
    const response = await fetch(`/api/history/${encodeURIComponent(runId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || "历史记录加载失败");
    }
    renderResult(payload);
    taskInput.value = payload.task || "";
    providerSelect.value = payload.provider_mode || "mock";
    topKInput.value = String(payload.top_k || 3);
    updateStatus(`已载入历史记录 ${payload.run_id}`);
  } catch (error) {
    updateStatus(error.message || "历史记录加载失败", true);
  }
}

exampleSelect.addEventListener("change", () => {
  const selected = state.examples.find((item) => item.id === exampleSelect.value);
  if (selected) {
    taskInput.value = selected.content;
  }
});

historyList.addEventListener("click", (event) => {
  const button = event.target.closest(".history-item");
  if (!button) return;
  const runId = button.dataset.runId;
  if (runId) {
    loadHistoryRecord(runId);
  }
});

runButton.addEventListener("click", runDemo);

Promise.all([loadExamples(), loadHistory()]).catch((error) => {
  updateStatus(`初始化失败：${error.message}`, true);
});
