"""Ticket categorization: BM25 shortlist of similar tickets, LLM picks the ISSUETYPE (see openspec change ticket-categorization)."""
import json
import re
from collections import defaultdict

from ticket_lookup import DEFAULT_LANG, SHORTLIST_SIZE

MAX_ALTERNATIVES = 2
MAX_EXAMPLES = 3
MAX_CATEGORIES = 1 + MAX_ALTERNATIVES

# The export has no decode table; the PM must confirm real names. Unknown codes show as "Type <code>".
ISSUETYPE_LABELS = {}

MESSAGES = {
    "en": {
        "llm_unavailable": "LLM ranking was unavailable; the category is based on the most similar tickets.",
        "no_match": "No category could be suggested. Try adding more detail (system, site, error).",
    },
    "it": {
        "llm_unavailable": "Il ranking LLM non è disponibile; la categoria si basa sui ticket più simili.",
        "no_match": "Impossibile suggerire una categoria. Prova ad aggiungere più dettagli (sistema, sito, errore).",
    },
}


def issuetype_label(code):
    code = (code or "").strip()
    return ISSUETYPE_LABELS.get(code) or f"Type {code}"


def local_vote(scored):
    """Total BM25 score per ISSUETYPE over [(ticket, score)], best first."""
    totals = defaultdict(float)
    for t, score in scored:
        if t.get("issuetype"):
            totals[t["issuetype"]] += score
    return [c for c, _ in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))]


def build_prompt(query, shortlist):
    """Only the allowed fields for the shortlisted tickets are sent."""
    rows = [
        {"pkey": t["pkey"], "summary": t["summary"], "description": t["description"], "issuetype": t["issuetype"]}
        for t in shortlist
    ]
    return (
        "You decide in which category (issuetype) a new support ticket should be created for a client's problem. "
        "The description may be Italian or English.\n"
        "Below are similar past tickets, each with its issuetype. "
        f"Pick at most {MAX_CATEGORIES} issuetype values from the list, best first. "
        "Return an empty list if none is relevant. Use only issuetype values that appear in the list.\n"
        'Reply with JSON only, no other text, in the form '
        '{"categories":[{"issuetype":"10","reason":"one short sentence in the language of the description"}]}\n\n'
        f"Client description:\n{query}\n\nSimilar tickets:\n{json.dumps(rows, ensure_ascii=False)}\n"
    )


def parse_llm_categories(output, shortlist):
    """Returns [(issuetype, reason)] limited to codes in the shortlist; raises ValueError on unusable output."""
    allowed = {t["issuetype"] for t in shortlist if t["issuetype"]}
    decoder = json.JSONDecoder()
    for m in re.finditer(r"\{", output or ""):
        try:
            data, _ = decoder.raw_decode(output[m.start():])
        except ValueError:
            continue
        if isinstance(data, dict) and isinstance(data.get("categories"), list):
            results = []
            for item in data["categories"]:
                if not isinstance(item, dict):
                    continue
                code = str(item.get("issuetype", "")).strip()
                if code in allowed and code not in [r[0] for r in results]:
                    results.append((code, str(item.get("reason", "")).strip()))
            return results[:MAX_CATEGORIES]
    raise ValueError("no valid JSON category in LLM output")


def _category(code, reason, scored):
    return {"issuetype": code, "label": issuetype_label(code), "reason": reason,
            "support": sum(1 for t, _ in scored if t["issuetype"] == code), "considered": len(scored)}


def _example(t):
    return {"pkey": t["pkey"], "summary": t["summary"], "status": t["status"]}


def format_reply(notes, category, alternatives):
    lines = list(notes)
    if category:
        lines.append(f"{category['label']} ({category['issuetype']}) - {category['support']}/{category['considered']}")
        if category["reason"]:
            lines.append(category["reason"])
        for a in alternatives:
            lines.append(f"{a['label']} ({a['issuetype']}) - {a['support']}/{a['considered']}")
    return "\n".join(lines)


def categorize(query, index, llm, lang=DEFAULT_LANG):
    """llm(prompt) -> str. Returns {"reply", "category", "alternatives", "examples"}; fixed notes use `lang`."""
    msg = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    notes = []
    scored = [(t, s) for t, s in index.shortlist_scored(query, SHORTLIST_SIZE) if t["issuetype"]]
    ranked = []
    if scored:
        shortlist = [t for t, _ in scored]
        try:
            ranked = parse_llm_categories(llm(build_prompt(query, shortlist)), shortlist)
        except Exception:
            notes.append(msg["llm_unavailable"])
            ranked = [(c, "") for c in local_vote(scored)[:MAX_CATEGORIES]]

    if not ranked:
        notes.append(msg["no_match"])
        return {"reply": "\n".join(notes), "notes": notes, "category": None, "alternatives": [], "examples": []}

    cats = [_category(c, r, scored) for c, r in ranked]
    category, alternatives = cats[0], cats[1:]
    examples = [_example(t) for t, _ in scored if t["issuetype"] == category["issuetype"]][:MAX_EXAMPLES]
    return {"reply": format_reply(notes, category, alternatives), "notes": notes, "category": category,
            "alternatives": alternatives, "examples": examples}
