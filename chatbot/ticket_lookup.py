"""Ticket lookup: ID shortcut, local keyword shortlist, LLM re-rank (see openspec change ticket-lookup-chatbot)."""
import csv
import json
import logging
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).resolve().parent.parent / "resources" / "issues_export.csv"
MAX_RESULTS = 3
SHORTLIST_SIZE = 30
RECOMMENDATION_TICKETS = 5
MAX_EXPERTS = 3
DESCRIPTION_LIMIT = 500
ID_RE = re.compile(r"\b([A-Za-z]{2,10}-\d+)\b")

# The export has no decode table. Codes 1/3/4/5/6 follow the Jira defaults; the PM must confirm them.
STATUS_LABELS = {"1": "Open", "3": "In Progress", "4": "Reopened", "5": "Resolved", "6": "Closed"}

DEFAULT_LANG = "en"
MESSAGES = {
    "en": {
        "exact": "Exact ticket ID match.",
        "not_found": "Ticket {pkey} was not found.",
        "llm_unavailable": "LLM ranking was unavailable; showing the best keyword matches.",
        "no_match": "No matching ticket found. Try adding more detail (system, site, error).",
    },
    "it": {
        "exact": "Corrispondenza esatta con l'ID del ticket.",
        "not_found": "Il ticket {pkey} non è stato trovato.",
        "llm_unavailable": "Il ranking LLM non è disponibile; vengono mostrate le migliori corrispondenze per parole chiave.",
        "no_match": "Nessun ticket corrispondente trovato. Prova ad aggiungere più dettagli (sistema, sito, errore).",
    },
}

# The export has no decode table for ISSUETYPE; the PM must supply labels. Unknown codes show as "Type <code>".
ISSUETYPE_LABELS = {}
ALT_RESULTS = 2

STOPWORDS = set(
    "il lo la i gli le un uno una di del dello della dei degli delle da dal dalla in nel nella su sul sulla "
    "con per tra fra e ed o ma che non si ha hanno è al alla allo ai agli alle cliente vuole come anche "
    "the a an of to in on for with and or but is are was be it this that from at by as not has have client".split()
)


def _norm(text):
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def tokenize(text):
    """Lowercase, accent-free tokens cut to 5 chars as a crude stem (covers Italian suffixes)."""
    tokens = re.findall(r"[a-z0-9]+", _norm(text))
    return [t[:5] for t in tokens if len(t) > 2 and t not in STOPWORDS]


def status_label(code):
    code = (code or "").strip()
    return STATUS_LABELS.get(code) or f"Status {code}"


def issuetype_label(code):
    code = (code or "").strip()
    return ISSUETYPE_LABELS.get(code) or f"Type {code}"


def assignee_label(value):
    value = (value or "").strip()
    return "Unassigned" if value in ("", "[NULL]") else value


def _clean(value):
    value = (value or "").strip()
    return "" if value == "[NULL]" else value


class TicketIndex:
    def __init__(self, tickets):
        self.tickets = {t["pkey"]: t for t in tickets}
        self._docs = []
        df = Counter()
        for t in self.tickets.values():
            # summary counts double
            tokens = tokenize(t["summary"]) * 2 + tokenize(t["description"])
            counts = Counter(tokens)
            self._docs.append((t["pkey"], counts, len(tokens)))
            df.update(counts.keys())
        n = len(self._docs)
        self._idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}
        self._avg_len = (sum(d[2] for d in self._docs) / n) if n else 0

    @classmethod
    def from_csv(cls, path=CSV_PATH):
        tickets = []
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                pkey = (row.get("PKEY") or "").strip()
                if not pkey:
                    continue
                tickets.append({
                    "pkey": pkey,
                    "summary": _clean(row.get("SUMMARY")),
                    "description": _clean(row.get("DESCRIPTION"))[:DESCRIPTION_LIMIT],
                    "status": status_label(row.get("ISSUESTATUS")),
                    "assignee": assignee_label(row.get("ASSIGNEE")),
                    "issuetype": _clean(row.get("ISSUETYPE")),
                })
        return cls(tickets)

    def get(self, pkey):
        return self.tickets.get(pkey.upper())

    def shortlist(self, query, size=SHORTLIST_SIZE):
        """BM25 ranking; tickets sharing no query term are never returned."""
        return [t for t, _ in self.shortlist_scored(query, size)]

    def shortlist_scored(self, query, size=SHORTLIST_SIZE):
        q_terms = set(tokenize(query))
        if not q_terms:
            return []
        k1, b = 1.5, 0.75
        scored = []
        for pkey, counts, length in self._docs:
            score = 0.0
            for term in q_terms:
                tf = counts.get(term)
                if tf:
                    norm = tf + k1 * (1 - b + b * length / (self._avg_len or 1))
                    score += self._idf[term] * tf * (k1 + 1) / norm
            if score > 0:
                scored.append((score, pkey))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(self.tickets[pkey], score) for score, pkey in scored[:size]]


