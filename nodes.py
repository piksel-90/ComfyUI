from __future__ import annotations

from .translator import TranslationError, TranslationSettings, translate_prompt


BACKENDS = ["google_free", "deepl_en-us", "libretranslate"]


def _settings(backend, endpoint, api_key, preserve_prompt_syntax, normalize_en_us, timeout):
    return TranslationSettings(
        backend=backend,
        endpoint=endpoint.strip(),
        api_key=api_key.strip(),
        preserve_prompt_syntax=bool(preserve_prompt_syntax),
        normalize_en_us=bool(normalize_en_us),
        timeout=int(timeout),
    )


class PLToENPrompt:
    """Translate a Polish image-generation prompt into American English."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt_pl": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "default": "",
                        "tooltip": "Prompt po polsku. Wynik wyjdzie jako STRING en-US.",
                    },
                ),
                "backend": (BACKENDS, {"default": "google_free"}),
            },
            "optional": {
                "endpoint": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Opcjonalny URL dla LibreTranslate lub własnego endpointu DeepL.",
                    },
                ),
                "api_key": (
                    "STRING",
                    {
                        "default": "",
                        "tooltip": "Opcjonalny klucz API. Dla DeepL lepiej użyć zmiennej DEEPL_AUTH_KEY.",
                    },
                ),
                "preserve_prompt_syntax": ("BOOLEAN", {"default": True}),
                "normalize_en_us": ("BOOLEAN", {"default": True}),
                "timeout": ("INT", {"default": 20, "min": 3, "max": 120, "step": 1}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt_en", "status")
    OUTPUT_TOOLTIPS = (
        "Przetłumaczony prompt en-US; można podłączyć do wejścia text w CLIP Text Encode.",
        "Informacja o użytym backendzie.",
    )
    FUNCTION = "translate"
    CATEGORY = "Piksel90/Prompt"
    DESCRIPTION = "Tłumaczy prompt z polskiego na en-US bez ładowania modelu językowego do VRAM."

    def translate(
        self,
        prompt_pl,
        backend,
        endpoint="",
        api_key="",
        preserve_prompt_syntax=True,
        normalize_en_us=True,
        timeout=20,
    ):
        settings = _settings(
            backend, endpoint, api_key, preserve_prompt_syntax, normalize_en_us, timeout
        )
        try:
            prompt_en = translate_prompt(prompt_pl, settings)
        except TranslationError as exc:
            raise RuntimeError(f"PL → en-US translation failed: {exc}") from exc
        return (prompt_en, f"PL → en-US | {backend}")


class PLToENCLIPTextEncode:
    """Translate Polish text and encode it with the supplied ComfyUI CLIP object."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP", {"tooltip": "CLIP z Checkpoint Loader / CLIP Loader."}),
                "prompt_pl": (
                    "STRING",
                    {
                        "multiline": True,
                        "dynamicPrompts": True,
                        "default": "",
                        "tooltip": "Wpisz prompt po polsku. Node tłumaczy go przed tokenizacją CLIP.",
                    },
                ),
                "backend": (BACKENDS, {"default": "google_free"}),
            },
            "optional": {
                "endpoint": ("STRING", {"default": ""}),
                "api_key": ("STRING", {"default": ""}),
                "preserve_prompt_syntax": ("BOOLEAN", {"default": True}),
                "normalize_en_us": ("BOOLEAN", {"default": True}),
                "timeout": ("INT", {"default": 20, "min": 3, "max": 120, "step": 1}),
            },
        }

    RETURN_TYPES = ("CONDITIONING", "STRING")
    RETURN_NAMES = ("conditioning", "prompt_en")
    OUTPUT_TOOLTIPS = (
        "Conditioning gotowy do KSampler / guidance nodes.",
        "Dokładny tekst en-US przekazany do CLIP.",
    )
    FUNCTION = "encode"
    CATEGORY = "Piksel90/Conditioning"
    DESCRIPTION = (
        "Zamiennik CLIP Text Encode: przyjmuje prompt po polsku, tłumaczy do en-US i koduje CLIP."
    )

    def encode(
        self,
        clip,
        prompt_pl,
        backend,
        endpoint="",
        api_key="",
        preserve_prompt_syntax=True,
        normalize_en_us=True,
        timeout=20,
    ):
        if clip is None:
            raise RuntimeError("CLIP input is invalid: None")

        settings = _settings(
            backend, endpoint, api_key, preserve_prompt_syntax, normalize_en_us, timeout
        )
        try:
            prompt_en = translate_prompt(prompt_pl, settings)
        except TranslationError as exc:
            raise RuntimeError(f"PL → en-US translation failed: {exc}") from exc

        tokens = clip.tokenize(prompt_en)
        if hasattr(clip, "encode_from_tokens_scheduled"):
            conditioning = clip.encode_from_tokens_scheduled(tokens)
        else:
            cond, pooled = clip.encode_from_tokens(tokens, return_pooled=True)
            conditioning = [[cond, {"pooled_output": pooled}]]

        return (conditioning, prompt_en)


NODE_CLASS_MAPPINGS = {
    "Piksel90_PLToENPrompt": PLToENPrompt,
    "Piksel90_PLToENCLIPTextEncode": PLToENCLIPTextEncode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Piksel90_PLToENPrompt": "🇵🇱 → 🇺🇸 Prompt Translator",
    "Piksel90_PLToENCLIPTextEncode": "🇵🇱 → 🇺🇸 CLIP Text Encode",
}
