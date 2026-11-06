"""Ticket lookup: ID shortcut, local keyword shortlist, LLM re-rank (see openspec change ticket-lookup-chatbot)."""
import csv
import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "resources" / "issues_export.csv"
MAX_RESULTS = 3
SHORTLIST_SIZE = 30
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


def assignee_label(value):
    value = (value or "").strip()
    return "Unassigned" if value in ("", "[NULL]") else value


def _clean(value):
    value = (value or "").strip()
    return "" if value == "[NULL]" else value


class TicketIndex:
    def __init__(self, tickets):
        self.tickets = {t["pkey"]: t for t in tickets}
        self.issue_types = sorted({t["issuetype"] for t in self.tickets.values() if t["issuetype"]})
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
        return [self.tickets[pkey] for _, pkey in scored[:size]]


def extract_ids(text):
    seen = []
    for m in ID_RE.findall(text):
        key = m.upper()
        if key not in seen:
            seen.append(key)
    return seen


def build_prompt(query, shortlist, issue_types=None):
    """Only the allowed fields for the shortlisted tickets are sent."""
    rows = [
        {"pkey": t["pkey"], "summary": t["summary"], "description": t["description"],
         "status": t["status"], "assignee": t["assignee"], "issuetype": t["issuetype"]}
        for t in shortlist
    ]
    types = sorted(set(issue_types if issue_types is not None else (t["issuetype"] for t in shortlist)))
    return (
        "You match a client's problem description to support tickets. The description may be Italian or English.\n"
        f"Pick at most {MAX_RESULTS} tickets from the list below that really match the description, best first. "
        "Return an empty list if none is relevant. Use only pkey values from the list. Also classify the new issue "
        "using exactly one value from the allowed issue types, or null if it cannot be determined. Do not invent "
        "issue types. Suggest assignees only through the ranked tickets; do not invent users.\n"
        'Reply with JSON only, no other text, in the form '
        '{"results":[{"pkey":"BTU-1","reason":"one short sentence in the language of the description"}], '
        '"suggested_issue_type":"10", "issue_type_reason":"short reason"}\n\n'
        f"Client description:\n{query}\n\nAllowed issue types:\n{json.dumps(types, ensure_ascii=False)}\n\n"
        f"Tickets:\n{json.dumps(rows, ensure_ascii=False)}\n"
    )


def parse_llm_response(output, shortlist, issue_types):
    """Parse ranked tickets and accept a type only when it belongs to the CSV taxonomy."""
    allowed = {t["pkey"] for t in shortlist}
    allowed_types = set(issue_types)
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
            issue_type = data.get("suggested_issue_type")
            if not isinstance(issue_type, str) or issue_type not in allowed_types:
                issue_type = None
            return {
                "results": results[:MAX_RESULTS],
                "suggested_issue_type": issue_type,
                "issue_type_reason": str(data.get("issue_type_reason", "")).strip() if issue_type else "",
            }
    raise ValueError("no valid JSON result in LLM output")


def parse_llm_results(output, shortlist):
    """Returns [(pkey, reason)] limited to shortlist IDs; raises ValueError on unusable output."""
    return parse_llm_response(output, shortlist, []) ["results"]


def _candidate(ticket, reason):
    return {"pkey": ticket["pkey"], "summary": ticket["summary"], "status": ticket["status"],
            "assignee": ticket["assignee"], "issuetype": ticket["issuetype"], "reason": reason}


def _assignee_suggestions(candidates):
    suggestions = []
    by_assignee = {}
    for candidate in candidates:
        assignee = candidate["assignee"]
        if assignee == "Unassigned":
            continue
        suggestion = by_assignee.get(assignee)
        if suggestion is None:
            suggestion = {"assignee": assignee, "evidence": []}
            by_assignee[assignee] = suggestion
            suggestions.append(suggestion)
        suggestion["evidence"].append(candidate["pkey"])
    return suggestions


def format_reply(notes, candidates):
    lines = list(notes)
    for i, c in enumerate(candidates, 1):
        lines.append(f"{i}. {c['pkey']} - {c['summary']}\n   Status: {c['status']} | Assignee: {c['assignee']}")
        if c["reason"]:
            lines.append(f"   {c['reason']}")
    return "\n".join(lines)


def lookup(query, index, llm, lang=DEFAULT_LANG):
    """llm(prompt) -> str. Returns ranked tickets and validated suggestions; notes use `lang` (en/it)."""
    msg = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    notes, candidates = [], []
    suggested_issue_type, issue_type_reason, assignee_suggestions = None, "", []
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
            response = parse_llm_response(
                llm(build_prompt(text.strip(), shortlist, index.issue_types)), shortlist, index.issue_types
            )
            ranked_candidates = [
                _candidate(index.tickets[p], reason) for p, reason in response["results"][:room]
            ]
            candidates += ranked_candidates
            suggested_issue_type = response["suggested_issue_type"]
            issue_type_reason = response["issue_type_reason"]
            assignee_suggestions = _assignee_suggestions(ranked_candidates)
        except Exception:
            notes.append(msg["llm_unavailable"])
            candidates += [_candidate(t, "") for t in shortlist[:room]]

    if not candidates:
        notes.append(msg["no_match"])
    return {
        "reply": format_reply(notes, candidates),
        "candidates": candidates,
        "suggested_issue_type": suggested_issue_type,
        "issue_type_reason": issue_type_reason,
        "assignee_suggestions": assignee_suggestions,
    }