def extract_ids(text):
    seen = []
    for m in ID_RE.findall(text):
        key = m.upper()
        if key not in seen:
            seen.append(key)
    return seen


def build_prompt(query, shortlist):
    """Only the allowed fields for the shortlisted tickets are sent."""
    rows = [
        {"pkey": t["pkey"], "summary": t["summary"], "description": t["description"],
         "status": t["status"], "assignee": t["assignee"]}
        for t in shortlist
    ]
    return (
        "You match a client's problem description to support tickets. The description may be Italian or English.\n"
        f"Pick at most {MAX_RESULTS} tickets from the list below that really match the description, best first. "
        "Return an empty list if none is relevant. Use only pkey values from the list.\n"
        'Reply with JSON only, no other text, in the form '
        '{"results":[{"pkey":"BTU-1","reason":"one short sentence in the language of the description"}]}\n\n'
        f"Client description:\n{query}\n\nTickets:\n{json.dumps(rows, ensure_ascii=False)}\n"
    )


def parse_llm_results(output, shortlist):
    """Returns [(pkey, reason)] limited to shortlist IDs; raises ValueError on unusable output."""
    allowed = {t["pkey"] for t in shortlist}
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", output or ""):
        try:
            data, _ = decoder.raw_decode(output[m.start():])
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("results"), list):
            results = []
            for item in data["results"]:
                if not isinstance(item, dict):
                    continue
                pkey = str(item.get("pkey", "")).strip().upper()
                if pkey in allowed and pkey not in [r[0] for r in results]:
                    results.append((pkey, str(item.get("reason", "")).strip()))
            return results[:MAX_RESULTS]
    raise ValueError("no valid JSON result in LLM output")


def _candidate(ticket, reason):
    return {"pkey": ticket["pkey"], "summary": ticket["summary"], "status": ticket["status"],
            "assignee": ticket["assignee"], "reason": reason}


def format_reply(notes, candidates):
    lines = list(notes)
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c['pkey']} - {c['summary']}\n   Status: {c['status']} | Assignee: {c['assignee']}")
        if c["reason"]:
            lines.append(f"   {c['reason']}")
    return "\n".join(lines)


def lookup(query, index, llm, lang=DEFAULT_LANG):
    """llm(prompt) -> str. Returns {"reply": str, "candidates": [...]}; fixed notes use `lang` (en/it)."""
    msg = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    notes, candidates = [], []
    for pkey in extract_ids(query):
        ticket = index.get(pkey)
        if ticket and len(candidates) < MAX_RESULTS:
            candidates.append(_candidate(ticket, msg["exact"]))
        elif not ticket:
            notes.append(msg["not_found"].format(pkey=pkey))

    text = ID_RE.sub(" ", query)
    shortlist = [t for t in index.shortlist(text) if t["pkey"] not in {c["pkey"] for c in candidates}]
    room = MAX_RESULTS - len(candidates)
    if shortlist and room > 0:
        try:
            ranked = parse_llm_results(llm(build_prompt(text.strip(), shortlist)), shortlist)
            candidates += [_candidate(index.tickets[p], r) for p, r in ranked[:room]]
        except Exception:
            logger.exception("LLM ranking failed; falling back to keyword matches")
            notes.append(msg["llm_unavailable"])
            candidates += [_candidate(t, "") for t in shortlist[:room]]

    if not candidates:
        notes.append(msg["no_match"])
    return {"reply": format_reply(notes, candidates), "candidates": candidates}


