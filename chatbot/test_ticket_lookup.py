import json
import unittest

import ticket_lookup as tl

INDEX = tl.TicketIndex.from_csv()


def llm_returning(*pkeys):
    return lambda prompt: json.dumps({"results": [{"pkey": p, "reason": "ok"} for p in pkeys]})


def failing_llm(prompt):
    raise RuntimeError("down")


class LoadTests(unittest.TestCase):
    def test_all_rows_load(self):
        self.assertEqual(len(INDEX.tickets), 3816)

    def test_fields_are_clean(self):
        t = INDEX.get("btu-4114")
        self.assertEqual((t["status"], t["assignee"]), ("Closed", "alfmancu"))
        self.assertTrue(all(len(x["description"]) <= tl.DESCRIPTION_LIMIT for x in INDEX.tickets.values()))
        self.assertNotIn("[NULL]", {x["assignee"] for x in INDEX.tickets.values()})


class LabelTests(unittest.TestCase):
    def test_status(self):
        self.assertEqual(tl.status_label("6"), "Closed")
        self.assertEqual(tl.status_label("10008"), "Status 10008")

    def test_assignee(self):
        self.assertEqual(tl.assignee_label(""), "Unassigned")
        self.assertEqual(tl.assignee_label("[NULL]"), "Unassigned")
        self.assertEqual(tl.assignee_label("mmolino"), "mmolino")


class IdTests(unittest.TestCase):
    def test_extract(self):
        self.assertEqual(tl.extract_ids("ticket btu-4114 non va"), ["BTU-4114"])
        self.assertEqual(tl.extract_ids("nessun numero"), [])


class ShortlistTests(unittest.TestCase):
    def test_italian_query(self):
        q = "il cliente vuole filtrare i campioni consegnati e da consegnare"
        keys = [t["pkey"] for t in INDEX.shortlist(q)]
        self.assertIn("BTU-4115", keys)
        self.assertLessEqual(len(keys), tl.SHORTLIST_SIZE)

    def test_english_query(self):
        keys = [t["pkey"] for t in INDEX.shortlist("deliver sample management Cardarelli Napoli")]
        self.assertIn("BTU-4113", keys)

    def test_no_shared_terms(self):
        self.assertEqual(INDEX.shortlist("zzzqx wwwvk"), [])


class ParseTests(unittest.TestCase):
    SHORT = [INDEX.get("BTU-4113"), INDEX.get("BTU-4114")]

    def test_valid_with_noise(self):
        out = 'sure\n{"results":[{"pkey":"BTU-4114","reason":"r"}]}\nUsage: 1'
        self.assertEqual(tl.parse_llm_results(out, self.SHORT), [("BTU-4114", "r")])

    def test_unknown_id_dropped(self):
        out = '{"results":[{"pkey":"BTU-1","reason":"x"},{"pkey":"BTU-4113","reason":"y"}]}'
        self.assertEqual(tl.parse_llm_results(out, self.SHORT), [("BTU-4113", "y")])

    def test_invalid(self):
        with self.assertRaises(ValueError):
            tl.parse_llm_results("not json", self.SHORT)

    def test_prompt_has_only_allowed_fields(self):
        prompt = tl.build_prompt("q", self.SHORT)
        self.assertIn("BTU-4113", prompt)
        row = json.loads(prompt.split("Tickets:\n", 1)[1])[0]
        self.assertEqual(set(row), {"pkey", "summary", "description", "status", "assignee"})


class LookupTests(unittest.TestCase):
    def test_existing_id_first(self):
        r = tl.lookup("BTU-4114", INDEX, failing_llm)
        self.assertEqual([c["pkey"] for c in r["candidates"]], ["BTU-4114"])
        self.assertEqual(r["candidates"][0]["assignee"], "alfmancu")

    def test_wrong_id_with_description(self):
        q = "BTU-99999 servizio per pannellini e stampanti preanalitica"
        r = tl.lookup(q, INDEX, llm_returning("BTU-4114"))
        self.assertIn("BTU-99999 was not found", r["reply"])
        self.assertEqual(r["candidates"][0]["pkey"], "BTU-4114")

    def test_no_match(self):
        r = tl.lookup("zzzqx wwwvk", INDEX, failing_llm)
        self.assertEqual(r["candidates"], [])
        self.assertIn("No matching ticket found", r["reply"])

    def test_llm_empty_list_means_no_match(self):
        r = tl.lookup("ricetta per la torta di mele", INDEX, llm_returning())
        self.assertEqual(r["candidates"], [])
        self.assertIn("No matching ticket found", r["reply"])

    def test_degraded_mode(self):
        with self.assertLogs("ticket_lookup", level="ERROR") as logs:
            r = tl.lookup("campioni consegnati da consegnare", INDEX, failing_llm)
        self.assertIn("RuntimeError: down", logs.output[0])
        self.assertEqual(len(r["candidates"]), tl.MAX_RESULTS)
        self.assertIn("LLM ranking was unavailable", r["reply"])

    def test_invalid_llm_output_is_logged(self):
        with self.assertLogs("ticket_lookup", level="ERROR") as logs:
            r = tl.lookup("campioni consegnati da consegnare", INDEX, lambda prompt: "not JSON")
        self.assertIn("ValueError: no valid JSON result", logs.output[0])
        self.assertIn("LLM ranking was unavailable", r["reply"])
        self.assertEqual(
            [c["pkey"] for c in r["candidates"]],
            [t["pkey"] for t in INDEX.shortlist("campioni consegnati da consegnare")[:tl.MAX_RESULTS]],
        )

    def test_italian_notes(self):
        r = tl.lookup("BTU-99999 zzzqx", INDEX, failing_llm, "it")
        self.assertIn("Il ticket BTU-99999 non è stato trovato", r["reply"])
        self.assertIn("Nessun ticket corrispondente trovato", r["reply"])

    def test_unknown_lang_falls_back_to_english(self):
        r = tl.lookup("zzzqx wwwvk", INDEX, failing_llm, "xx")
        self.assertIn("No matching ticket found", r["reply"])

    def test_max_three_and_csv_facts(self):
        keys = [t["pkey"] for t in INDEX.shortlist("preanalitica")][:6]
        r = tl.lookup("preanalitica", INDEX, llm_returning(*keys))
        self.assertEqual(len(r["candidates"]), tl.MAX_RESULTS)
        for c in r["candidates"]:
            t = INDEX.get(c["pkey"])
            self.assertEqual((c["summary"], c["status"], c["assignee"]), (t["summary"], t["status"], t["assignee"]))


