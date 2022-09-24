
from pathlib import Path

from konlpy.tag import Okt

vocabulary = []
okt = Okt()

source_dir = Path(__file__).parents[0]
fre_json = Path(f"{source_dir}/data/text_to_vocab.txt")

with open(fre_json, encoding="utf-8") as f:
    korean_text = f.read()
    print('Tokenizing Korean text...', end='')
    tokenized_text = okt.pos(korean_text, norm=True, stem=True)
    print('Done')

for token in tokenized_text:
    try:
        if (token[1] == 'Punctuation' or token[1] == 'Foreign'):
            print(f'Skipping garbage... ({token}')
            continue
    except Exception as e:
        print('Error skipping token:', e)

    vocabulary.append({
        'Word': token[0],
        'Type': token[1],
    })
    print(token[0], token[1])