def recommend(query, index):
    """Recommend assignees by aggregating BM25 scores from the five closest assigned tickets."""
    similar = [
        (ticket, score)
        for ticket, score in index.shortlist_scored(query)
        if ticket["assignee"] != "Unassigned"
    ][:RECOMMENDATION_TICKETS]
    if not similar:
        message = "No similar assigned tickets found. Try adding more detail (system, site, error)."
        return {"reply": message, "notes": [], "experts": []}

    by_assignee = {}
    for ticket, score in similar:
        expert = by_assignee.setdefault(ticket["assignee"], {"score": 0.0, "tickets": []})
        expert["score"] += score
        expert["tickets"].append({"pkey": ticket["pkey"], "summary": ticket["summary"]})

    total_score = sum(score for _, score in similar)
    ranked = sorted(by_assignee.items(), key=lambda item: (-item[1]["score"], item[0].casefold()))
    experts = [
        {
            "assignee": assignee,
            "confidence": round(100 * data["score"] / total_score),
            "tickets": data["tickets"],
            "reason": f"Assigned on {len(data['tickets'])} of the {len(similar)} closest tickets.",
        }
        for assignee, data in ranked[:MAX_EXPERTS]
    ]
    return {"reply": "Recommendations are based on the five closest assigned tickets.",
            "notes": [], "experts": experts}


def category_scores(scored):
    """Sums BM25 scores per ISSUETYPE; returns [(code, score)] best first."""
    totals = {}
    for t, score in scored:
        if t["issuetype"]:
            totals[t["issuetype"]] = totals.get(t["issuetype"], 0.0) + score
    return sorted(totals.items(), key=lambda s: (-s[1], s[0]))


def build_category_prompt(query, shortlist):
    """Only the allowed fields for the shortlisted tickets are sent."""
    rows = [
        {"pkey": t["pkey"], "summary": t["summary"], "description": t["description"], "issuetype": t["issuetype"]}
        for t in shortlist
    ]
    return (
        "You choose the ticket category (issuetype) for a new support ticket from a client's problem description. "
        "The description may be Italian or English.\n"
        "Choose exactly one issuetype code used by the similar tickets listed below. "
        "Use only issuetype values from the list. If none of the tickets is really relevant, use null.\n"
        'Reply with JSON only, no other text, in the form '
        '{"category":"<issuetype code or null>","reason":"one short sentence in the language of the description"}\n\n'
        f"Client description:\n{query}\n\nSimilar tickets:\n{json.dumps(rows, ensure_ascii=False)}\n"
    )


def parse_category(output, shortlist):
    """Returns (code, reason); code is None when the LLM says nothing fits. Raises ValueError on unusable output."""
    allowed = {t["issuetype"] for t in shortlist if t["issuetype"]}
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", output or ""):
        try:
            data, _ = decoder.raw_decode(output[m.start():])
        except ValueError:
            continue
        if isinstance(data, dict) and "category" in data:
            if data["category"] is None:
                return None, str(data.get("reason", "")).strip()
            code = str(data["category"]).strip()
            if code in allowed:
                return code, str(data.get("reason", "")).strip()
            raise ValueError("category not in shortlist")
    raise ValueError("no valid JSON result in LLM output")


def format_category_reply(notes, category, alternatives, examples):
    lines = list(notes)
    lines.append(f"Suggested category: {category['label']} (confidence {category['confidence']}%)")
    if category["reason"]:
        lines.append(category["reason"])
    if alternatives:
        lines.append("Alternatives: " + ", ".join(f"{a['label']} ({a['confidence']}%)" for a in alternatives))
    for e in examples:
        lines.append(f"- {e['pkey']} - {e['summary']}")
    return "\n".join(lines)


def categorize(query, index, llm):
    """llm(prompt) -> str. Suggests an ISSUETYPE; ticket IDs in the text are treated as plain text."""
    no_category = {"reply": "No category could be suggested. Try adding more detail (system, site, error).",
                   "category": None, "alternatives": [], "examples": []}
    scored = index.shortlist_scored(query)
    ranking = category_scores(scored)
    if not ranking:
        return no_category

    total = sum(s for _, s in ranking)
    scores = dict(ranking)
    shortlist = [t for t, _ in scored]
    notes, reason, top = [], "", ranking[0][0]
    try:
        top, reason = parse_category(llm(build_category_prompt(query.strip(), shortlist)), shortlist)
    except Exception:
        notes.append("LLM ranking was unavailable; showing the best keyword match.")
    if top is None:
        return no_category

    def entry(code, why=""):
        return {"code": code, "label": issuetype_label(code),
                "confidence": round(100 * scores[code] / total), "reason": why}

    category = entry(top, reason)
    alternatives = [entry(c) for c, _ in ranking if c != top][:ALT_RESULTS]
    examples = [_candidate(t, "") for t, _ in scored if t["issuetype"] == top][:MAX_RESULTS]
    return {"reply": format_category_reply(notes, category, alternatives, examples),
            "category": category, "alternatives": alternatives, "examples": examples}
