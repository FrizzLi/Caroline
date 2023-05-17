"""
"Korea - Vocabulary" Spreadsheet:
 - serves to convert two tabs (Book_Level, Book_Lesson) into one (Lesson)
   in "Level 1-2 (modified)"
 - NOTE this is already included in gsheet2, therefore useless
"""

import sys
from pathlib import Path


def _update_df(ws_df):
    """Merges columns Book_Lesson and Book_Level into one -> Book_Level

    Args:
        ws_df (pandas.core.frame.DataFrame): worksheet dataframe table

    Returns:
        pandas.core.frame.DataFrame: updated dataframe table
    """

    for row in ws_df.itertuples():
        if not row.Book_Lesson:
            continue
        if isinstance(row.Book_Lesson, str):
            print("Lesson string bug:", row.Book_Lesson)
            continue
        elif isinstance(row.Book_Level, str):
            print("Level string bug:", row.Book_Level)
            continue
        ws_df.at[row.Index, "Book_Level"] = (
            row.Book_Level * 100 + row.Book_Lesson
        )

    return [ws_df]


def merge(gs_name, ws_names):
    """Loads, merges columns according to _create_df method and updates the ws

    Args:
        gs_name (str): google spreadsheet name
        ws_name (str): worksheet name
    """

    wss, ws_dfs = utils.get_worksheets(gs_name, ws_names)
    ws_df = _update_df(ws_dfs[0])
    utils.update_worksheet(wss[0], ws_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    SPREADSHEET_NAME = "Korea - Vocabulary"
    WORKSHEET_NAMES = ("Level 1-2 (modified)",)

    merge(SPREADSHEET_NAME, WORKSHEET_NAMES)
