const T = {
  en: {
    placeholder: "Describe the client's problem or enter a ticket ID (IT/EN)...",
    send: "Send",
    toDark: "Switch to dark theme",
    toLight: "Switch to light theme",
    you: "You",
    bot: "Miner",
    searching: "Searching...",
    error: "Error: ",
    status: "Status",
    assignee: "Assignee",
    issueType: "Issue type",
    suggestedIssueType: "Suggested issue type",
    suggestedAssignees: "Suggested assignees",
    basedOn: "based on",
    noCopilot: cmd => "Copilot CLI is not installed. Install it with: " + cmd + " ?",
    noNpm: "npm was not found. Install Node.js first (https://nodejs.org).",
    install: "Yes, install",
    installing: "Installing...",
    needsLogin: "Copilot is installed, but you are not signed in.",
    login: "Sign in",
    openLogin: "Open the sign-in page and enter the code:",
    waitingAuth: "Waiting for authorization...",
    preparingCode: "Preparing sign-in code...",
    serverDown: "Server is not reachable. Start sip-chatbot-web.py.",
    errors: {
      npm_missing: () => "npm was not found. Install Node.js (https://nodejs.org) and try again.",
      install_failed: c => "Installation failed (code " + c + ").",
      not_in_path: () => "Copilot is installed but not in PATH. Restart the terminal and the server.",
      login_failed: c => "Sign-in failed (code " + c + ").",
      not_ready: () => "Copilot is not ready (install or sign-in).",
    },
  },
  it: {
    placeholder: "Descrivi il problema del cliente o inserisci l'ID del ticket (IT/EN)...",
    send: "Invia",
    toDark: "Passa al tema scuro",
    toLight: "Passa al tema chiaro",
    you: "Tu",
    bot: "Miner",
    searching: "Ricerca in corso...",
    error: "Errore: ",
    status: "Stato",
    assignee: "Assegnatario",
    issueType: "Tipo di issue",
    suggestedIssueType: "Tipo di issue suggerito",
    suggestedAssignees: "Assegnatari suggeriti",
    basedOn: "in base a",
    noCopilot: cmd => "Copilot CLI non è installato. Vuoi installarlo con: " + cmd + " ?",
    noNpm: "npm non trovato. Installa prima Node.js (https://nodejs.org).",
    install: "Sì, installa",
    installing: "Installazione in corso...",
    needsLogin: "Copilot è installato, ma non hai effettuato l'accesso.",
    login: "Accedi",
    openLogin: "Apri la pagina di accesso e inserisci il codice:",
    waitingAuth: "In attesa dell'autorizzazione...",
    preparingCode: "Preparazione del codice di accesso...",
    serverDown: "Server non raggiungibile. Avvia sip-chatbot-web.py.",
    errors: {
      npm_missing: () => "npm non trovato. Installa Node.js (https://nodejs.org) e riprova.",
      install_failed: c => "Installazione non riuscita (codice " + c + ").",
      not_in_path: () => "Copilot è installato ma non è nel PATH. Riavvia il terminale e il server.",
      login_failed: c => "Accesso non riuscito (codice " + c + ").",
      not_ready: () => "Copilot non è pronto (installazione o accesso).",
    },
  },
};

const log = document.getElementById("log");
const form = document.getElementById("form");
const entry = document.getElementById("entry");
const btn = document.getElementById("btn");
const setup = document.getElementById("setup");
const langButtons = document.querySelectorAll("#lang button");
const themeBtn = document.getElementById("theme");
const HELMET_SVG =
  '<svg viewBox="0 0 24 24" aria-hidden="true">' +
  '<path class="beam" d="M12 7V4.2M8.2 7.8 6.6 5.7M15.8 7.8l1.6-2.1"/>' +
  '<path class="shell" d="M5 16.5a7 7 0 0 1 14 0z"/>' +
  '<rect class="shell" x="2.5" y="16.5" width="19" height="2.8" rx="1.4"/>' +
  '<circle class="lamp" cx="12" cy="12.6" r="2.5"/></svg>';
let lang = T[localStorage.getItem("lang")] ? localStorage.getItem("lang") : "en";
let lastStatus = null;
let ready = false;
let busy = false;

const t = () => T[lang];

function errorText(e) {
  if (!e) return "";
  if (typeof e === "string") return e;
  const f = t().errors[e.key];
  return f ? f(e.code) : (e.detail || e.key);
}

function setLang(next) {
  lang = next;
  localStorage.setItem("lang", lang);
  document.documentElement.lang = lang;
  for (const b of langButtons) b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
  entry.placeholder = t().placeholder;
  btn.textContent = t().send;
  updateThemeLabel();
  if (lastStatus) renderSetup(lastStatus);
  else if (!setup.hidden) setup.replaceChildren(el("p", t().serverDown, "err"));
}

function updateThemeLabel() {
  const label = document.documentElement.dataset.theme === "dark" ? t().toLight : t().toDark;
  themeBtn.title = label;
  themeBtn.setAttribute("aria-label", label);
}

themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("theme", next);
  updateThemeLabel();
});

