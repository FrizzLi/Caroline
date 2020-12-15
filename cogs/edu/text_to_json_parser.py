import glob, os, json

# select directory
dir_name = input(f"Which directory you want to make json from?\n\
{[f for f in os.listdir() if f.startswith('vocab')]}\n")
paths = glob.glob(dir_name + "/**/*.txt", recursive=True)

# select keys and values
with open(paths[0], encoding="utf-8") as f:
    first_line = f.readline()
if not first_line:
    first_line = "<NO_CONTENT>"
reverse_lang = input(f"First line looks like this: {first_line}\
Do you want to switch keys and vals? (0/1)\n")

# create json files from text files
for path in paths: 
    with open(path, encoding="utf-8") as f:
        vocabd = {}
        for line in f:
            key, val = line.split(" - ")
            val = val.strip()
            key, val = (val, key) if int(reverse_lang) else (key, val)
            vocabd[key] = val

    if vocabd:
        with open(path + '.json', "w", encoding="utf-8") as f:
            json.dump(vocabd, f, indent=4, sort_keys=True, ensure_ascii=False)

