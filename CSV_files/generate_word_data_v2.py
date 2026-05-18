import csv
import json
import re
import time
from tqdm import tqdm
import ollama

MODEL = "llama3.2:3b"
INPUT_CSV = "CSV_files/word_data_utf8.csv"
OUTPUT_MEANINGS = "CSV_files/meanings.csv"
OUTPUT_EXAMPLES = "CSV_files/examples.csv"
SLEEP = 0

def build_prompt(word, pos, translation):
    """Prompt that forces inclusion of the translation."""
    # For words with multiple translations (like "a" -> "un/una"), pick the first one as primary.
    primary_trans = translation.split('/')[0].strip()
    
    prompt = f"""You are a dictionary assistant. Generate JSON only.

Word: {word}
Part of speech: {pos}
Spanish translations: {translation} (use "{primary_trans}" as the main translation when possible)

Generate a JSON object with:
- One English definition and one Spanish definition.
- One example sentence in English that clearly uses the word "{word}".
- The Spanish translation of that example, and you MUST include the word "{primary_trans}" in the Spanish sentence (unless the word has no direct equivalent, like "it" or "a" in some contexts – then use 0 for position).

Format EXACTLY as below, with no extra text:

{{
  "def_en": "English definition",
  "def_es": "Spanish definition",
  "ex_en": "English sentence",
  "ex_es": "Spanish sentence that includes '{primary_trans}' (if possible, otherwise omit and set pos_es=0)",
  "pos_es": <integer position of '{primary_trans}' in the Spanish sentence, 1-indexed, or 0 if absent>
}}

Important: Do not include any other fields. Do not add explanations.
"""
    return prompt

def compute_word_position_en(sentence, target_word):
    """Return 1-indexed position of target_word in sentence, or 0 if not found."""
    words = sentence.split()
    for i, w in enumerate(words, start=1):
        if w.lower() == target_word.lower():
            return i
    # Also try removing punctuation
    cleaned = re.sub(r'[^\w\s]', '', sentence).split()
    for i, w in enumerate(cleaned, start=1):
        if w.lower() == target_word.lower():
            return i
    return 0

def compute_word_position_es(sentence, translation):
    """Return 1-indexed position of the primary translation in Spanish sentence."""
    # translation may contain slashes, e.g., "un/una". Take the first part.
    primary = translation.split('/')[0].strip()
    words = sentence.split()
    for i, w in enumerate(words, start=1):
        # Remove punctuation for comparison
        clean_w = re.sub(r'[^\wáéíóúüñ]', '', w.lower())
        if clean_w == primary.lower():
            return i
    return 0

def process_word(word_id, spelling, pos, translation):
    prompt = build_prompt(spelling, pos, translation)
    for attempt in range(3):  # retry up to 3 times
        try:
            response = ollama.generate(model=MODEL, prompt=prompt)
            raw = response['response']
            # Extract JSON
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if not match:
                raise ValueError("No JSON found")
            data = json.loads(match.group(0))
            
            # Get fields
            def_en = data.get('def_en', '')
            def_es = data.get('def_es', '')
            ex_en = data.get('ex_en', '')
            ex_es = data.get('ex_es', '')
            pos_es_claimed = data.get('pos_es', 0)
            
            # Compute actual positions
            pos_en = compute_word_position_en(ex_en, spelling)
            # For Spanish, recompute using the original translation (more reliable)
            pos_es = compute_word_position_es(ex_es, translation)
            
            return {
                'def_en': def_en,
                'def_es': def_es,
                'ex_en': ex_en,
                'pos_en': pos_en,
                'ex_es': ex_es,
                'pos_es': pos_es
            }
        except Exception as e:
            print(f"\nAttempt {attempt+1} failed for '{spelling}': {e}")
            time.sleep(2)
    # Fallback empty
    return {
        'def_en': '', 'def_es': '', 'ex_en': '', 'pos_en': 0,
        'ex_es': '', 'pos_es': 0
    }

def main():
    # Read input
    words = []
    with open(INPUT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append({
                'id': int(row['id_word']),
                'spelling': row['Spelling'],
                'pos': row['DomPoS'],
                'translation': row['meaning']
            })
    
    meanings = []
    examples = []
    
    for w in tqdm(words, desc="Processing"):  # agregar [:10] para hacer una pruba
        result = process_word(w['id'], w['spelling'], w['pos'], w['translation'])
        meanings.append({
            'fk_word': w['id'],
            'def_en': result['def_en'],
            'def_es': result['def_es'],
            'translation': w['translation']
        })
        examples.append({
            'fk_word': w['id'],
            'ex_en': result['ex_en'],
            'word_pos_en': result['pos_en'],
            'ex_es': result['ex_es'],
            'word_pos_esp': result['pos_es']
        })
        time.sleep(SLEEP)
    
    # Write CSV files
    with open(OUTPUT_MEANINGS, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fk_word', 'def_en', 'def_es', 'translation'])
        writer.writeheader()
        writer.writerows(meanings)
    
    with open(OUTPUT_EXAMPLES, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fk_word', 'ex_en', 'word_pos_en', 'ex_es', 'word_pos_esp'])
        writer.writeheader()
        writer.writerows(examples)
    
    print(f"\n✅ Done. Files: {OUTPUT_MEANINGS}, {OUTPUT_EXAMPLES}")

if __name__ == "__main__":
    main()