for (const b of langButtons) b.addEventListener("click", () => setLang(b.dataset.lang));

function el(tag, text, cls) {
  const e = document.createElement(tag);
  if (text) e.textContent = text;
  if (cls) e.className = cls;
  return e;
}

function action(label, path) {
  const b = el("button", label);
  b.type = "button";
  b.onclick = async () => {
    b.disabled = true;
    await fetch(path, { method: "POST" });
    refresh();
  };
  return b;
}

function renderSetup(s) {
  setup.replaceChildren();
  if (s.state === "no_copilot") {
    setup.append(el("p", t().noCopilot(s.install_cmd)));
    if (!s.npm) setup.append(el("p", t().noNpm, "err"));
    else setup.append(action(t().install, "/api/install"));
  } else if (s.state === "installing") {
    setup.append(el("p", t().installing));
  } else if (s.state === "needs_login") {
    setup.append(el("p", t().needsLogin));
    setup.append(action(t().login, "/api/login"));
  } else if (s.state === "logging_in") {
    setup.append(el("p", t().openLogin));
    if (s.login_code && s.login_url && s.login_url.startsWith("https://")) {
      const a = el("a", s.login_url);
      a.href = s.login_url;
      a.target = "_blank";
      a.rel = "noopener";
      const p = el("p");
      p.append(a, " ", el("span", s.login_code, "code"));
      setup.append(p, el("p", t().waitingAuth));
    } else {
      setup.append(el("p", t().preparingCode));
    }
  }
  for (const e of [s.install_error, s.login_error]) {
    if (e && s.state !== "installing" && s.state !== "logging_in") setup.append(el("p", errorText(e), "err"));
  }
  if (s.state === "installing" && s.install_log) setup.append(el("pre", s.install_log));
  setup.hidden = s.state === "ready";
}

async function refresh() {
  try {
    const s = await (await fetch("/api/status")).json();
    lastStatus = s;
    ready = s.state === "ready";
    renderSetup(s);
  } catch (err) {
    lastStatus = null;
    ready = false;
    setup.replaceChildren(el("p", t().serverDown, "err"));
    setup.hidden = false;
  }
  btn.disabled = busy || !ready;
}

setLang(lang);
refresh();
setInterval(refresh, 2000);

function add(cls, who, text) {
  const m = document.createElement("div");
  m.className = "msg " + cls;
  const w = document.createElement("div");
  w.className = "who";
  if (cls === "bot") {
    const avatar = el("span", "", "avatar");
    avatar.innerHTML = HELMET_SVG;
    w.append(avatar);
  }
  w.append(who);
  const txt = document.createElement("div");
  txt.className = "text";
  txt.textContent = text;
  m.append(w, txt);
  log.appendChild(m);
  log.scrollTop = log.scrollHeight;
  return txt;
}

function renderReply(out, data) {
  if (!Array.isArray(data.candidates)) { out.textContent = data.reply; return; }
  out.replaceChildren();
  const notes = (data.reply || "").split("\n").filter(l => !/^\s*\d+\. |^\s{3}/.test(l));
  for (const n of notes) if (n.trim()) out.append(el("div", n, "note"));
  if (data.suggested_issue_type || data.assignee_suggestions?.length) {
    const suggestions = el("div", "", "suggestions");
    if (data.suggested_issue_type) {
      suggestions.append(el("div", t().suggestedIssueType + ": " + data.suggested_issue_type, "suggestion"));
      if (data.issue_type_reason) suggestions.append(el("div", data.issue_type_reason, "why"));
    }
    if (data.assignee_suggestions?.length) {
      suggestions.append(el("div", t().suggestedAssignees, "suggestion-label"));
      for (const suggestion of data.assignee_suggestions) {
        suggestions.append(el("div", suggestion.assignee + " (" + t().basedOn + " " + suggestion.evidence.join(", ") + ")", "suggestion"));
      }
    }
    out.append(suggestions);
  }
  for (const c of data.candidates) {
    const card = el("div", "", "card");
    const head = el("div", "", "head");
    head.append(el("span", c.pkey, "pkey"), el("span", c.summary, "summary"));
    const meta = el("div", "", "meta");
    meta.append(el("span", t().status + ": " + c.status, "pill"),
                el("span", t().assignee + ": " + c.assignee, "pill"));
    if (c.issuetype) meta.append(el("span", t().issueType + ": " + c.issuetype, "pill"));
    card.append(head, meta);
    if (c.reason) card.append(el("div", c.reason, "why"));
    out.append(card);
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = entry.value.trim();
  if (!prompt || !ready || busy) return;
  entry.value = "";
  add("user", t().you, prompt);
  const out = add("bot", t().bot, t().searching);
  busy = true;
  btn.disabled = true;
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, lang }),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      const f = t().errors[data.error];
      throw new Error(f ? f() : (data.reply || "HTTP " + r.status));
    }
    renderReply(out, data);
  } catch (err) {
    out.textContent = t().error + err.message;
  }
  busy = false;
  btn.disabled = !ready;
  entry.focus();
  log.scrollTop = log.scrollHeight;
});
