from pathlib import Path

from konlpy.tag import Okt

okt = Okt()

source_dir = Path(__file__).parents[0]
text_file_name = Path(f"{source_dir}/data/text_to_vocab.txt")
vocab_file_name = Path(f"{source_dir}/data/reading_vocab.txt")

with open(text_file_name, encoding="utf-8") as file:
    korean_text = file.read()
    print('Tokenizing Korean text...', end='')
    tokenized_text = okt.pos(korean_text, norm=True, stem=True)
    print('Done')

with open(vocab_file_name, "w", encoding="utf-8") as file:
    for token in tokenized_text:
        try:
            if (token[1] == 'Punctuation' or token[1] == 'Foreign'):
                print(f'Skipping garbage... ({token}')
                continue
        except Exception as e:
            print('Error skipping token:', e)

        file.write(f"{token[0]} {token[1]}\n")
