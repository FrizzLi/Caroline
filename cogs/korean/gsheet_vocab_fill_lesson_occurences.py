""" 
"Korea - Vocabulary" Spreadsheet:
 - fills up "Listening/Reading _Used" column for each word
 - adds row in "listening/reading occurences" tab for each word
 - NOTE that this got discarded as it was too time consuming. Could take
   advantage of ChatGPT instead.
 - NOTE that this script isn't deeply polished
"""

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd
from konlpy.tag import Okt


def tokenize_text(f_path):
    """Read the text file and creates list of single words.

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


def _group_by_count(tokens, log_file):
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

    print("Done!")

    return occurs, word_types


def _get_msg_line(portion, word, occurs, word_types, vocab_base_word):
    """Gets line of a message for logging.

    Args:
        portion (str): type of information
        word (str): word being processed
        occurs (collections.defaultdict[str, int]): occurences of all words
        word_types (Dict[str, str]): words and types (word being the key)
        vocab_base_word (str): base form of the word

    Returns:
        str: message to use for logging
    """

    head = f"Out of {portion}:"
    occur = str(occurs[vocab_base_word])
    type_ = word_types[vocab_base_word]
    str_ = " ".join((head, word, occur, type_))

    return str_


def _fill_df(lvl_df, occurs_df, occurs, word_types, text, lesson, log_file):
    """Fills dataframe with occurences.

    Args:
        lvl_df (pandas.core.frame.DataFrame): vocab worksheet df
        occurs_df (pandas.core.frame.DataFrame): occurences tab worksheet df
        occurs (collections.defaultdict[str, int]): word occurences
        word_types (Dict[str, str]): words and types (word being the key)
        text (str): text type (either reading or listening text)
        lesson (str): lesson number in 3 digits
        log_file (_io.TextIOWrapper): log text wrapper for manual checking

    Returns:
        Tuple[pandas.core.frame.DataFrame, pandas.core.frame.DataFrame]: (
            filled lvl dataframe occurences,
            filled occurences df with number of occurences
        )
    """

    missing_vocab_set = set()
    log_file.write("\n")

    for row in lvl_df.itertuples():
        w = row.Korean
        vocab_base_word = w[:-1] if w[-1].isdigit() else w
        if vocab_base_word in occurs:
            if not row.Lesson or row.Lesson > int(lesson):
                missing_vocab_set.add(vocab_base_word)
                msg = _get_msg_line(
                    "lesson (in next)", w, occurs, word_types, vocab_base_word
                )
                log_file.write(msg + "\n")
            elif row.Lesson < int(lesson):
                listen_read_used = (
                    row.Reading_Used if text == "Read" else row.Listening_Used
                )
                if listen_read_used:
                    missing_vocab_set.add(vocab_base_word)
                    msg = _get_msg_line(
                        "lesson (in previous)",
                        w,
                        occurs,
                        word_types,
                        vocab_base_word,
                    )
                    log_file.write(msg + "\n")
                else:
                    msg = f"Going to fill {row.Korean} from {row.Lesson}!\n"
                    log_file.write(msg)
                    lvl_df.at[row.Index, f"{text}ing_Used"] = lesson
            else:
                lvl_df.at[row.Index, f"{text}ing_Used"] = lesson
                log_file.write(f"Fill {row.Korean}!\n")

            # update occurances
            count = occurs.pop(vocab_base_word)
            row_dict = {
                "Word": w,
                f"{text}_{str(int(lesson[-2:]))}": count,
            }
            df = pd.DataFrame(row_dict, columns=occurs_df.columns, index=[0])
            occurs_df = pd.concat([occurs_df, df])

    log_file.write("\n")
    for leftover in occurs:
        leftover = leftover[:-1] if leftover[-1].isdigit() else leftover
        if not leftover or leftover.isdigit():  # some kind of bug?
            continue
        if leftover not in missing_vocab_set:
            msg = _get_msg_line(
                "vocab", leftover, occurs, word_types, leftover
            )
            log_file.write(msg + "\n")

    return lvl_df, occurs_df


def fill_lesson_occurences(gs_name, ws_names, lesson, text, update):
    """Fills word occurences from certain lesson.

    Fills up "Listening/Reading _Used" column for each word.
    Adds row in "listening/reading occurences" tab for each word.
    Many times the korean parser cannot find the base form of words that were
    used in the sentences. That's why log file is created, where we can check
    and validate all the words.

    Args:
        gs_name (str): google spreadsheet name
        ws_names (Tuple[str]): worksheet names
        lesson (str): lesson number in 3 digits
        text (str): text type (either reading or listening text)
        update (bool): determines the update of worksheets
    """

    src_dir = Path(__file__).parents[0]
    lesson_dir = f"{src_dir}/data/level_{lesson[0]}/lesson_{int(lesson[-2:])}"
    path_str = f"{lesson_dir}/{text.lower()}ing_text.txt"
    explo_path_str = f"{lesson_dir}/{text.lower()}ing_explo.txt"

    f_path = Path(path_str)
    f_explo_path = Path(explo_path_str)

    # parsing the text into single words
    tokenized = tokenize_text(f_path)

    # count grouping word occurences and finding duplicates
    log_file = open(f_explo_path, "w", encoding="utf-8")
    occurs, word_types = _group_by_count(tokenized, log_file)

    wss, ws_dfs = utils.get_worksheets(gs_name, ws_names)
    lvl_df, occurs_df = ws_dfs[0], ws_dfs[1]
    lvl_df, occurs_df = _fill_df(
        lvl_df, occurs_df, occurs, word_types, text, lesson, log_file
    )
    log_file.close()

    if update:
        lvl_ws, occurs_ws = wss[0], wss[1]
        utils.update_worksheet(lvl_ws, lvl_df)
        utils.update_worksheet(occurs_ws, occurs_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    LESSON = "110"  # Lesson in 3 digits
    TEXT = "Listen"  # Read/Listen
    UPDATE = False  # Sheet updating

    SPREADSHEET_NAME = "Korea - Vocabulary"
    WORKSHEET_NAMES = ("Level 1-2 (modified)", f"{TEXT.lower()}ing occurences")

    fill_lesson_occurences(
        SPREADSHEET_NAME, WORKSHEET_NAMES, LESSON, TEXT, UPDATE
    )
