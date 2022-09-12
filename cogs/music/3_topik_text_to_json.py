
from pathlib import Path
import json

source_dir = Path(__file__).parents[0]
map_txt = Path(f"{source_dir}/topik_vocab.txt")
map_json = Path(f"{source_dir}/topik_vocab.json")

vocab = {}
with open(map_txt, encoding="utf-8") as file:
    for line in file:
        worded = line.split(maxsplit=2)
        kr = worded[1]
        en = worded[2].strip()
        print(kr, en)
        vocab[kr] = en

with open(map_json, "w", encoding="utf-8") as file:
    json.dump(vocab, file, indent=4, ensure_ascii=False)

with open(map_json, encoding="utf-8") as file:
    config = json.load(file)

ss = 2
