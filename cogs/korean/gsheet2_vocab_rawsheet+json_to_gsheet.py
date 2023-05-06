"""
"Korea - Vocabulary (raw)" Spreadsheet:
 - uses "raw" tab to fill up "arranged" tab that is easier to read
 - NOTE that "raw" tab requires first row with "Lesson_vocab" as a header

"Korea - Vocabulary" Spreadsheet:
 - uses "arranged" tab to fill up "Level 1-2 (raw)" tab
 - uses freq and topi json files in data/gsheet for further filling
 - NOTE that "Level 1-2 (raw) tab must have the first row (column naming) 
   header prepared in this order: 
   Lesson, Korean, Book_English, Topik_English, Freq_English, Example_EN, 
   Example_KR, Rank, Type, Romanization, Frequency, Dispersion, TOPIK
   (After running the script, Topik_English column might end up before TOPIK)
"""

import json
import sys
from pathlib import Path

import pandas as pd


def _fill_arranged_df(raw_df, arranged_df):
    lesson = ""
    level = ""
    index_add = 0
    for row in raw_df.itertuples():
        kr_en = row.Lesson_vocab.split(" - ")
        if len(kr_en) > 1:
            index = row.Index - index_add
            arranged_df.at[index, "Korean"] = kr_en[0]
            arranged_df.at[index, "Book_English"] = kr_en[1]
            arranged_df.at[index, "Book_Level"] = level
            arranged_df.at[index, "Book_Lesson"] = lesson
            arranged_df.at[index, "Lesson"] = level + lesson.zfill(2)
        else:
            index_add += 1
        if 2 < len(row.Lesson_vocab) < 5:
            level, lesson = row.Lesson_vocab.split(";")


def create_arranged_vocab():
    """Fills up "arranged" vocab tab by using the "raw" tab."""

    worksheets, worksheets_df = utils.get_worksheets(
        "Korea - Vocabulary (raw)", ("raw", "arranged")
    )
    raw_df, arranged_df = worksheets_df[0], worksheets_df[1]

    _fill_arranged_df(raw_df, arranged_df)

    arranged_worksheet = worksheets[1]
    utils.update_worksheet(arranged_worksheet, arranged_df)
    print("Created arranged vocab")


def create_level_vocab():
    """Fills up "Level 1-2 (raw)" vocab tab. (changes Topik_English column pos)

    Filling has three stages:
    1. filling over words that are in "arranged" tab with freq and topi sources
    2. filling over words that are in "freq" with topi source
    3. filling over words that are in "topi" source
    """

    src_dir = Path(__file__).parents[0]
    fre_json = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.json")
    top_json = Path(f"{src_dir}/data/vocab_sources/topik_vocab.json")
    with open(fre_json, encoding="utf-8") as fre:
        freq = json.load(fre)
    with open(top_json, encoding="utf-8") as top:
        topi = json.load(top)

    _, worksheets_raw_df = utils.get_worksheets(
        "Korea - Vocabulary (raw)", ("arranged",)
    )
    worksheets_lvl, worksheets_lvl_df = utils.get_worksheets(
        "Korea - Vocabulary", ("Level 1-2 (raw)",)
    )
    arranged_df = worksheets_raw_df[0]
    lvl_worksheet, lvl_df = worksheets_lvl[0], worksheets_lvl_df[0]

    # add arranged + freq + topi
    for row in arranged_df.itertuples():
        lvl_df.at[row.Index, "Lesson"] = row.Lesson
        lvl_df.at[row.Index, "Korean"] = row.Korean
        lvl_df.at[row.Index, "Book_English"] = row.Book_English
        if row.Korean in freq:
            word = freq.pop(row.Korean)
            lvl_df.at[row.Index, "Freq_English"] = row.Korean
            lvl_df.at[row.Index, "Example_EN"] = word["example_en"]
            lvl_df.at[row.Index, "Example_KR"] = word["example_kr"]
            lvl_df.at[row.Index, "Rank"] = word["rank"]
            lvl_df.at[row.Index, "Type"] = word["type"]
            lvl_df.at[row.Index, "Romanization"] = word["romanization"]
            lvl_df.at[row.Index, "Frequency"] = word["frequency"]
            lvl_df.at[row.Index, "Dispersion"] = word["disp"]
        if row.Korean in topi:
            word = topi.pop(row.Korean)
            lvl_df.at[row.Index, "Topik_English"] = word
            lvl_df.at[row.Index, "TOPIK"] = "I"

    print("Created vocab from arranged vocab, last copied word:", row.Korean)

    # add freq + topi (not present in arranged)
    for row in freq:
        row_dict = {
            "Korean": row,
            "Rank": freq[row]["rank"],
            "Romanization": freq[row]["romanization"],
            "Type": freq[row]["type"],
            "Freq_English": row,
            "Example_KR": freq[row]["example_kr"],
            "Example_EN": freq[row]["example_en"],
            "Frequency": freq[row]["frequency"],
            "Dispersion": freq[row]["disp"],
        }
        if row in topi:
            row_dict["TOPIK"] = "I"
            row_dict["Topik_English"] = topi.pop(row)

        df = pd.DataFrame(row_dict, columns=lvl_df.columns, index=[0])
        lvl_df = pd.concat([lvl_df, df])

    print("Created vocab from freq book vocab, last freq word:", row)

    # topi (not present in arranged/freq)
    for row in topi:
        row_dict = {
            "Korean": row,
            "TOPIK": "I",
            "Topik_English": topi[row],
        }
        df = pd.DataFrame(row_dict, columns=lvl_df.columns, index=[0])
        lvl_df = pd.concat([lvl_df, df])

    print("Created vocab from topi, last topi word:", row)

    utils.update_worksheet(lvl_worksheet, lvl_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    create_arranged_vocab()
    create_level_vocab()

# TODO: remove + sign in file name
