from pathlib import Path

from konlpy.tag import Okt

okt = Okt()

level = 1
lesson = 2
source_dir = Path(__file__).parents[0]
text_file_name = Path(f"{source_dir}/data/level_{level}/lesson_{lesson}/listening_text.txt")
vocab_file_name = Path(f"{source_dir}/data/level_{level}/lesson_{lesson}/listening_wordsss.txt")

with open(text_file_name, encoding="utf-8") as file:
    korean_text = file.read()
    print('Tokenizing Korean text...', end='')
    tokenized_text = okt.pos(korean_text, norm=True, stem=True)
    print('Done')


from collections import defaultdict
occurences = defaultdict(int)
occurences_check = defaultdict(int)
word_types = {}

log_file = open(vocab_file_name, "w", encoding="utf-8")

log_file.write("Detailed tokenization cuz of grouping order chaos when debugging.\n")
for token in tokenized_text:
    try:
        if (token[1] == 'Punctuation' or token[1] == 'Foreign'):
            log_file.write(f'Skipping garbage... ({token}\n')
            continue
    except Exception as e:
        log_file.write('Error skipping token:', e, "\n")
    occurences[(token[0])] += 1
    occurences_check[((token[0]), token[1])] += 1  # dup check
    word_types[token[0]] = token[1]
    str_ = " ".join(((token[0]), (token[1])))
    log_file.write(str_ + "\n")

words = []
for i in occurences_check:
    words.append(i[0])
dup_words = [w for w in words if words.count(w) > 1]
uniq_dup = set(dup_words)
if uniq_dup:
    print("Found duplicates! There are two different types of word", uniq_dup)

# with open(vocab_file_name, "w", encoding="utf-8") as file:
#     for key, val in occurences.items():
#         file.write(f"{key}: {val}\n")

# TODO: duplicates in gspread is solved by popping from words list here
# TODO: if theres number in the last character, omit it

# apply to gspread

import os
import json
import gspread
import pandas as pd

# occurences
credentials_dict_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(credentials_dict_str)
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet_main = g_credentials.open("Korea - Vocabulary")

lvl_1_2_g_work_sheet = g_sheet_main.worksheet("Level 1-2 beta")
lvl_1_2_df = pd.DataFrame(lvl_1_2_g_work_sheet.get_all_records())

book_occurences_g_work_sheet = g_sheet_main.worksheet("Book occurences")
book_occurences_df = pd.DataFrame(book_occurences_g_work_sheet.get_all_records())
vocab_set = set()

print("Starting google sheets update.")
log_file.write("\n")
for row in lvl_1_2_df.itertuples():
    lvl_1_2_word = row.Korean[:-1] if row.Korean[-1].isdigit() else row.Korean
    if lvl_1_2_word in dup_words:
        print("Skipping duplicate in gspread!")
    elif lvl_1_2_word in occurences:
        if row.Book_Level == level:
            if row.Book_Lesson != lesson:
                vocab_set.add(row.Korean)
                str_ = " ".join(("Out of lesson:", row.Korean, str(occurences[lvl_1_2_word]), word_types[lvl_1_2_word]))
                log_file.write(str_ + "\n")
                continue
        else:
            vocab_set.add(row.Korean)
            str_ = " ".join(("Out of level:", row.Korean, str(occurences[lvl_1_2_word]), word_types[lvl_1_2_word]))
            log_file.write(str_ + "\n")
            continue
    
        count = occurences.pop(lvl_1_2_word)

        if not row.Listening_used:
            lvl_1_2_df.at[row.Index, "Listening_used"] = level * 100 + level

        row_dict = {
            "Word": row.Korean,
            f"Listen_{lesson}": count,
        }
        df = pd.DataFrame(row_dict, columns=book_occurences_df.columns, index=[0])
        book_occurences_df = pd.concat([book_occurences_df, df])  # ignore_index

log_file.write("\n")
for leftover in occurences:
    if leftover not in vocab_set:
        str_ = " ".join(("Not in vocab:", leftover, str(occurences[leftover]), word_types[leftover]))
        log_file.write(str_ + "\n")

log_file.close()

# save to gsheets
book_occurences_df = book_occurences_df.fillna("")
book_occurences_list = [book_occurences_df.columns.values.tolist()]  # header
book_occurences_list += book_occurences_df.values.tolist()
book_occurences_g_work_sheet.update(book_occurences_list, value_input_option="USER_ENTERED")

lvl_1_2_df = lvl_1_2_df.fillna("")
lvl_1_2_list = [lvl_1_2_df.columns.values.tolist()]  # header
lvl_1_2_list += lvl_1_2_df.values.tolist()
lvl_1_2_g_work_sheet.update(lvl_1_2_list, value_input_option="USER_ENTERED")
