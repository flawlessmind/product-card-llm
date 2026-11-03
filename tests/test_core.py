import json
import unittest
from unittest import mock

from cardgen import generator
from cardgen.validation import InvalidProductError, missing_specs, normalize, parse_product


class ValidationTests(unittest.TestCase):
    def test_broken_json(self):
        with self.assertRaises(InvalidProductError):
            parse_product("{not json")

    def test_not_an_object(self):
        with self.assertRaises(InvalidProductError):
            normalize([1, 2])

    def test_name_required(self):
        with self.assertRaises(InvalidProductError):
            normalize({"name": "  ", "specs": {"a": "1"}})

    def test_nothing_to_write_from(self):
        with self.assertRaises(InvalidProductError):
            normalize({"name": "Прибор", "specs": {}, "description": ""})

    def test_empty_spec_dropped_with_warning(self):
        product, warnings = normalize(
            {"name": "П", "specs": {"класс точности": " ", "диапазон": "0-10"}, "description": "x"}
        )
        self.assertEqual(product["specs"], {"диапазон": "0-10"})
        self.assertTrue(any("класс точности" in w for w in warnings))

    def test_missing_specs(self):
        missing = missing_specs({"диапазон измерений": "0-10 бар"})
        self.assertIn("класс точности", missing)
        self.assertNotIn("диапазон измерений", missing)


class GeneratorTests(unittest.TestCase):
    product = {
        "name": "Манометр",
        "manufacturer": "",
        "specs": {"диапазон измерений": "0–1,6 МПа"},
        "description": "Измеряет давление.",
    }

    def _answer(self, title="Манометр 0–1,6 МПа", desc_len=900):
        return json.dumps(
            {
                "seo_title": title,
                "seo_description": "а" * desc_len,
                "search_queries": ["манометр", "манометр 1,6 МПа", "купить манометр"],
                "suitable_for": [],
                "tasks": ["Измерение давления"],
            },
            ensure_ascii=False,
        )

    def test_retry_on_wrong_length(self):
        answers = [self._answer(desc_len=100), self._answer()]
        with mock.patch("cardgen.llm.chat", side_effect=answers) as chat:
            card = generator.generate_card(self.product, [])
        self.assertEqual(chat.call_count, 2)
        self.assertFalse(any("Не удалось выдержать" in w for w in card["warnings"]))

    def test_too_long_description_truncated(self):
        long_text = json.loads(self._answer())
        long_text["seo_description"] = "Предложение номер один. " * 100
        with mock.patch("cardgen.llm.chat", return_value=json.dumps(long_text, ensure_ascii=False)):
            card = generator.generate_card(self.product, [])
        self.assertLessEqual(len(card["seo_description"]), 1200)
        self.assertTrue(card["seo_description"].endswith("."))
        self.assertTrue(any("обрезан" in w for w in card["warnings"]))

    def test_unsupported_commercial_item_flagged(self):
        answer = json.loads(self._answer())
        answer["suitable_for"] = ["нефтегазовые предприятия"]
        answer["tasks"] = ["измерение давления"]
        with mock.patch("cardgen.llm.chat", return_value=json.dumps(answer, ensure_ascii=False)):
            card = generator.generate_card(self.product, [])
        warning = next(w for w in card["warnings"] if "без опоры" in w)
        self.assertIn("нефтегазовые", warning)
        self.assertNotIn("измерение давления", warning)

    def test_no_data_markers(self):
        with mock.patch("cardgen.llm.chat", return_value=self._answer()):
            card = generator.generate_card(self.product, [])
        self.assertEqual(card["manufacturer"], "данных нет")
        self.assertEqual(card["commercial"]["suitable_for"], ["данных нет"])
        self.assertEqual(card["characteristics"]["класс точности"], "данных нет")

    def test_unknown_number_flagged(self):
        with mock.patch("cardgen.llm.chat", return_value=self._answer(title="Манометр 25 МПа")):
            card = generator.generate_card(self.product, [])
        self.assertTrue(any("25" in w for w in card["warnings"]))


if __name__ == "__main__":
    unittest.main()
