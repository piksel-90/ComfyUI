# ComfyUI PL → en-US Prompt Translator

Lekki custom node do ComfyUI, który tłumaczy prompt **z polskiego na angielski en-US** bez ładowania LLM/VLM do VRAM.

Projekt zawiera dwa nody:

- **🇵🇱 → 🇺🇸 Prompt Translator** — wejście `prompt_pl`, wyjście `prompt_en` typu `STRING`. Można je podłączyć do `text` w standardowym `CLIP Text Encode`.
- **🇵🇱 → 🇺🇸 CLIP Text Encode** — zamiennik standardowego `CLIP Text Encode`. Wpisujesz prompt po polsku bezpośrednio w jego duże pole tekstowe; node tłumaczy go i koduje dostarczonym `CLIP`, zwracając `CONDITIONING` oraz tekst `prompt_en` użyty faktycznie do tokenizacji.

## Dlaczego ta wersja jest lekka

Node **nie ładuje żadnego modelu tłumaczeniowego do RAM/VRAM** i nie wymaga `transformers`, QwenVL, torchowych modeli językowych ani osobnego loadera HF. Domyślny backend korzysta z prostego żądania HTTP.

## Backendy

### `google_free` — domyślny

Nie wymaga klucza API. Korzysta z publicznego endpointu tłumaczenia Google. Target jest `en`; wynik jest następnie ostrożnie normalizowany do typowych form en-US (`colour → color`, `grey → gray`, itd.).

To wygodny backend do lokalnego workflow, ale endpoint nie ma gwarantowanego SLA i może kiedyś ulec zmianie.

### `deepl_en-us`

Najlepszy wariant, jeżeli zależy Ci na **jawnie ustawionym `EN-US`**. Wymaga klucza DeepL.

Najbezpieczniej ustawić go poza workflow:

```bash
set DEEPL_AUTH_KEY=twoj_klucz
```

Windows PowerShell:

```powershell
$env:DEEPL_AUTH_KEY="twoj_klucz"
```

Można też wpisać `api_key` w nodzie, ale wtedy klucz może zostać zapisany w JSON-ie workflow.

### `libretranslate`

Dla własnego serwera LibreTranslate. Domyślny adres:

```text
http://127.0.0.1:5000
```

W polu `endpoint` możesz podać inny host. Node sam dopisze `/translate`, jeśli trzeba.

## Ochrona składni promptu

Przy włączonym `preserve_prompt_syntax` node maskuje przed tłumaczeniem elementy, których tłumacz nie powinien ruszać, m.in.:

- `<lora:nazwa:1.0>` i inne tagi w nawiasach ostrych,
- `embedding:nazwa`,
- wildcardy `__camera__`,
- adresy URL,
- nazwy plików modeli `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin`.

Wagi typu `(czerwona sukienka:1.25)` nie są blokowane — tekst wewnątrz może zostać przetłumaczony, a wartość wagi pozostaje częścią promptu.

## Instalacja

W katalogu `ComfyUI/custom_nodes`:

```bash
git clone https://github.com/piksel-90/ComfyUI.git ComfyUI-PL-EN-Translator
cd ComfyUI-PL-EN-Translator
python -m pip install -r requirements.txt
```

Uruchom ponownie ComfyUI.

Nody znajdziesz w:

```text
Piksel90 / Prompt
Piksel90 / Conditioning
```

## Najprostszy workflow

Zamiast zwykłego `CLIP Text Encode` dodaj:

```text
Checkpoint Loader
      │ clip
      ▼
🇵🇱 → 🇺🇸 CLIP Text Encode
      │ conditioning
      ▼
KSampler / guidance
```

Prompt wpisujesz po polsku bezpośrednio w nodzie. Wyjście `prompt_en` pokazuje dokładny angielski tekst przekazany do CLIP.

## Uwagi

- Tłumaczenie wymaga dostępu sieciowego, chyba że używasz lokalnego LibreTranslate.
- Błąd sieci lub backendu zatrzyma wykonanie noda czytelnym wyjątkiem zamiast przepuszczać polski tekst po cichu.
- `requests` jest jedyną dodatkową zależnością projektu.
- Kod CLIP wykorzystuje aktualne `clip.tokenize(...)` + `clip.encode_from_tokens_scheduled(...)` i ma fallback dla starszego API ComfyUI.

## Licencja

MIT
