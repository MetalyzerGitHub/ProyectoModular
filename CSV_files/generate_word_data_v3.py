import csv
import json
import re
import time
import os
from tqdm import tqdm
import ollama

# ── Configuration ──────────────────────────────────────────────────────────────
MODEL        = "llama3.2:3b"
INPUT_CSV    = "CSV_files/word_data_utf8.csv"
OUTPUT_MEANINGS  = "CSV_files/meanings.csv"
OUTPUT_EXAMPLES  = "CSV_files/examples.csv"
SLEEP        = 0          # seconds between requests (increase if model gets unstable)
MAX_RETRIES  = 3
# ──────────────────────────────────────────────────────────────────────────────


# ── Prompt ────────────────────────────────────────────────────────────────────
def build_prompt(word: str, pos: str, translation: str) -> str:
    primary_trans = translation.split('/')[0].strip()
    return f"""You are a bilingual dictionary. Reply with a single JSON object and nothing else.

Given:
  word: "{word}"
  part_of_speech: "{pos}"
  spanish_translations: "{translation}"
  primary_translation: "{primary_trans}"

Rules:
1. "def_en" — short English definition (one sentence).
2. "def_es" — short Spanish definition (one sentence).
3. "ex_en"  — one natural English example sentence that uses the word "{word}".
4. "ex_es"  — Spanish translation of that sentence; include "{primary_trans}" when grammatically possible.
5. "pos_es" — 1-indexed position of "{primary_trans}" in "ex_es", or 0 if it is absent.

Respond ONLY with valid JSON, no markdown, no extra text:
{{
  "def_en": "...",
  "def_es": "...",
  "ex_en": "...",
  "ex_es": "...",
  "pos_es": 0
}}"""


