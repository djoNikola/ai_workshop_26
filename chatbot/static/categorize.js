const T = {
  en: {
    toDark: "Switch to dark theme",
    toLight: "Switch to light theme",
    languageLabel: "Language",
    pageTitle: "Ticket Categorization Miner",
    homeNav: "SIP Tickets Miner",
    categorizeNav: "Ticket Categorization Miner",
    recommendNav: "Expert Recommendation Miner",
    placeholder: "Describe the problem (IT/EN) to suggest an issue type...",
    send: "Send",
    you: "You",
    bot: "Miner",
    working: "Classifying the issue...",
    notReady: "Copilot is not ready. Open Ticket lookup to install or sign in.",
    noCategory: "No category could be suggested. Try adding more detail (system, site, error).",
    unavailable: "LLM ranking was unavailable; showing the best keyword match.",
    suggested: "Suggested category",
    confidence: "Confidence",
    alternatives: "Alternatives",
    similar: "Similar tickets in this category",
    error: "Error: ",
  },
  it: {
    toDark: "Passa al tema scuro",
    toLight: "Passa al tema chiaro",
    languageLabel: "Lingua",
    pageTitle: "Miner classificazione ticket",
    homeNav: "Miner ticket SIP",
    categorizeNav: "Miner classificazione ticket",
    recommendNav: "Miner raccomandazione esperti",
    placeholder: "Descrivi il problema (IT/EN) per suggerire un tipo di issue...",
    send: "Invia",
    you: "Tu",
    bot: "Miner",
    working: "Classificazione in corso...",
    notReady: "Copilot non è pronto. Apri la ricerca ticket per installare o accedere.",
    noCategory: "Nessuna categoria suggerita. Aggiungi dettagli (sistema, sede, errore).",
    unavailable: "Ranking LLM non disponibile; mostro la migliore corrispondenza per parole chiave.",
    suggested: "Categoria suggerita",
    confidence: "Confidenza",
    alternatives: "Alternative",
    similar: "Ticket simili in questa categoria",
    error: "Errore: ",
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
let ready = false;
let busy = false;

const t = () => T[lang];

function el(tag, text, cls) {
  const element = document.createElement(tag);
  if (text) element.textContent = text;
  if (cls) element.className = cls;
  return element;
}

function updateThemeLabel() {
  const label = document.documentElement.dataset.theme === "dark" ? t().toLight : t().toDark;
  themeBtn.title = label;
  themeBtn.setAttribute("aria-label", label);
}

function renderSetup() {
  setup.replaceChildren();
  if (ready) {
    setup.hidden = true;
    return;
  }
  const link = el("a", t().lookupLink);
  link.href = "/";
  setup.append(el("p", t().notReady), link);
  setup.hidden = false;
}

function setLang(next) {
  lang = next;
  localStorage.setItem("lang", lang);
  document.documentElement.lang = lang;
  document.getElementById("lang").setAttribute("aria-label", t().languageLabel);
  for (const button of langButtons) button.setAttribute("aria-pressed", String(button.dataset.lang === lang));
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t()[node.dataset.i18n];
  entry.placeholder = t().placeholder;
  btn.textContent = t().send;
  updateThemeLabel();
  renderSetup();
}

function addMessage(role, text) {
  const message = el("div", "", "msg " + role);
  const author = el("div", "", "who");
  if (role === "bot") {
    const avatar = el("span", "", "avatar");
    avatar.innerHTML = HELMET_SVG;
    author.append(avatar);
  }
  author.append(t()[role === "user" ? "you" : "bot"]);
  const content = el("div", text, "text");
  message.append(author, content);
  log.append(message);
  log.scrollTop = log.scrollHeight;
  return content;
}

function renderCategory(output, data) {
  output.replaceChildren();
  if (!data.category) {
    const reply = (data.reply || "").startsWith("No category could be suggested") ? t().noCategory : (data.reply || t().noCategory);
    output.append(el("div", reply, "note"));
    return;
  }
  if ((data.reply || "").startsWith("LLM ranking was unavailable")) {
    output.append(el("div", t().unavailable, "note"));
  }
  const heading = el("div", "", "category-title");
  heading.append(el("span", t().suggested + ": "), el("span", data.category.label, "pkey"));
  output.append(heading, el("div", t().confidence + ": " + data.category.confidence + "%", "pill category-confidence"));
  if (data.category.reason) output.append(el("div", data.category.reason, "why category-reason"));
  if (data.alternatives.length) {
    output.append(el("div", t().alternatives + ": " + data.alternatives.map(item => item.label + " (" + item.confidence + "%)").join(", "), "category-alternatives"));
  }
  if (data.examples.length) {
    const examples = el("div", "", "category-examples");
    examples.append(el("div", t().similar, "suggestion-label"));
    for (const ticket of data.examples) {
      const row = el("div", "", "category-example");
      row.append(el("strong", ticket.pkey), " - " + ticket.summary);
      examples.append(row);
    }
    output.append(examples);
  }
}

async function refresh() {
  try {
    const status = await (await fetch("/api/status")).json();
    ready = status.state === "ready";
  } catch (error) {
    ready = false;
  }
  renderSetup();
  btn.disabled = busy || !ready;
}

themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("theme", next);
  updateThemeLabel();
});
for (const button of langButtons) button.addEventListener("click", () => setLang(button.dataset.lang));
setLang(lang);
refresh();
setInterval(refresh, 2000);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const prompt = entry.value.trim();
  if (!prompt || !ready || busy) return;
  entry.value = "";
  addMessage("user", prompt);
  const output = addMessage("bot", t().working);
  busy = true;
  btn.disabled = true;
  try {
    const response = await fetch("/api/categorize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.reply || "HTTP " + response.status);
    renderCategory(output, data);
  } catch (error) {
    output.textContent = t().error + error.message;
  }
  busy = false;
  btn.disabled = !ready;
  entry.focus();
  log.scrollTop = log.scrollHeight;
});