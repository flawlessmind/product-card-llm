import json

NO_DATA = "данных нет"

EXPECTED_SPECS = [
    ("диапазон измерений", ["диапазон"]),
    ("класс точности", ["класс точности", "погрешность"]),
    ("питание", ["питание"]),
    ("тип корпуса", ["корпус"]),
    ("присоединение / интерфейсы", ["присоединение", "интерфейс", "выходной сигнал"]),
    ("степень защиты", ["степень защиты", "ip"]),
    ("рабочая температура", ["температур"]),
]


class InvalidProductError(ValueError):
    pass


def parse_product(raw: str):
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise InvalidProductError(f"Некорректный JSON: {e}")


def _clean_str(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def normalize(data) -> tuple[dict, list[str]]:
    if not isinstance(data, dict):
        raise InvalidProductError("Ожидался JSON-объект с данными о товаре.")

    warnings: list[str] = []

    name = _clean_str(data.get("name"))
    if not name:
        raise InvalidProductError("Не заполнено обязательное поле «name».")

    manufacturer = _clean_str(data.get("manufacturer"))
    if not manufacturer:
        warnings.append("Не указан производитель (manufacturer).")

    raw_specs = data.get("specs")
    if raw_specs is None:
        raw_specs = {}
    if not isinstance(raw_specs, dict):
        raise InvalidProductError("Поле «specs» должно быть объектом «название: значение».")

    specs: dict[str, str] = {}
    for key, value in raw_specs.items():
        key = str(key).strip()
        text = "" if value is None else str(value).strip()
        if not key:
            continue
        if not text:
            warnings.append(f"Характеристика «{key}» не заполнена — пропущена.")
            continue
        specs[key] = text

    description = _clean_str(data.get("description"))
    if not description:
        warnings.append("Нет текстового описания (description).")

    if not specs and not description:
        raise InvalidProductError("Нет ни характеристик, ни описания — писать карточку не из чего.")

    product = {
        "name": name,
        "manufacturer": manufacturer,
        "specs": specs,
        "description": description,
    }
    return product, warnings


def missing_specs(specs: dict[str, str]) -> list[str]:
    keys = [k.lower() for k in specs]
    return [
        label
        for label, aliases in EXPECTED_SPECS
        if not any(alias in key for alias in aliases for key in keys)
    ]
