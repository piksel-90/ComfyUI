from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from typing import Dict, Tuple

import requests


class TranslationError(RuntimeError):
    """Raised when a translation backend cannot return a usable result."""


_PROTECTED_PATTERNS = [
    r"<[^<>\n]+>",
    r"__[^\n]+?__",
    r"\bembedding:[^\s,;]+",
    r"https?://[^\s]+",
    r"\b[^\s,;]+\.(?:safetensors|ckpt|pt|pth|bin)\b",
]
_PROTECTED_RE = re.compile("|".join(f"(?:{p})" for p in _PROTECTED_PATTERNS), re.IGNORECASE)

_US_SPELLINGS = {
    "colour": "color",
    "colours": "colors",
    "favourite": "favorite",
    "favourites": "favorites",
    "centre": "center",
    "centres": "centers",
    "theatre": "theater",
    "theatres": "theaters",
    "grey": "gray",
    "travelling": "traveling",
    "jewellery": "jewelry",
}
_US_RE = re.compile(r"\b(" + "|".join(map(re.escape, _US_SPELLINGS)) + r")\b", re.IGNORECASE)


@dataclass(frozen=True)
class TranslationSettings:
    backend: str = "google_free"
    endpoint: str = ""
    api_key: str = ""
    preserve_prompt_syntax: bool = True
    normalize_en_us: bool = True
    timeout: int = 20


def _match_case(source: str, replacement: str) -> str:
    if source.isupper():
        return replacement.upper()
    if source[:1].isupper():
        return replacement.capitalize()
    return replacement


def normalize_american_english(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        original = match.group(0)
        return _match_case(original, _US_SPELLINGS[original.lower()])

    return _US_RE.sub(repl, text)


def protect_prompt_syntax(text: str) -> Tuple[str, Dict[str, str]]:
    protected: Dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        key = f"ZXQPRESERVE{len(protected):04d}QXZ"
        protected[key] = match.group(0)
        return key

    return _PROTECTED_RE.sub(repl, text), protected


def restore_prompt_syntax(text: str, protected: Dict[str, str]) -> str:
    if not protected:
        return text

    text = re.sub(
        r"ZXQ\s*PRESERVE\s*(\d{4})\s*QXZ",
        lambda m: f"ZXQPRESERVE{m.group(1)}QXZ",
        text,
        flags=re.IGNORECASE,
    )
    for key, original in protected.items():
        text = re.sub(re.escape(key), lambda _m, value=original: value, text, flags=re.IGNORECASE)
    return text


def _google_free(text: str, timeout: int) -> str:
    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "pl", "tl": "en", "dt": "t", "q": text},
        timeout=timeout,
        headers={"User-Agent": "ComfyUI-PL-EN-Translator/1.0"},
    )
    response.raise_for_status()
    payload = response.json()
    if not payload or not payload[0]:
        raise TranslationError("Google Free returned an empty response.")
    translated = "".join(part[0] for part in payload[0] if part and part[0])
    if not translated.strip():
        raise TranslationError("Google Free returned an empty translation.")
    return translated


def _libretranslate(text: str, endpoint: str, api_key: str, timeout: int) -> str:
    base = (endpoint or "http://127.0.0.1:5000").rstrip("/")
    url = base if base.endswith("/translate") else f"{base}/translate"
    body = {"q": text, "source": "pl", "target": "en", "format": "text"}
    if api_key:
        body["api_key"] = api_key
    response = requests.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    translated = payload.get("translatedText", "") if isinstance(payload, dict) else ""
    if not translated.strip():
        raise TranslationError("LibreTranslate returned an empty translation.")
    return html.unescape(translated)


def _deepl(text: str, api_key: str, endpoint: str, timeout: int) -> str:
    auth_key = api_key or os.getenv("DEEPL_AUTH_KEY", "")
    if not auth_key:
        raise TranslationError(
            "DeepL requires an API key. Set DEEPL_AUTH_KEY or enter api_key in the node."
        )

    if endpoint:
        url = endpoint.rstrip("/")
        if not url.endswith("/v2/translate"):
            url += "/v2/translate"
    else:
        host = "https://api-free.deepl.com" if auth_key.endswith(":fx") else "https://api.deepl.com"
        url = f"{host}/v2/translate"

    response = requests.post(
        url,
        data={"text": text, "source_lang": "PL", "target_lang": "EN-US"},
        headers={"Authorization": f"DeepL-Auth-Key {auth_key}"},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    translations = payload.get("translations", []) if isinstance(payload, dict) else []
    translated = translations[0].get("text", "") if translations else ""
    if not translated.strip():
        raise TranslationError("DeepL returned an empty translation.")
    return translated


def translate_prompt(text: str, settings: TranslationSettings) -> str:
    if not isinstance(text, str):
        raise TranslationError("Prompt must be a string.")
    if not text.strip():
        return text

    working = text
    protected: Dict[str, str] = {}
    if settings.preserve_prompt_syntax:
        working, protected = protect_prompt_syntax(working)

    backend = settings.backend.strip().lower()
    try:
        if backend == "google_free":
            translated = _google_free(working, settings.timeout)
        elif backend == "libretranslate":
            translated = _libretranslate(working, settings.endpoint, settings.api_key, settings.timeout)
        elif backend == "deepl_en-us":
            translated = _deepl(working, settings.api_key, settings.endpoint, settings.timeout)
        else:
            raise TranslationError(f"Unsupported backend: {settings.backend}")
    except requests.RequestException as exc:
        raise TranslationError(f"Translation request failed: {exc}") from exc
    except ValueError as exc:
        raise TranslationError(f"Translation backend returned invalid JSON: {exc}") from exc

    translated = restore_prompt_syntax(translated, protected)
    if settings.normalize_en_us and backend != "deepl_en-us":
        translated = normalize_american_english(translated)
    return translated.strip()
