import requests

from . import config


class LLMError(RuntimeError):
    pass


def chat(messages: list[dict], schema: dict) -> str:
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "format": schema,
        "options": {"temperature": 0.2},
    }
    try:
        resp = requests.post(
            f"{config.OLLAMA_HOST}/api/chat", json=payload, timeout=config.OLLAMA_TIMEOUT
        )
    except requests.ConnectionError:
        raise LLMError(
            f"Не удалось подключиться к Ollama ({config.OLLAMA_HOST}). "
            "Проверьте, что сервер запущен: `ollama serve`."
        )
    except requests.Timeout:
        raise LLMError(f"Ollama не ответила за {config.OLLAMA_TIMEOUT} с.")

    if resp.status_code == 404:
        raise LLMError(
            f"Модель «{config.OLLAMA_MODEL}» не найдена. Загрузите её: "
            f"`ollama pull {config.OLLAMA_MODEL}`."
        )
    if not resp.ok:
        raise LLMError(f"Ollama вернула ошибку {resp.status_code}: {resp.text[:300]}")

    try:
        return resp.json()["message"]["content"]
    except (ValueError, KeyError, TypeError):
        raise LLMError("Неожиданный формат ответа Ollama.")
