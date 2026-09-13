import ast
import unittest
from pathlib import Path

from jpta_core import JPTAIndex, normalize_ja


ROOT = Path(__file__).resolve().parents[1]


class SearchRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = JPTAIndex(ROOT / "tags")
        # Exercise the WebUI scorer without requiring a running Gradio installation.
        source = ast.parse((ROOT / "scripts/jp_tag_assistant.py").read_text(encoding="utf-8"))
        function = next(node for node in source.body if isinstance(node, ast.FunctionDef) and node.name == "score_entry")
        namespace = {"normalize_ja": normalize_ja}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "webui_scorer", "exec"), namespace)
        cls.webui_score = staticmethod(namespace["score_entry"])

    def test_unrelated_suffix_is_not_a_match(self):
        entry = {"terms": ["アン"], "source": "translation"}
        for scorer in (self.index.score_entry, self.webui_score):
            with self.subTest(scorer=scorer):
                self.assertEqual(scorer("レズビアン", entry)[0], 0)

    def test_short_queries_still_match_longer_terms(self):
        for scorer in (self.index.score_entry, self.webui_score):
            self.assertGreater(scorer("膝", {"terms": ["膝立ち"]})[0], 0)

    def test_japanese_alias_returns_yuri_not_ahn(self):
        results = self.index.search("レズビアン")
        self.assertEqual(results[0]["tag"], "yuri")
        self.assertNotIn("ahn", [item["tag"] for item in results])

    def test_existing_words_and_phrases(self):
        for query, expected in [("膝", "kneeling"), ("膝立ち", "kneeling"), ("四つんばい", "all_fours"), ("all fours", "all_fours"), ("from below", "from_below"), ("knee", "kneeling"), ("口", "mouth")]:
            with self.subTest(query=query):
                self.assertIn(expected, [item["tag"] for item in self.index.search(query, limit=100)])

    def test_copyright_filter(self):
        results = self.index.search("ピース", limit=100, exclude_licensed=True)
        self.assertTrue(results)
        categories = self.index.load_tag_categories()
        self.assertTrue(all(categories.get(item["tag"]) not in (3, 4) for item in results))


if __name__ == "__main__":
    unittest.main()
