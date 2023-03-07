"""
"Korea - Vocabulary (raw)" Google Spreadsheet:
 - uses "raw" tab to fill up "arranged" tab that is easier to read

"Korea - Vocabulary" Google Spreadsheet:
 - uses "arranged" tab to fill up "Level 1-2" tab
 - uses freq and topi json files in data/gsheet to further fill "Level 1-2" tab
"""

import json
import os
from pathlib import Path

import gspread
import pandas as pd

# create arranged vocab with raw
credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
credentials_dict = json.loads(credentials_dict_str)
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet_main = g_credentials.open("Korea - Vocabulary")
g_sheet_raw = g_credentials.open("Korea - Vocabulary (raw)")

raw_vocab_g_work_sheet = g_sheet_raw.worksheet("raw")
raw_vocab_df = pd.DataFrame(raw_vocab_g_work_sheet.get_all_records())

arranged_vocab_g_work_sheet = g_sheet_raw.worksheet("arranged")
arranged_vocab_df = pd.DataFrame(arranged_vocab_g_work_sheet.get_all_records())

lesson = ""
level = ""
index_add = 0
for row in raw_vocab_df.itertuples():
    kr_en = row.Frequency.split(" - ")
    if len(kr_en) > 1:
        index = row.Index - index_add
        arranged_vocab_df.at[index, "Korean"] = kr_en[0]
        arranged_vocab_df.at[index, "Book_English"] = kr_en[1]
        arranged_vocab_df.at[index, "Lesson"] = level + lesson.zfill(2)
    else:
        index_add += 1
    if 2 < len(row.Frequency) < 5:
        level, lesson = row.Frequency.split(";")

arranged_vocab_df = arranged_vocab_df.fillna("")
arranged_vocab_list = [arranged_vocab_df.columns.values.tolist()]
arranged_vocab_list += arranged_vocab_df.values.tolist()
arranged_vocab_g_work_sheet.update(
    arranged_vocab_list, value_input_option="USER_ENTERED"
)

print("Created arranged vocab")

# create Level 1-2
src_dir = Path(__file__).parents[0]
fre_json = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.json")
top_json = Path(f"{src_dir}/data/vocab_sources/topik_vocab.json")

with open(fre_json, encoding="utf-8") as fre:
    freq = json.load(fre)
with open(top_json, encoding="utf-8") as top:
    topi = json.load(top)

arranged_vocab_g_work_sheet = g_sheet_raw.worksheet("arranged")
arranged_vocab_df = pd.DataFrame(arranged_vocab_g_work_sheet.get_all_records())

lvl_1_2_g_work_sheet = g_sheet_main.worksheet("Level 1-2 (raw)")
lvl_1_2_df = pd.DataFrame(lvl_1_2_g_work_sheet.get_all_records())

# add arranged + freq + topi
for row in arranged_vocab_df.itertuples():
    lvl_1_2_df.at[row.Index, "Lesson"] = row.Lesson
    lvl_1_2_df.at[row.Index, "Korean"] = row.Korean
    lvl_1_2_df.at[row.Index, "Book_English"] = row.Book_English
    if row.Korean in freq:
        word = freq.pop(row.Korean)
        lvl_1_2_df.at[row.Index, "Freq_English"] = word["freq_eng"]
        lvl_1_2_df.at[row.Index, "Rank"] = word["rank"]
        lvl_1_2_df.at[row.Index, "Example_KR"] = word["example_kr"]
        lvl_1_2_df.at[row.Index, "Example_EN"] = word["example_en"]
        lvl_1_2_df.at[row.Index, "Romanization"] = word["romanization"]
        lvl_1_2_df.at[row.Index, "Type"] = word["type"]
        lvl_1_2_df.at[row.Index, "Frequency"] = word["frequency"]
        lvl_1_2_df.at[row.Index, "Dispersion"] = word["disp"]
    if row.Korean in topi:
        word = topi.pop(row.Korean)
        lvl_1_2_df.at[row.Index, "Topik_English"] = word
        lvl_1_2_df.at[row.Index, "TOPIK"] = "I"

print("Created vocab from arranged vocab, last copied word:", row.Korean)

# add freq + topi (not present in arranged)
for row in freq:
    row_dict = {
        "Korean": row,
        "Rank": freq[row]["rank"],
        "Romanization": freq[row]["romanization"],
        "Type": freq[row]["type"],
        "Freq_English": freq[row]["freq_eng"],
        "Example_KR": freq[row]["example_kr"],
        "Example_EN": freq[row]["example_en"],
        "Frequency": freq[row]["frequency"],
        "Dispersion": freq[row]["disp"],
    }
    if row in topi:
        row_dict["TOPIK"] = "I"
        row_dict["Topik_English"] = topi.pop(row)

    # lvl_1_2_df.append(row_dict, ignore_index=True)
    df = pd.DataFrame(row_dict, columns=lvl_1_2_df.columns, index=[0])
    lvl_1_2_df = pd.concat([lvl_1_2_df, df])  # ignore_index

print("Created vocab from freq book vocab, last freq word:", row)

# topi (not present in arranged/freq)
for row in topi:
    row_dict = {
        "Korean": row,
        "TOPIK": "I",
        "Topik_English": topi[row],
    }
    df = pd.DataFrame(row_dict, columns=lvl_1_2_df.columns, index=[0])
    lvl_1_2_df = pd.concat([lvl_1_2_df, df])

print("Created vocab from topi, last topi word:", row)

# save to gsheets
lvl_1_2_df = lvl_1_2_df.fillna("")
lvl_1_2_list = [lvl_1_2_df.columns.values.tolist()]
lvl_1_2_list += lvl_1_2_df.values.tolist()
lvl_1_2_g_work_sheet.update(lvl_1_2_list, value_input_option="USER_ENTERED")

# create_gsheet_vocab
# vocab_json_to_gsheet