# ── JSON extraction ────────────────────────────────────────────────────────────
def extract_json(raw: str) -> dict:
    """
    Try multiple strategies to pull a JSON object out of the model response.
    Handles: plain JSON, markdown fences, leading/trailing prose.
    """
    # 1. Strip markdown code fences  ```json ... ```  or  ``` ... ```
    fenced = re.sub(r'```(?:json)?\s*', '', raw).strip()

    # 2. Try to parse the whole cleaned string first (cheapest path)
    for candidate in (fenced, raw.strip()):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. Pull out the first {...} block (handles leading/trailing prose)
    match = re.search(r'\{[^{}]*\}', fenced, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # 4. Greedy search for nested braces (model sometimes emits extra nesting)
    match = re.search(r'\{.*\}', fenced, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"No valid JSON found in response:\n{raw[:300]}")


# ── Word position helpers ─────────────────────────────────────────────────────
_PUNCT = re.compile(r'[^\wáéíóúüñÁÉÍÓÚÜÑ]')

def _tokenize(sentence: str) -> list[str]:
    return [_PUNCT.sub('', w).lower() for w in sentence.split()]

def compute_pos_en(sentence: str, word: str) -> int:
    tokens = _tokenize(sentence)
    target = word.lower()
    for i, t in enumerate(tokens, 1):
        if t == target:
            return i
    return 0

def compute_pos_es(sentence: str, translation: str) -> int:
    primary = translation.split('/')[0].strip().lower()
    tokens = _tokenize(sentence)
    for i, t in enumerate(tokens, 1):
        if t == primary:
            return i
    return 0


# ── Per-word processing ───────────────────────────────────────────────────────
def process_word(spelling: str, pos: str, translation: str) -> dict:
    prompt = build_prompt(spelling, pos, translation)
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # format="json" tells Ollama to constrain output to valid JSON
            # (supported in ollama-python >= 0.2; falls back gracefully if not)
            try:
                response = ollama.generate(model=MODEL, prompt=prompt, format="json")
            except TypeError:
                # Older ollama-python versions don't accept `format`
                response = ollama.generate(model=MODEL, prompt=prompt)

            raw  = response.get('response', '')
            data = extract_json(raw)

            def_en = data.get('def_en', '').strip()
            def_es = data.get('def_es', '').strip()
            ex_en  = data.get('ex_en',  '').strip()
            ex_es  = data.get('ex_es',  '').strip()

            pos_en = compute_pos_en(ex_en, spelling)
            pos_es = compute_pos_es(ex_es, translation)

            return {
                'def_en': def_en, 'def_es': def_es,
                'ex_en':  ex_en,  'pos_en': pos_en,
                'ex_es':  ex_es,  'pos_es': pos_es,
            }

        except Exception as e:
            last_error = e
            print(f"\n  ⚠ Attempt {attempt}/{MAX_RETRIES} failed for '{spelling}': {e}")
            time.sleep(2 ** attempt)   # exponential back-off: 2 s, 4 s, 8 s

    print(f"\n  ✗ All attempts failed for '{spelling}'. Storing empty row.")
    return {'def_en': '', 'def_es': '', 'ex_en': '', 'pos_en': 0, 'ex_es': '', 'pos_es': 0}


# ── Progress tracking helpers ─────────────────────────────────────────────────
def load_processed_ids(filepath: str, id_column: str) -> set[int]:
    """Return the set of word IDs already written to an output CSV."""
    if not os.path.exists(filepath):
        return set()
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return {int(row[id_column]) for row in reader if row.get(id_column)}

def ensure_csv_header(filepath: str, fieldnames: list[str]) -> None:
    """Write the header row only if the file doesn't exist yet."""
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # ── Load input ────────────────────────────────────────────────────────────
    words = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            words.append({
                'id':          int(row['id_word']),
                'spelling':    row['Spelling'],
                'pos':         row['DomPoS'],
                'translation': row['meaning'],
            })

    # ── Resume support: find already-processed IDs ────────────────────────────
    done_meanings  = load_processed_ids(OUTPUT_MEANINGS, 'fk_word')
    done_examples  = load_processed_ids(OUTPUT_EXAMPLES, 'fk_word')
    done_ids       = done_meanings & done_examples   # only skip if BOTH were written

    pending = [w for w in words if w['id'] not in done_ids]
    skipped = len(words) - len(pending)
    if skipped:
        print(f"ℹ Resuming — skipping {skipped} already-processed word(s).")

    # ── Ensure output files have headers ─────────────────────────────────────
    ensure_csv_header(OUTPUT_MEANINGS, ['fk_word', 'def_en', 'def_es', 'translation'])
    ensure_csv_header(OUTPUT_EXAMPLES, ['fk_word', 'ex_en', 'word_pos_en', 'ex_es', 'word_pos_esp'])

    # ── Process & stream-write results ────────────────────────────────────────
    with (
        open(OUTPUT_MEANINGS, 'a', encoding='utf-8', newline='') as f_mean,
        open(OUTPUT_EXAMPLES, 'a', encoding='utf-8', newline='') as f_exmp,
    ):
        w_mean = csv.DictWriter(f_mean, fieldnames=['fk_word', 'def_en', 'def_es', 'translation'])
        w_exmp = csv.DictWriter(f_exmp, fieldnames=['fk_word', 'ex_en', 'word_pos_en', 'ex_es', 'word_pos_esp'])

        for w in tqdm(pending, desc="Processing", unit="word"):
            result = process_word(w['spelling'], w['pos'], w['translation'])

            w_mean.writerow({
                'fk_word':     w['id'],
                'def_en':      result['def_en'],
                'def_es':      result['def_es'],
                'translation': w['translation'],
            })
            w_exmp.writerow({
                'fk_word':      w['id'],
                'ex_en':        result['ex_en'],
                'word_pos_en':  result['pos_en'],
                'ex_es':        result['ex_es'],
                'word_pos_esp': result['pos_es'],
            })

            # Flush both files so data survives a crash / keyboard interrupt
            f_mean.flush()
            f_exmp.flush()

            if SLEEP:
                time.sleep(SLEEP)

    print(f"\n✅ Done. Output: {OUTPUT_MEANINGS}, {OUTPUT_EXAMPLES}")


if __name__ == "__main__":
    main()