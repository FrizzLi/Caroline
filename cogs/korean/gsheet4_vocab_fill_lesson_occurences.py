"""
"Korea - Vocabulary" Spreadsheet:
 - fills up "Listening/Reading _Used" column for words that are in chosen lesson
 - adds row in "listening/reading occurences" tab for each word in chosen lesson
 - NOTE that this got discarded as it was too time consuming. Could take
   advantage of ChatGPT instead.
"""

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from konlpy.tag import Okt

sys.path.append(str(Path(__file__).parents[2]))
import utils


def tokenize_text(f_path):
    """Parses through the text in the text file creates list of single words.

    Args:
        f_path (pathlib.WindowsPath): path to the text file

    Returns:
        List[Tuple[str, str]]: list of words with their type (E.g. noun)
    """

    print("Tokenizing Korean text... ", end="")
    okt = Okt()
    try:
        with open(f_path, encoding="utf-8") as file:
            korean_text = file.read()
            tokenized_text = okt.pos(korean_text, norm=True, stem=True)
            print("Done!")
    except FileNotFoundError as err:
        print(err)
        exit()

    return tokenized_text


def group_by_count(tokens):
    """Counts occurences for each word (token).

    Args:
        tokens (List[Tuple[str, str]]): list of words and their type

    Returns:
        Tuple[collections.defaultdict[str, int], Dict[str, str]]: (
            word: occurences
            word: type (E.g. noun)
        )
    """

    print("Grouping into occurs count and finding duplicates... ", end="")
    occurs = defaultdict(int)
    occurs_check = defaultdict(int)
    word_types = {}

    log_file.write("Detailed tokenization cuz of grouping chaos.\n")
    for token in tokens:
        try:
            if token[1] == "Punctuation" or token[1] == "Foreign":
                log_file.write(f"Skipping garbage... ({token}\n")
                continue
        except Exception as err:
            log_file.write(f"Error skipping token: {err} \n")
        occurs[(token[0])] += 1
        occurs_check[((token[0]), token[1])] += 1  # dup check
        word_types[token[0]] = token[1]

        str_ = " ".join(((token[0]), (token[1])))
        log_file.write(str_ + "\n")

    words = []
    for i in occurs_check:
        words.append(i[0])
    dup_words = [w for w in words if words.count(w) > 1]
    uniq_dup = set(dup_words)
    log_file.write(f"\nDuplicates: {uniq_dup}\n")
    for dup in uniq_dup:
        for occur in occurs_check:
            if occur[0] == dup:
                log_file.write(f"{occur}: {occurs_check[occur]}\n")

    return occurs, word_types


def create_df(vocab_df, occurs_df, occurs, word_types, text_type, lesson):
    def write_line_msg(portion, word, occurs, word_types, vocab_base_word):
        head = f"Out of {portion}:"
        occur = str(occurs[vocab_base_word])
        type_ = word_types[vocab_base_word]
        str_ = " ".join((head, word, occur, type_))

        log_file.write(str_ + "\n")

    missing_vocab_set = set()
    log_file.write("\n")

    for row in vocab_df.itertuples():
        w = row.Korean
        vocab_base_word = w[:-1] if w[-1].isdigit() else w
        if vocab_base_word in occurs:
            if not row.Lesson or row.Lesson > int(lesson):
                missing_vocab_set.add(vocab_base_word)
                write_line_msg(
                    "lesson (in next)", w, occurs, word_types, vocab_base_word
                )
            elif row.Lesson < int(lesson):
                listen_read_used = row.Reading_Used if text_type == "Read" else row.Listening_Used
                if listen_read_used:
                    missing_vocab_set.add(vocab_base_word)
                    write_line_msg(
                        "lesson (in previous)",
                        w,
                        occurs,
                        word_types,
                        vocab_base_word,
                    )
                else:
                    log_file.write(
                        f"Going to fill {row.Korean} from {row.Lesson} Lesson!\n"
                    )
                    vocab_df.at[row.Index, f"{text_type}ing_Used"] = lesson
            else:
                vocab_df.at[row.Index, f"{text_type}ing_Used"] = lesson
                log_file.write(f"Fill {row.Korean}!\n")

            # update occurances
            count = occurs.pop(vocab_base_word)
            row_dict = {"Word": w, f"{text_type}_{str(int(lesson[-2:]))}": count}
            df = pd.DataFrame(row_dict, columns=occurs_df.columns, index=[0])
            occurs_df = pd.concat([occurs_df, df])

    log_file.write("\n")
    for leftover in occurs:
        leftover = leftover[:-1] if leftover[-1].isdigit() else leftover
        if not leftover or leftover.isdigit():  # some kind of bug?
            continue
        if leftover not in missing_vocab_set:
            write_line_msg("vocab", leftover, occurs, word_types, leftover)

    return vocab_df, occurs_df


lesson = input("Enter lesson in 3 digits: ")
final = input("Press ENTER if you don't want to update sheets.")
text_type = input("Press ENTER for listening_text, else reading text.")
text_type = "Read" if text_type else "Listen"

src_dir = Path(__file__).parents[0]
lesson_dir = f"{src_dir}/data/level_{lesson[0]}/lesson_{int(lesson[-2:])}"
path_str = f"{lesson_dir}/{text_type.lower()}ing_text.txt"
explo_path_str = f"{lesson_dir}/{text_type.lower()}ing_explo.txt"

f_path = Path(path_str)
f_explo_path = Path(explo_path_str)

# parsing the text into single words
tokenized = tokenize_text(f_path)

# count grouping word occurences and finding duplicates
log_file = open(f_explo_path, "w", encoding="utf-8")
occurs, word_types = group_by_count(tokenized)

# updating google sheets
print("Updating google sheets... ", end="")

wss, ws_dfs = utils.get_worksheets("Korea - Vocabulary", ("Level 1-2 (modified)", f"{text_type.lower()}ing occurences"))
lvl_ws, occurs_ws = wss[0], wss[1]
lvl_df, occurs_df = ws_dfs[0], ws_dfs[1]


lvl_df, occurs_df = create_df(lvl_df, occurs_df, occurs, word_types, text_type, lesson)
log_file.close()

if final:
    utils.update_worksheet(lvl_ws, lvl_df)
    utils.update_worksheet(occurs_ws, occurs_df)

print("Done!")

# TODO: format.. and polish even further
# if __name__ == "__main__":
#     add_homonyms_below_base_word()