class RecommendTests(unittest.TestCase):
    class ScoredIndex:
        def __init__(self, rows):
            self.rows = rows

        def shortlist_scored(self, query):
            return self.rows

    @staticmethod
    def ticket(pkey, assignee):
        return {"pkey": pkey, "summary": "sample ticket", "assignee": assignee}

    def test_aggregates_top_five_assigned_tickets(self):
        rows = [
            (self.ticket("X-0", "Unassigned"), 20.0),
            (self.ticket("X-1", "ana"), 5.0),
            (self.ticket("X-2", "bob"), 3.0),
            (self.ticket("X-3", "ana"), 2.0),
            (self.ticket("X-4", "bob"), 1.0),
            (self.ticket("X-5", "carol"), 0.5),
            (self.ticket("X-6", "dave"), 0.1),
        ]
        result = tl.recommend("sample", self.ScoredIndex(rows))
        self.assertEqual([x["assignee"] for x in result["experts"]], ["ana", "bob", "carol"])
        self.assertEqual([x["pkey"] for x in result["experts"][0]["tickets"]], ["X-1", "X-3"])
        self.assertEqual([x["pkey"] for x in result["experts"][2]["tickets"]], ["X-5"])
        self.assertEqual(len(result["experts"]), tl.MAX_EXPERTS)

    def test_no_assigned_matches_returns_empty_experts(self):
        index = self.ScoredIndex([(self.ticket("X-1", "Unassigned"), 1.0)])
        result = tl.recommend("sample", index)
        self.assertEqual(result["experts"], [])
        self.assertIn("No similar assigned tickets", result["reply"])


class CategorizeTests(unittest.TestCase):
    QUERY = "servizio per pannellini e stampanti preanalitica"

    @staticmethod
    def llm_category(code):
        return lambda prompt: json.dumps({"category": code, "reason": "ok"})

    def test_label(self):
        self.assertEqual(tl.issuetype_label("10"), "Type 10")

    def test_known_ticket_gets_its_type(self):
        t = INDEX.get("BTU-4114")
        r = tl.categorize(t["summary"], INDEX, failing_llm)
        self.assertEqual(r["category"]["code"], t["issuetype"])
        self.assertIn("LLM ranking was unavailable", r["reply"])
        self.assertIn("BTU-4114", [e["pkey"] for e in r["examples"]])

    def test_limits_and_example_fields(self):
        r = tl.categorize(self.QUERY, INDEX, failing_llm)
        self.assertLessEqual(len(r["alternatives"]), tl.ALT_RESULTS)
        self.assertLessEqual(len(r["examples"]), tl.MAX_RESULTS)
        for e in r["examples"]:
            t = INDEX.get(e["pkey"])
            self.assertEqual((e["summary"], t["issuetype"]), (t["summary"], r["category"]["code"]))

    def test_llm_choice_used_when_in_shortlist(self):
        shortlist = INDEX.shortlist(self.QUERY)
        local = tl.category_scores(INDEX.shortlist_scored(self.QUERY))[0][0]
        other = next((t["issuetype"] for t in shortlist if t["issuetype"] and t["issuetype"] != local), None)
        if other:
            r = tl.categorize(self.QUERY, INDEX, self.llm_category(other))
            self.assertEqual(r["category"]["code"], other)

    def test_foreign_category_falls_back(self):
        r = tl.categorize(self.QUERY, INDEX, self.llm_category("999"))
        self.assertIn("LLM ranking was unavailable", r["reply"])
        self.assertNotEqual(r["category"]["code"], "999")

    def test_no_match_skips_llm(self):
        r = tl.categorize("zzzz qqqq", INDEX, lambda p: self.fail("LLM called"))
        self.assertIsNone(r["category"])
        self.assertIn("No category could be suggested", r["reply"])

    def test_llm_null_means_no_category(self):
        r = tl.categorize("ricetta per la torta di mele", INDEX, lambda p: '{"category": null, "reason": "x"}')
        self.assertIsNone(r["category"])

    def test_prompt_fields(self):
        rows = tl.build_category_prompt("q", INDEX.shortlist(self.QUERY))
        self.assertNotIn("assignee", rows)
        self.assertNotIn('"status"', rows)


if __name__ == "__main__":
    unittest.main()
