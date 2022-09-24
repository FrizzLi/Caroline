import json
from pathlib import Path

# freq book
source_dir = Path(__file__).parents[0]
map_txt = Path(f"{source_dir}/data/spreadsheet_data/freq_dict_kor.txt")
map_json = Path(f"{source_dir}/data/spreadsheet_data/freq_dict_kor.json")

NUM = 0
CON = 1
EXA = 2
line_num = NUM

vocab = {}
content = []
with open(map_txt, encoding="utf-8") as file:
    for line in file:
        if line != "\n":
            stripped_line = line.strip()
            if line_num == NUM and stripped_line.isdigit():
                rank = stripped_line

                line_num = CON
            elif line_num == CON:
                line = stripped_line.split()
                content += line
                if len(content) > 3:
                    kr, ro, type_ = content[0], content[1], content[2]
                    en = content[3:]
                    en = " ".join(en)

                    line_num = EXA
                    content.clear()

            elif line_num == EXA:
                stripped_line = stripped_line.replace("•", "")
                stripped_line = stripped_line.strip()
                if "—" in stripped_line:
                    ex_kr, ex_en = stripped_line.split("—")
                    ex_kr = ex_kr.strip()
                    ex_en = ex_en.strip()
                elif " | " not in stripped_line:
                    ex_en += f" {stripped_line}"

            if " | " in stripped_line:
                freq, disp = stripped_line.split(" | ")
                line_num = NUM

                print(rank, kr, ro, type_, en, ex_kr, ex_en, freq, disp)
                vocab[kr] = {
                    "rank": rank,
                    "romanization": ro,
                    "type": type_,
                    "content": en,
                    "example_kr": ex_kr,
                    "example_en": ex_en,
                    "frequency": freq,
                    "disp": disp,
                }

with open(map_json, "w", encoding="utf-8") as file:
    json.dump(vocab, file, indent=4, ensure_ascii=False)
with open(map_json, encoding="utf-8") as file:
    config = json.load(file)

# topik
source_dir = Path(__file__).parents[0]
map_txt = Path(f"{source_dir}/data/topik_vocab.txt")
map_json = Path(f"{source_dir}/data/topik_vocab.json")

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
