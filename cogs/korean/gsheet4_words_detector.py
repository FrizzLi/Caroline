import json
import os
from collections import defaultdict
from pathlib import Path

import gspread
import pandas as pd
from konlpy.tag import Okt

level = 1
lesson = 2
source_dir = Path(__file__).parents[0]
lesson_folder = f"{source_dir}/data/level_{level}/lesson_{lesson}/"
listen_str = f"{lesson_folder}listening_text.txt"
listen_explo_str = f"{lesson_folder}explo.txt"
f_listen = Path(listen_str)
f_listen_explo = Path(listen_explo_str)

# parsing the text into single words
print("Parsing the text into single words..")
okt = Okt()
with open(f_listen, encoding="utf-8") as file:
    korean_text = file.read()
    print("Tokenizing Korean text... ", end="")
    tokenized_text = okt.pos(korean_text, norm=True, stem=True)
    print("Done!")


# count grouping word occurs and finding duplicates
print("Grouping into occurs count and finding duplicates... ", end="")
occurs = defaultdict(int)
occurs_check = defaultdict(int)
word_types = {}

log_file = open(f_listen_explo, "w", encoding="utf-8")
log_file.write("Detailed tokenization cuz of grouping chaos.\n")
for token in tokenized_text:
    try:
        if token[1] == "Punctuation" or token[1] == "Foreign":
            log_file.write(f"Skipping garbage... ({token}\n")
            continue
    except Exception as e:
        log_file.write("Error skipping token:", e, "\n")
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
if uniq_dup:
    print("Found duplicates! There are two different types of word", uniq_dup)
    return
else:
    print("Done!")


# updating google sheets
print("Updating google sheets... ", end="")
credentials_dict_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(credentials_dict_str)
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet_main = g_credentials.open("Korea - Vocabulary")

lvl_1_2_g_work_sheet = g_sheet_main.worksheet("Level 1-2 beta")
lvl_1_2_df = pd.DataFrame(lvl_1_2_g_work_sheet.get_all_records())

occurs_g_work_sheet = g_sheet_main.worksheet("Book occurs")
occurs_df = pd.DataFrame(occurs_g_work_sheet.get_all_records())
vocab_set = set()

log_file.write("\n")
for row in lvl_1_2_df.itertuples():
    lvl_1_2_word = row.Korean[:-1] if row.Korean[-1].isdigit() else row.Korean
    if lvl_1_2_word in dup_words:
        print("Skipping duplicate in gspread!")
        return
    elif lvl_1_2_word in occurs:
        if row.Book_Level == level:
            if row.Book_Lesson != lesson:
                vocab_set.add(row.Korean)

                head = "Out of lesson:"
                word = row.Korean
                occur = str(occurs[lvl_1_2_word])
                type_ = word_types[lvl_1_2_word]
                str_ = " ".join((head, word, occur, type_))

                log_file.write(str_ + "\n")
                continue
        else:
            vocab_set.add(row.Korean)

            head = "Out of lesson:"
            word = row.Korean
            occur = str(occurs[lvl_1_2_word])
            type_ = word_types[lvl_1_2_word]
            str_ = " ".join((head, word, occur, type_))

            log_file.write(str_ + "\n")
            continue

        count = occurs.pop(lvl_1_2_word)

        if not row.Listening_used:
            lvl_1_2_df.at[row.Index, "Listening_used"] = level * 100 + level

        row_dict = {"Word": row.Korean, f"Listen_{lesson}": count}
        df = pd.DataFrame(row_dict, columns=occurs_df.columns, index=[0])
        occurs_df = pd.concat([occurs_df, df])  # ignore_index

log_file.write("\n")
for leftover in occurs:
    if leftover not in vocab_set:
        head = "Out of lesson:"
        word = row.Korean
        occur = str(occurs[lvl_1_2_word])
        type_ = word_types[lvl_1_2_word]
        str_ = " ".join((head, word, occur, type_))

        log_file.write(str_ + "\n")

log_file.close()

# save to gsheets
occurs_df = occurs_df.fillna("")
occurs_list = [occurs_df.columns.values.tolist()]  # header
occurs_list += occurs_df.values.tolist()
occurs_g_work_sheet.update(occurs_list, value_input_option="USER_ENTERED")

lvl_1_2_df = lvl_1_2_df.fillna("")
lvl_1_2_list = [lvl_1_2_df.columns.values.tolist()]  # header
lvl_1_2_list += lvl_1_2_df.values.tolist()
lvl_1_2_g_work_sheet.update(lvl_1_2_list, value_input_option="USER_ENTERED")
print("Done!")
