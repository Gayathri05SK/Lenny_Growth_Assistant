const API_BASES = [
  "http://127.0.0.1:8001/api",
  "http://localhost:8001/api",
  "http://127.0.0.1:8000/api",
  "http://localhost:8000/api",
];

function renderMarkdown(text) {
  if (window.marked && typeof window.marked.parse === "function") {
    return window.marked.parse(text);
  }
  return text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n\n/g, "</p><p>")
    .replace(/^/, "<p>")
    .replace(/$/, "</p>");
}

let currentSessionId = null;

const sessionListEl = document.getElementById("session-list");
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");
const llmSelect = document.getElementById("llm-select");
const artifactPanel = document.getElementById("artifact-panel");
const artifactTitle = document.getElementById("artifact-title");
const artifactBody = document.getElementById("artifact-body");
const copyArtifactBtn = document.getElementById("copy-artifact");
const closeArtifactBtn = document.getElementById("close-artifact");

let activeArtifact = null;

document.getElementById("new-chat-btn").onclick = createSession;
if (closeArtifactBtn && artifactPanel) {
  closeArtifactBtn.onclick = () => artifactPanel.classList.add("hidden");
}
if (copyArtifactBtn) {
  copyArtifactBtn.onclick = async () => {
    if (!activeArtifact) return;
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(activeArtifact.content);
      } else {
        const helper = document.createElement("textarea");
        helper.value = activeArtifact.content;
        document.body.appendChild(helper);
        helper.select();
        document.execCommand("copy");
        helper.remove();
      }
      copyArtifactBtn.textContent = "Copied";
      setTimeout(() => {
        copyArtifactBtn.textContent = "Copy";
      }, 1200);
    } catch (err) {
      copyArtifactBtn.textContent = "Copy failed";
      setTimeout(() => {
        copyArtifactBtn.textContent = "Copy";
      }, 1400);
    }
  };
}
chatForm.onsubmit = handleSend;
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm.requestSubmit();
  }
});

async function api(path, options = {}) {
  let lastError = null;

  for (const apiBase of API_BASES) {
    try {
      const res = await fetch(`${apiBase}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        const detail = err.detail || "Request failed";
        throw new Error(`(${apiBase}) ${detail}`);
      }

      return res.json();
    } catch (err) {
      console.debug(`API fetch failed for ${apiBase}:`, err);
      lastError = err;
    }
  }

  throw lastError || new Error("Request failed");
}

async function loadSessions() {
  const sessions = await api("/sessions");
  sessionListEl.innerHTML = "";
  sessions.forEach((s) => {
    const el = document.createElement("div");
    el.className = "session-item" + (s.id === currentSessionId ? " active" : "");

    const label = document.createElement("span");
    label.className = "session-label";
    label.textContent = s.title;

    const deleteBtn = document.createElement("button");
    deleteBtn.className = "session-delete-btn";
    deleteBtn.textContent = "⋯";
    deleteBtn.title = "Delete this chat";
    deleteBtn.onclick = async (e) => {
      e.stopPropagation();
      if (!confirm("Delete this chat?")) return;
      await api(`/sessions/${s.id}`, { method: "DELETE" });
      if (s.id === currentSessionId) {
        currentSessionId = null;
      }
      await loadSessions();
    };

    el.appendChild(label);
    el.appendChild(deleteBtn);
    el.onclick = () => openSession(s.id);
    sessionListEl.appendChild(el);
  });
  if (!currentSessionId && sessions.length) {
    openSession(sessions[0].id);
  }
}

async function createSession() {
  const session = await api("/sessions", { method: "POST" });
  currentSessionId = session.id;
  messagesEl.innerHTML = "";
  await loadSessions();
}

async function openSession(id) {
  currentSessionId = id;
  const messages = await api(`/sessions/${id}/messages`);
  messagesEl.innerHTML = "";
  if (!messages.length) {
    messagesEl.innerHTML = `<div class="empty-state">Ask a product/growth question, or say "write this as a Ship30for30 essay".</div>`;
  }
  messages.forEach(renderMessage);
  await loadSessions();
}

function renderMessage(msg) {
  const empty = messagesEl.querySelector(".empty-state");
  if (empty) empty.remove();

  const bubble = document.createElement("div");
  bubble.className = `bubble ${msg.role}`;

  if (msg.role === "assistant" && msg.skill_used) {
    const tag = document.createElement("span");
    tag.className = "skill-tag";
    tag.textContent = msg.skill_used === "ship30" ? "Ship30for30 skill" : "Q&A skill";
    bubble.appendChild(tag);
  }

  const content = document.createElement("div");
  content.innerHTML = msg.role === "assistant" ? renderMarkdown(msg.content) : escapeHtml(msg.content);
  bubble.appendChild(content);

  if (msg.artifact_type) {
    const chip = document.createElement("span");
    chip.className = "artifact-chip";
    chip.textContent = `📄 View artifact: ${msg.artifact_title}`;
    chip.onclick = () =>
      showArtifact({ type: msg.artifact_type, title: msg.artifact_title, content: msg.artifact_content });
    bubble.appendChild(chip);
  }

  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function showArtifact(artifact) {
  activeArtifact = artifact;
  artifactTitle.textContent = artifact.title;
  artifactBody.innerHTML = "";
  if (artifact.type === "html") {
    const iframe = document.createElement("iframe");
    iframe.srcdoc = artifact.content;
    artifactBody.appendChild(iframe);
  } else {
    artifactBody.innerHTML = renderMarkdown(artifact.content);
  }
  copyArtifactBtn.textContent = "Copy";
  artifactPanel.classList.remove("hidden");
}

async function handleSend(e) {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  if (!currentSessionId) await createSession();

  renderMessage({ role: "user", content: text });
  chatInput.value = "";

  const thinking = document.createElement("div");
  thinking.className = "bubble assistant";
  thinking.textContent = "Thinking...";
  messagesEl.appendChild(thinking);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const res = await api("/chat", {
      method: "POST",
      body: JSON.stringify({
        session_id: currentSessionId,
        message: text,
        llm_provider: llmSelect.value,
      }),
    });
    thinking.remove();
    renderMessage({
      role: "assistant",
      content: res.reply,
      skill_used: res.skill_used,
      artifact_type: res.artifact?.type,
      artifact_title: res.artifact?.title,
      artifact_content: res.artifact?.content,
    });
    if (res.artifact) showArtifact(res.artifact);
    loadSessions(); // refresh title after first message
  } catch (err) {
    thinking.remove();
    renderMessage({ role: "assistant", content: `⚠️ Error: ${err.message}` });
  }
}

loadSessions();
