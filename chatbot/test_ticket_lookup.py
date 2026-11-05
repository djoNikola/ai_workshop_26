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


if __name__ == "__main__":
    unittest.main()
