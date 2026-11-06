import json
import unittest

import ticket_categorize as tc
import ticket_lookup as tl

INDEX = tl.TicketIndex.from_csv()
QUERY = "la stampante delle etichette non stampa"


def llm_returning(*codes):
    return lambda prompt: json.dumps({"categories": [{"issuetype": c, "reason": "ok"} for c in codes]})


def failing_llm(prompt):
    raise RuntimeError("down")


def no_llm(prompt):
    raise AssertionError("LLM must not be called")


def fixture(*rows):
    return [({"pkey": f"X-{i}", "summary": "s", "description": "d", "status": "Open", "issuetype": c}, s)
            for i, (c, s) in enumerate(rows)]


class LabelAndVoteTests(unittest.TestCase):
    def test_unknown_code(self):
        self.assertEqual(tc.issuetype_label("10"), "Type 10")

    def test_known_code(self):
        tc.ISSUETYPE_LABELS["99"] = "Bug"
        try:
            self.assertEqual(tc.issuetype_label("99"), "Bug")
        finally:
            del tc.ISSUETYPE_LABELS["99"]

    def test_rows_have_issuetype(self):
        self.assertEqual(len(INDEX.tickets), 3816)
        self.assertTrue(any(t["issuetype"] for t in INDEX.tickets.values()))

    def test_vote_ranks_by_score_total(self):
        self.assertEqual(tc.local_vote(fixture(("10", 1.0), ("9", 2.0), ("10", 0.5), ("11", 0.1))), ["9", "10", "11"])


class ParseTests(unittest.TestCase):
    SHORT = [t for t, _ in fixture(("10", 1), ("9", 1))]

    def test_valid_and_unknown_dropped(self):
        out = 'text {"categories":[{"issuetype":"9","reason":"r"},{"issuetype":"77","reason":"x"}]}'
        self.assertEqual(tc.parse_llm_categories(out, self.SHORT), [("9", "r")])

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            tc.parse_llm_categories("nope", self.SHORT)

    def test_prompt_fields_and_size(self):
        rows = [t for t, _ in INDEX.shortlist_scored(QUERY)]
        prompt = tc.build_prompt(QUERY, rows)
        self.assertLessEqual(len(rows), tl.SHORTLIST_SIZE)
        self.assertNotIn("assignee", prompt)
        self.assertIn("issuetype", prompt)


class CategorizeTests(unittest.TestCase):
    def codes(self):
        return {t["issuetype"] for t, _ in INDEX.shortlist_scored(QUERY) if t["issuetype"]}

    def test_normal(self):
        code = sorted(self.codes())[0]
        r = tc.categorize(QUERY, INDEX, llm_returning(code, "no-such-code"))
        self.assertEqual(r["category"]["issuetype"], code)
        self.assertEqual(r["alternatives"], [])
        self.assertLessEqual(len(r["examples"]), tc.MAX_EXAMPLES)
        for x in r["examples"]:
            row = INDEX.get(x["pkey"])
            self.assertEqual((row["issuetype"], row["summary"], row["status"]), (code, x["summary"], x["status"]))

    def test_limits(self):
        r = tc.categorize(QUERY, INDEX, llm_returning(*self.codes()))
        self.assertLessEqual(len(r["alternatives"]), tc.MAX_ALTERNATIVES)

    def test_llm_failure_falls_back(self):
        r = tc.categorize(QUERY, INDEX, failing_llm)
        self.assertEqual(r["category"]["issuetype"], tc.local_vote(INDEX.shortlist_scored(QUERY))[0])
        self.assertIn(tc.MESSAGES["en"]["llm_unavailable"], r["notes"])

    def test_no_match_skips_llm(self):
        r = tc.categorize("zzzqx wwwvk", INDEX, no_llm, "it")
        self.assertIsNone(r["category"])
        self.assertEqual(r["notes"], [tc.MESSAGES["it"]["no_match"]])

    def test_unknown_lang_is_english(self):
        r = tc.categorize("zzzqx wwwvk", INDEX, no_llm, "xx")
        self.assertEqual(r["notes"], [tc.MESSAGES["en"]["no_match"]])


if __name__ == "__main__":
    unittest.main()
