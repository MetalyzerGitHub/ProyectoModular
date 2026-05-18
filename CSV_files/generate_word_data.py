import csv
import json
import time
import re
from tqdm import tqdm
import ollama

# Configuration
MODEL = "llama3.2:3b"          # Change if you pulled a different model
INPUT_CSV = "CSV_files/word_data_utf8.csv"
OUTPUT_MEANINGS = "meanings.csv"
OUTPUT_EXAMPLES = "examples.csv"
BATCH_SIZE = 1                 # Process one word at a time; can increase but careful with GPU memory
SLEEP_BETWEEN_CALLS = 0.5      # Seconds to avoid overloading Ollama

def build_prompt(word, pos, translation):
    """Create the prompt for Ollama."""
    prompt = f"""You are a helpful assistant that generates dictionary data.

Word: {word}
Part of speech: {pos}
Common Spanish translation: {translation}

Generate the following in **strict JSON format** only. Do not add any extra text, explanations, or markdown.

{{
  "definitions": [
    {{"en": "English definition (one sentence)", "es": "Spanish definition (una oración)"}}
  ],
  "example": {{
    "en": "Example sentence in English that clearly uses the word.",
    "pos_en": <integer position (1-indexed) of the word in the English sentence>,
    "es": "Spanish translation of the example sentence.",
    "pos_es": <integer position (1-indexed) of the main translation in the Spanish sentence, or 0 if not present>
  }}
}}

Important:
- The example must contain the word exactly as given.
- The Spanish example must be a natural translation.
- If the Spanish sentence does not contain a direct equivalent (e.g., for "it"), set "pos_es" to 0.
- Return ONLY the JSON object, no other text.
"""
    return prompt

def parse_response(response_text):
    """Extract JSON from Ollama response (in case it adds extra text)."""
    # Try to find JSON between curly braces
    match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in response")
    json_str = match.group(0)
    # Clean common issues: trailing commas, etc.
    json_str = re.sub(r',\s*}', '}', json_str)
    return json.loads(json_str)

def process_word(word_id, spelling, pos, translation):
    """Send request to Ollama and return parsed data."""
    prompt = build_prompt(spelling, pos, translation)
    try:
        response = ollama.generate(model=MODEL, prompt=prompt)
        raw = response['response']
        data = parse_response(raw)
        
        # Extract definitions (take first one, or you could loop for multiple)
        def_en = data['definitions'][0]['en']
        def_es = data['definitions'][0]['es']
        
        # Extract example
        ex_en = data['example']['en']
        pos_en = data['example']['pos_en']
        ex_es = data['example']['es']
        pos_es = data['example']['pos_es']
        
        return {
            'def_en': def_en,
            'def_es': def_es,
            'ex_en': ex_en,
            'pos_en': pos_en,
            'ex_es': ex_es,
            'pos_es': pos_es
        }
    except Exception as e:
        print(f"\nError processing word '{spelling}' (ID {word_id}): {e}")
        # Return empty/placeholder data to avoid breaking the pipeline
        return {
            'def_en': '',
            'def_es': '',
            'ex_en': '',
            'pos_en': '',
            'ex_es': '',
            'pos_es': ''
        }

def main():
    # Read input CSV
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
    
    # Prepare output lists
    meanings_rows = []
    examples_rows = []
    
    # Process with progress bar
    #for w in tqdm(words, desc="Processing words"):
    for w in tqdm(words[:10], desc="Processing words"):   # process only first 20 words
        result = process_word(w['id'], w['spelling'], w['pos'], w['translation'])
        
        meanings_rows.append({
            'fk_word': w['id'],
            'def_en': result['def_en'],
            'def_es': result['def_es'],
            'translation': w['translation']   # keep original translation
        })
        
        examples_rows.append({
            'fk_word': w['id'],
            'ex_en': result['ex_en'],
            'word_pos_en': result['pos_en'],
            'ex_es': result['ex_es'],
            'word_pos_esp': result['pos_es']
        })
        
        time.sleep(SLEEP_BETWEEN_CALLS)
    
    # Write meanings CSV
    with open(OUTPUT_MEANINGS, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fk_word', 'def_en', 'def_es', 'translation'])
        writer.writeheader()
        writer.writerows(meanings_rows)
    
    # Write examples CSV
    with open(OUTPUT_EXAMPLES, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['fk_word', 'ex_en', 'word_pos_en', 'ex_es', 'word_pos_esp'])
        writer.writeheader()
        writer.writerows(examples_rows)
    
    print(f"\n✅ Done! Files saved: {OUTPUT_MEANINGS} and {OUTPUT_EXAMPLES}")

if __name__ == "__main__":
    main()