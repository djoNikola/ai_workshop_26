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
        r = tl.lookup("campioni consegnati da consegnare", INDEX, failing_llm)
        self.assertEqual(len(r["candidates"]), tl.MAX_RESULTS)
        self.assertIn("LLM ranking was unavailable", r["reply"])

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


class RecommendTests(unittest.TestCase):
    QUERY = "servizio per pannellini e stampanti preanalitica"

    @staticmethod
    def fail_llm(prompt):
        raise RuntimeError("down")

    def test_limits_and_csv_facts(self):
        r = tl.recommend(self.QUERY, INDEX, self.fail_llm)
        self.assertTrue(1 <= len(r["experts"]) <= tl.RECOMMEND_EXPERTS)
        self.assertLessEqual(len(r["tickets"]), tl.RECOMMEND_TICKETS)
        for x in r["experts"]:
            self.assertNotEqual(x["assignee"], "Unassigned")
            for t in x["tickets"]:
                row = INDEX.get(t["pkey"])
                self.assertEqual((t["summary"], x["assignee"]), (row["summary"], row["assignee"]))

    def test_known_ticket_assignee_recommended(self):
        t = INDEX.get("BTU-4114")
        r = tl.recommend(t["summary"], INDEX, self.fail_llm)
        self.assertIn(t["assignee"], [x["assignee"] for x in r["experts"]])
        self.assertIn("LLM ranking was unavailable", r["reply"])

    def test_llm_choice_and_reason(self):
        index = tl.TicketIndex([
            {"pkey": "X-1", "summary": "stampante etichette", "description": "", "status": "Closed",
             "assignee": "agiallo", "issuetype": "10"},
            {"pkey": "X-2", "summary": "stampante etichette rotta", "description": "", "status": "Closed",
             "assignee": "mrossi", "issuetype": "10"},
        ])
        out = '{"experts":[{"assignee":"agiallo","reason":"ok"},{"assignee":"ghost","reason":"x"}]}'
        r = tl.recommend("stampante etichette", index, lambda p: out)
        self.assertEqual([x["assignee"] for x in r["experts"]], ["agiallo"])
        self.assertEqual(r["experts"][0]["reason"], "ok")

    def test_llm_empty_means_no_expert(self):
        r = tl.recommend(self.QUERY, INDEX, lambda p: '{"experts": []}')
        self.assertEqual(r["experts"], [])

    def test_skips_unassigned(self):
        index = tl.TicketIndex([
            {"pkey": "X-1", "summary": "stampante etichette", "description": "", "status": "Closed",
             "assignee": "Unassigned", "issuetype": "10"},
            {"pkey": "X-2", "summary": "stampante etichette rotta", "description": "", "status": "Closed",
             "assignee": "mrossi", "issuetype": "10"},
        ])
        r = tl.recommend("stampante etichette", index, self.fail_llm)
        self.assertEqual([x["assignee"] for x in r["experts"]], ["mrossi"])
        self.assertEqual([t["pkey"] for t in r["tickets"]], ["X-2"])

    def test_no_match(self):
        r = tl.recommend("zzzz qqqq", INDEX, self.fail_llm)
        self.assertEqual(r["experts"], [])
        self.assertIn("No expert could be recommended", r["reply"])


if __name__ == "__main__":
    unittest.main()
