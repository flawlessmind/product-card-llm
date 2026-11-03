import argparse
import json
import sys
from pathlib import Path

from cardgen import config
from cardgen.generator import generate_card
from cardgen.llm import LLMError
from cardgen.render import to_markdown
from cardgen.validation import InvalidProductError, normalize, parse_product


def process_file(path: Path, out_dir: Path) -> bool:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"[{path.name}] Не удалось прочитать файл: {e}", file=sys.stderr)
        return False

    try:
        product, warnings = normalize(parse_product(raw))
        card = generate_card(product, warnings)
    except (InvalidProductError, LLMError) as e:
        print(f"[{path.name}] Ошибка: {e}", file=sys.stderr)
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{path.stem}.json").write_text(
        json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    markdown = to_markdown(card)
    (out_dir / f"{path.stem}.md").write_text(markdown, encoding="utf-8")

    print(markdown)
    print(f"Сохранено: {out_dir / (path.stem + '.md')}\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Черновик карточки товара по данным о приборе.")
    parser.add_argument("files", nargs="+", type=Path, help="JSON-файлы с данными о товаре")
    parser.add_argument("-o", "--out", type=Path, default=Path("output"), help="папка для результата")
    args = parser.parse_args()

    print(f"Модель: {config.OLLAMA_MODEL} ({config.OLLAMA_HOST})\n")
    results = [process_file(p, args.out) for p in args.files]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
