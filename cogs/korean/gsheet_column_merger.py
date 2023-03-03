"""This script served to convert two tabs (Book_Level, Book_Lesson)
into one (Lesson) in "Korea - Vocabulary" Google Spreadsheet"""

import json
import os

import gspread
import pandas as pd


def _create_df(worksheet):
    """Creates a dataframe out from a google worksheet and merges the columns.

    Merges two columns Book_Lesson and Book_Level into one -> Book_Level

    Args:
        worksheet (gspread.worksheet.Worksheet): worksheet table

    Returns:
        pandas.core.frame.DataFrame: dataframe table
    """

    df = pd.DataFrame(worksheet.get_all_records())

    for row in df.itertuples():
        if not row.Book_Lesson:
            continue
        if isinstance(row.Book_Lesson, str):
            print("Lesson string bug:", row.Book_Lesson)
            continue
        elif isinstance(row.Book_Level, str):
            print("Level string bug:", row.Book_Level)
            continue
        df.at[row.Index, "Book_Level"] = row.Book_Level * 100 + row.Book_Lesson

    return df


def _get_worksheet(gs_name, ws_name):
    """Gets a worksheet instance that is pulled from google sheets.

    Args:
        gs_name (str): name of the google sheets
        ws_name (str): name of the worksheet (a tab of google sheets)

    Returns:
        gspread.worksheet.Worksheet: worksheet table
    """

    credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
    credentials_dict = json.loads(credentials_dict_str)
    g_credentials = gspread.service_account_from_dict(credentials_dict)
    g_sheet = g_credentials.open(gs_name)
    worksheet = g_sheet.worksheet(ws_name)

    return worksheet


def _update_worksheet(dataframe, worksheet):
    """Updates the google worksheet with the dataframe.

    Args:
        dataframe (pandas.core.frame.DataFrame): dataframe table
        worksheet (gspread.worksheet.Worksheet): worksheet table
    """

    dataframe = dataframe.fillna("")
    df_list = [dataframe.columns.values.tolist()]
    df_list += dataframe.values.tolist()
    worksheet.update(df_list, value_input_option="USER_ENTERED")


def merge(gs_name, ws_name):
    """Merges columns of worksheet according to _create_df method

    Args:
        gs_name (str): name of the google sheets
        ws_name (str): name of the worksheet (a tab of google sheets)
    """

    google_worksheet = _get_worksheet(gs_name, ws_name)
    google_dataframe = _create_df(google_worksheet)
    _update_worksheet(google_dataframe, google_worksheet)


if __name__ == "__main__":
    google_sheet_name = "Korea - Vocabulary"
    google_worksheet_name = "Level 1-2 (modified)"

    merge(google_sheet_name, google_worksheet_name)
