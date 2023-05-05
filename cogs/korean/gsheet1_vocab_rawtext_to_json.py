"""Takes and transforms book's raw vocabulary text into json file."""

import json
from pathlib import Path


def create_freq_json():
    """Creates freq json vocabulary file out from raw text.

    Takes and transforms raw text of freq vocabulary into json file.
    Contents are stored data/vocab_sources folder.
    """

    src_dir = Path(__file__).parents[0]
    freq_text_file = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.txt")
    freq_json_file = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.json")

    vocab = {}
    word_data = []

    with open(freq_text_file, encoding="utf-8") as file:
        line_num = 0
        for line in file:
            if line != "\n":
                stripped_line = line.strip()

                # get rank
                if line_num == 0 and stripped_line.isdigit():
                    rank = stripped_line

                    line_num = 1

                # get korean and english word, romanization, type of word
                elif line_num == 1:
                    line = stripped_line.split()
                    word_data += line
                    if len(word_data) > 3:
                        kor = word_data[0]
                        rom = word_data[1]
                        type_ = word_data[2]
                        eng = " ".join(word_data[3:])

                        word_data.clear()
                        line_num = 2

                # get examples in korean and english
                elif line_num == 2:
                    stripped_line = stripped_line.replace("•", "")
                    stripped_line = stripped_line.strip()
                    if "—" in stripped_line:
                        ex_kr, ex_en = stripped_line.split("—")
                        ex_kr = ex_kr.strip()
                        ex_en = ex_en.strip()
                    elif " | " not in stripped_line:
                        ex_en += f" {stripped_line}"

                # get frequency and dispersion
                if " | " in stripped_line:
                    freq, disp = stripped_line.split(" | ")
                    line_num = 0

                    # save all the data of word into vocab dictionary
                    print(rank, kor, rom, type_, eng, ex_kr, ex_en, freq, disp)
                    vocab[kor] = {
                        "rank": rank,
                        "romanization": rom,
                        "type": type_,
                        "content": eng,
                        "example_kr": ex_kr,
                        "example_en": ex_en,
                        "frequency": freq,
                        "disp": disp,
                    }

    with open(freq_json_file, "w", encoding="utf-8") as file:
        json.dump(vocab, file, indent=4, ensure_ascii=False)


def create_topi_json():
    """Creates topi json vocabulary file out from raw text.

    Takes and transforms raw text of topi vocabulary into json file.
    Contents are stored data/vocab_sources folder.
    """

    src_dir = Path(__file__).parents[0]
    topi_text_file = Path(f"{src_dir}/data/vocab_sources/topik_vocab.txt")
    topi_json_file = Path(f"{src_dir}/data/vocab_sources/topik_vocab.json")

    vocab = {}

    with open(topi_text_file, encoding="utf-8") as file:
        for line in file:

            # get korean and english word
            worded = line.split(maxsplit=2)
            kor = worded[1]
            eng = worded[2].strip()

            # save them into vocab dictionary
            print(kor, eng)
            vocab[kor] = eng

    with open(topi_json_file, "w", encoding="utf-8") as file:
        json.dump(vocab, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    create_freq_json()
    create_topi_json()
