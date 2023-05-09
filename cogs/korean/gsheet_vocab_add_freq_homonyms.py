"""
"Korea - Vocabulary" Spreadsheet:
 - adds numbered freq words (multiple meanings) below base word
   in "Level 1-2 (raw)" tab
 - NOTE that it creates duplicates inside the worksheet
 - NOTE that the outcome of this script hasn't been used in the end
"""

import json
import sys
from pathlib import Path

import pandas as pd


def _df_row_insert(row_num, old_df, row_val):
    """Inserts a row into dataframe.

    Args:
        row_num (int): row number
        old_df (pandas.core.frame.DataFrame): dataframe into which we insert
        row_val (list): row values

    Returns:
        pandas.core.frame.DataFrame: new dataframe with inserted row_val
    """

    df1 = old_df[0:row_num]
    df2 = old_df[row_num:]
    df1.loc[row_num] = row_val
    new_df = pd.concat([df1, df2])
    new_df.index = [*range(new_df.shape[0])]

    return new_df


def _fill_lvl_df(freq, ws_lvl_df):
    """Fills up lvl dataframe with homonyms below base word.

    Args:
        freq (Dict[str, Dict[str, str]]): freq source
        ws_lvl_df (pandas.core.frame.DataFrame): worksheet dataframe table
            to be filled

    Returns:
        pandas.core.frame.DataFrame: filled dataframe
    """

    added_num = 0
    for row in ws_lvl_df.itertuples():
        for num in range(1, 6):
            if not row.Korean:
                continue
            if row.Korean[-1].isdigit():
                continue
            else:
                row_korean = row.Korean
            numered_word = f"{row_korean}{num}"
            if numered_word in freq:
                added_num += 1
                word = freq.pop(numered_word)
                row_value = [
                    "",
                    numered_word,
                    "",
                    word["content"],
                    "",
                    word["example_en"],
                    word["example_kr"],
                    word["rank"],
                    word["type"],
                    word["romanization"],
                    word["frequency"],
                    word["disp"],
                    "",
                    "",
                    "",
                    "",
                ]
                index = row.Index + added_num
                ws_lvl_df = _df_row_insert(index, ws_lvl_df, row_value)

    return ws_lvl_df


def add_homonyms_below_base_word():
    """Adds homonyms below base word in Level 1-2 (raw) worksheet."""

    src_dir = Path(__file__).parents[0]
    fre_json = Path(f"{src_dir}/data/vocab_sources/freq_dict_kor.json")
    with open(fre_json, encoding="utf-8") as fre:
        freq = json.load(fre)

    wss, ws_dfs = utils.get_worksheets(
        "Korea - Vocabulary", ("Level 1-2 (raw)",)
    )
    ws_lvl, ws_lvl_df = wss[0], ws_dfs[0]

    ws_lvl_df = _fill_lvl_df(freq, ws_lvl_df)

    utils.update_worksheet(ws_lvl, ws_lvl_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    add_homonyms_below_base_word()

# TODO: rename to gsheet_vocab...
