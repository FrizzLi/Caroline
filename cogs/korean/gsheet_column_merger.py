"""This script serves to convert two tabs (Book_Level, Book_Lesson)
into one (Lesson) in "Korea - Vocabulary" Spreadsheet
 - NOTE that this is already included in gsheet2, therefore useless"""

import sys
from pathlib import Path


def _update_df(worksheet_df):
    """Merges columns Book_Lesson and Book_Level into one -> Book_Level

    Args:
        worksheet (pandas.core.frame.DataFrame): dataframe table

    Returns:
        pandas.core.frame.DataFrame: updated dataframe table
    """

    for row in worksheet_df.itertuples():
        if not row.Book_Lesson:
            continue
        if isinstance(row.Book_Lesson, str):
            print("Lesson string bug:", row.Book_Lesson)
            continue
        elif isinstance(row.Book_Level, str):
            print("Level string bug:", row.Book_Level)
            continue
        worksheet_df.at[row.Index, "Book_Level"] = (
            row.Book_Level * 100 + row.Book_Lesson
        )

    return [worksheet_df]


def merge(gs_name, ws_names):
    """Merges columns of worksheet according to _create_df method

    Args:
        gs_name (str): name of the spreadsheet
        ws_name (str): name of the worksheet (a tab of spreadsheet)
    """

    worksheet, worksheet_df = utils.get_worksheets(gs_name, ws_names)
    worksheet_df = _update_df(worksheet_df[0])
    utils.update_worksheet(worksheet[0], worksheet_df[0])


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    SPREADSHEET_NAME = "Korea - Vocabulary"
    WORKSHEET_NAMES = ("Level 1-2 (modified)",)

    merge(SPREADSHEET_NAME, WORKSHEET_NAMES)
