"""
"Korea - Vocabulary (raw)" Spreadsheet:
 - uses "raw" tab to fill up "arranged" tab that is easier to read
 - NOTE that "raw" tab requires first row to be "Lesson_vocab" (as the header)

"Korea - Vocabulary" Spreadsheet:
 - uses "arranged" tab to fill up "Level 1-2 (raw)" tab
 - NOTE that "Level 1-2 (raw) tab must have the first row (column naming) 
   header prepared in this order: 
   Lesson, Korean, Book_English, Topik_English, Freq_English, Example_EN, 
   Example_KR, Rank, Type, Romanization, Frequency, Dispersion, TOPIK
   (After running the script, Topik_English column might end up before TOPIK)

Uses (Contents are stored data/vocab_sources folder):
 - json-ed frequency vocabulary book
 - topik vocabulary raw's content
   (https://learning-korean.com/elementary/20210101-10466/)
"""

import json
import sys
from pathlib import Path

import pandas as pd


def _fill_arranged_df(raw_df, arranged_df):
    """Fills the arranged dataframe with the raw dataframe.

    Args:
        raw_df (_type_): raw dataframe
        arranged_df (_type_): arranged_dataframe to be filled
    """

    print("Creating arranged vocab... ", end="")

    row = None
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

    print("Done! (empty!)" if not row else "Done!")


def _fill_lvl_df(arranged_df, lvl_df, freq, topi):
    """Fills the "level" (main) dataframe with "arranged" (cleansed) tab.

    Filling has three stages:
    1. filling words that are in "arranged" tab with "freq" and "topi" sources
    2. filling words that are in "freq" with "topi" source
    3. filling words that are in "topi" source

    Args:
        arranged_df (pandas.core.frame.DataFrame): arranged cleansed vocab tab
        lvl_df (pandas.core.frame.DataFrame): main vocab tab
        freq (Dict[str, Dict[str, str]]): frequency vocabulary book contents
        topi (Dict[str, str]): topik vocabulary contents
    """

    print("Creating vocab from arranged vocab... ", end="")

    row = None

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

    print("Done! (empty!)" if not row else "Done!")
    print("Creating vocab from freq vocab... ", end="")

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

    print("Done!")
    print("Creating vocab from topi vocab... ", end="")

    # topi (not present in arranged/freq)
    for row in topi:
        row_dict = {
            "Korean": row,
            "TOPIK": "I",
            "Topik_English": topi[row],
        }
        df = pd.DataFrame(row_dict, columns=lvl_df.columns, index=[0])
        lvl_df = pd.concat([lvl_df, df])

    print("Done!")


def init_arranged_vocab(gs_name, ws_names):
    """Initializes "arranged" (cleansed) vocab from "raw" tab.

    Args:
        gs_name (str): google spreadsheet name
        ws_names (Tuple[str]): worksheet names
    """

    wss, ws_dfs = utils.get_worksheets(gs_name, ws_names, create=True)
    raw_df, arranged_df = ws_dfs[0], ws_dfs[1]

    _fill_arranged_df(raw_df, arranged_df)

    arranged_ws = wss[1]
    utils.update_worksheet(arranged_ws, arranged_df)


def init_level_vocab(arr_gs_name, arr_ws_names, lvl_gs_name, lvl_ws_names):
    """Initializes "level" (main) vocabulary tab.

    Args:
        arr_gs_name (str): arranged google spreadsheet name
        arr_ws_names (Tuple[str]): arranged worksheet names
        lvl_gs_name (str): level google spreadsheet name
        lvl_ws_names (Tuple[str]): level worksheet names
    """

    src_dir = Path(__file__).parents[0]
    fre_json = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.json")
    top_json = Path(f"{src_dir}/data/vocab_sources/topik_vocab.json")
    with open(fre_json, encoding="utf-8") as fre:
        freq = json.load(fre)
    with open(top_json, encoding="utf-8") as top:
        topi = json.load(top)

    _, ws_raw_dfs = utils.get_worksheets(arr_gs_name, arr_ws_names, True)
    wss_lvl, ws_lvl_dfs = utils.get_worksheets(lvl_gs_name, lvl_ws_names, True)
    arranged_df = ws_raw_dfs[1]
    ws_lvl, lvl_df = wss_lvl[0], ws_lvl_dfs[0]

    _fill_lvl_df(arranged_df, lvl_df, freq, topi)

    utils.update_worksheet(ws_lvl, lvl_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    ARRANGED_SPREADSHEET_NAME = "Korea - Vocabulary (raw)"
    ARRANGED_WORKSHEET_NAMES = ("raw", "arranged")

    LEVEL_SPREADSHEET_NAME = "Korea - Vocabulary"
    LEVEL_WORKSHEET_NAMES = ("Level 1-2 (raw)",)

    init_arranged_vocab(ARRANGED_SPREADSHEET_NAME, ARRANGED_WORKSHEET_NAMES)
    init_level_vocab(
        ARRANGED_SPREADSHEET_NAME,
        ARRANGED_WORKSHEET_NAMES,
        LEVEL_SPREADSHEET_NAME,
        LEVEL_WORKSHEET_NAMES,
    )

# TODO: rename to vocab_create_worksheet
# TODO: documentation (how to set up gspread sheets, token, how to use this, what does this all mean)
