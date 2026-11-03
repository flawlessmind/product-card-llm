import json
import re

from . import llm
from .prompt import DESC_MAX, DESC_MIN, RESULT_SCHEMA, TITLE_MAX, build_messages
from .validation import NO_DATA, missing_specs

MAX_ATTEMPTS = 3
_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")


class ResultError(ValueError):
    pass


def _parse_result(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ResultError("Ответ не является корректным JSON.")
    if not isinstance(data, dict):
        raise ResultError("Ответ должен быть JSON-объектом.")
    for key in RESULT_SCHEMA["required"]:
        if key not in data:
            raise ResultError(f"В ответе нет поля «{key}».")
    for key in ("seo_title", "seo_description"):
        if not isinstance(data[key], str):
            raise ResultError(f"Поле «{key}» должно быть строкой.")
        data[key] = data[key].strip()
    for key in ("search_queries", "suitable_for", "tasks"):
        if not isinstance(data[key], list):
            raise ResultError(f"Поле «{key}» должно быть списком.")
        data[key] = [str(x).strip() for x in data[key] if str(x).strip()]
    return data


def _length_problems(result: dict) -> list[str]:
    problems = []
    title_len = len(result["seo_title"])
    desc_len = len(result["seo_description"])
    if not title_len:
        problems.append("seo_title пустой.")
    elif title_len > TITLE_MAX:
        problems.append(f"seo_title длиной {title_len} символов, нужно не более {TITLE_MAX}.")
    if not DESC_MIN <= desc_len <= DESC_MAX:
        problems.append(
            f"seo_description длиной {desc_len} символов, нужно от {DESC_MIN} до {DESC_MAX}."
        )
    if not 3 <= len(result["search_queries"]) <= 5:
        problems.append("search_queries должно содержать от 3 до 5 запросов.")
    return problems


def _numbers(text: str) -> set[str]:
    return {n.replace(",", ".") for n in _NUMBER.findall(text)}


def _unknown_numbers(result: dict, product: dict) -> list[str]:
    known = _numbers(json.dumps(product, ensure_ascii=False))
    generated = " ".join(
        [result["seo_title"], result["seo_description"]]
        + result["search_queries"]
        + result["suitable_for"]
        + result["tasks"]
    )
    return sorted(_numbers(generated) - known)


def _unsupported_items(result: dict, product: dict) -> list[str]:
    source = json.dumps(product, ensure_ascii=False).lower()
    unsupported = []
    for item in result["suitable_for"] + result["tasks"]:
        if item.lower() == NO_DATA:
            continue
        words = re.findall(r"[а-яёa-z]{5,}", item.lower())
        if any(w[:5] not in source for w in words):
            unsupported.append(item)
    return unsupported


def _truncate(text: str, limit: int) -> str:
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("."))
    return cut[: end + 1] if end > 0 else cut


def generate_card(product: dict, warnings: list[str]) -> dict:
    messages = build_messages(product)
    result = None
    problems: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = llm.chat(messages, RESULT_SCHEMA)
        try:
            result = _parse_result(raw)
            problems = _length_problems(result)
        except ResultError as e:
            result, problems = None, [str(e)]

        if not problems or attempt == MAX_ATTEMPTS:
            break
        feedback = (
            "Исправь замечания и верни JSON целиком. Если текст слишком длинный, "
            "убери повторы и всё, чего нет во входных данных. Если слишком короткий — "
            "опиши каждую характеристику и назначение из входных данных отдельным "
            "полным предложением с названием и значением, не добавляя новых фактов.\n- "
            + "\n- ".join(problems)
        )
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": feedback},
        ]

    if result is None:
        raise llm.LLMError(f"Модель не вернула корректный ответ: {problems[0]}")

    card_warnings = list(warnings)
    if len(result["seo_description"]) > DESC_MAX:
        result["seo_description"] = _truncate(result["seo_description"], DESC_MAX)
        card_warnings.append(
            "seo_description был слишком длинным и автоматически обрезан по предложению — "
            "проверьте текст."
        )
        problems = [p for p in problems if not p.startswith("seo_description")]
    card_warnings += [f"Не удалось выдержать ограничение: {p}" for p in problems]

    unknown = _unknown_numbers(result, product)
    if unknown:
        card_warnings.append(
            "В тексте есть числа, которых нет во входных данных: "
            + ", ".join(unknown)
            + ". Проверьте вручную."
        )

    unsupported = _unsupported_items(result, product)
    if unsupported:
        card_warnings.append(
            "В блоке для менеджера есть пункты без опоры на входные данные: "
            + "; ".join(f"«{x}»" for x in unsupported)
            + ". Проверьте или удалите."
        )

    missing = missing_specs(product["specs"])
    if missing:
        card_warnings.append("Нужно уточнить у поставщика: " + ", ".join(missing) + ".")

    characteristics = dict(product["specs"])
    for label in missing:
        characteristics[label] = NO_DATA

    return {
        "name": product["name"],
        "manufacturer": product["manufacturer"] or NO_DATA,
        "seo_title": result["seo_title"],
        "seo_description": result["seo_description"],
        "characteristics": characteristics,
        "search_queries": result["search_queries"][:5],
        "commercial": {
            "suitable_for": result["suitable_for"] or [NO_DATA],
            "tasks": result["tasks"] or [NO_DATA],
        },
        "warnings": card_warnings,
    }
