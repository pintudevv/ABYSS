import json, shutil
from pathlib import Path

results = Path('backend/results')

# Remove task dirs that have no classification_result.json (empty/incomplete)
removed = 0
for p in list(results.iterdir()):
    if p.is_dir():
        if not (p / 'classification_result.json').exists():
            shutil.rmtree(p)
            print(f'Removed incomplete: {p.name}')
            removed += 1

# Rebuild hash cache from only valid dirs
cache = {}
for p in results.iterdir():
    if p.is_dir() and (p / 'classification_result.json').exists():
        try:
            data = json.loads((p / 'classification_result.json').read_text())
            sha = data.get('sha256', '')
            fname = data.get('file', '?')
            if sha:
                cache[sha] = p.name
                print(f'Kept: {p.name} ({fname})')
        except Exception as e:
            print(f'Error reading {p.name}: {e}')

cache_file = results / 'hash_cache.json'
cache_file.write_text(json.dumps(cache, indent=2))
print(f'Cache rebuilt with {len(cache)} entries. Removed {removed} incomplete dirs.')
