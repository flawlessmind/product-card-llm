def to_markdown(card: dict) -> str:
    lines = [f"# {card['name']}", "", f"**Производитель:** {card['manufacturer']}", ""]

    if card["warnings"]:
        lines += ["## Требует внимания", ""]
        lines += [f"- {w}" for w in card["warnings"]]
        lines.append("")

    lines += [
        "## SEO-заголовок",
        "",
        card["seo_title"],
        "",
        f"_{len(card['seo_title'])} симв._",
        "",
        "## SEO-описание",
        "",
        card["seo_description"],
        "",
        f"_{len(card['seo_description'])} симв._",
        "",
        "## Ключевые характеристики",
        "",
    ]
    lines += [f"- **{k}:** {v}" for k, v in card["characteristics"].items()]

    lines += ["", "## Поисковые запросы", ""]
    lines += [f"- {q}" for q in card["search_queries"]]

    lines += ["", "## Блок для менеджера", "", "**Кому подходит:**", ""]
    lines += [f"- {x}" for x in card["commercial"]["suitable_for"]]
    lines += ["", "**Какие задачи решает:**", ""]
    lines += [f"- {x}" for x in card["commercial"]["tasks"]]

    return "\n".join(lines) + "\n"
