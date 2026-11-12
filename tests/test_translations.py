"""Static verification of bilingual V15 setup/options translations."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]/"custom_components"/"v15_lastmanagement"
FIELDS = {
    "grid_sensor", "limit_kw", "reserve_kw", "reverse_sign", "stale_seconds",
    "load_switches", "auto_restore", "restore_stable_seconds",
    "restore_min_off_seconds", "restore_margin_watts", "evcc_configured",
    "goe_configured",
}


class TestFlowTranslations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.de = json.loads((ROOT/"translations"/"de.json").read_text())
        cls.en = json.loads((ROOT/"translations"/"en.json").read_text())
        cls.strings = json.loads((ROOT/"strings.json").read_text())

    def test_german_all_settings_have_labels_and_help(self):
        for section, step in (("config", "user"), ("options", "init")):
            with self.subTest(step=step):
                form = self.de[section]["step"][step]
                self.assertEqual(set(form["data"]), FIELDS)
                self.assertEqual(set(form["data_description"]), FIELDS)
                self.assertTrue(all(form["data"].values()))
                self.assertTrue(all(form["data_description"].values()))

    def test_english_all_settings_have_labels_and_help(self):
        for section, step in (("config", "user"), ("options", "init")):
            with self.subTest(step=step):
                form = self.en[section]["step"][step]
                self.assertEqual(set(form["data"]), FIELDS)
                self.assertEqual(set(form["data_description"]), FIELDS)

    def test_second_page_contains_visible_explanation(self):
        for language, content in (("de", self.de), ("en", self.en)):
            for section in ("config", "options"):
                with self.subTest(language=language, section=section):
                    step = content[section]["step"]["restore"]
                    self.assertIn("{switches}", step["description"])
                    self.assertIn("W", step["title"])
                    self.assertGreater(len(step["description"]), 150)

    def test_evcc_page_has_bilingual_labels_and_descriptions(self):
        for language, content in (("de", self.de), ("en", self.en)):
            for section in ("config", "options"):
                with self.subTest(language=language, section=section):
                    step = content[section]["step"]["evcc"]
                    self.assertEqual(set(step["data"]), set(step["data_description"]))
                    self.assertGreaterEqual(len(step["data"]), 12)
                    self.assertGreater(len(step["description"]), 150)

    def test_goe_page_is_bilingual_and_has_safety_warnings(self):
        for language, content in (("de", self.de), ("en", self.en)):
            for section in ("config", "options"):
                with self.subTest(language=language, section=section):
                    step = content[section]["step"]["goe"]
                    self.assertEqual(set(step["data"]), set(step["data_description"]))
                    self.assertEqual(len(step["data"]), 9)
                    self.assertIn("goe_other_regulators_disabled", step["data"])
                    self.assertIn("goe_local_ipv4", step["data"])
                    self.assertGreater(len(step["description"]), 180)

    def test_locales_have_matching_structure(self):
        def keys(value):
            if isinstance(value, dict):
                return {k: keys(v) for k,v in value.items()}
            return None
        self.assertEqual(keys(self.de), keys(self.en))

    def test_english_source_matches_english_translation(self):
        self.assertEqual(self.strings, self.en)

    def test_dynamic_selected_switch_names_are_passed_to_both_forms(self):
        src = (ROOT/"config_flow.py").read_text()
        self.assertEqual(src.count('description_placeholders=restore_description_placeholders('), 2)
        tree = ast.parse(src)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'restore_description_placeholders')
        local = {}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), 'flow_helper', 'exec'), local)
        self.assertEqual(local['restore_description_placeholders'](['switch.test_a', 'switch.test_b']), {
            'switches': '- `switch.test_a`\n- `switch.test_b`'
        })


if __name__ == '__main__':
    unittest.main()
