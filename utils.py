"""Here are utilities - functions that are being used in multiple cogs."""

import json
import os

import gspread
import pandas as pd


class WorksheetNameNotInList(Exception):
    """Exception for Worksheet variable type: only lists are allowed."""


def get_worksheets(gs_name, ws_names, create=False):
    """Gets worksheets of spreadsheet.

    Args:
        gs_name (str): google spreadsheet name
        ws_names (Tuple[str]): worksheet names (a tab of spreadsheet)
        create (bool): create new spreadsheet/worksheet if it doesn't exist

    Returns:
        List[gspread.worksheet.Worksheet, pandas.core.frame.DataFrame]: (
            list of worksheet tables,
            list of worksheet dataframe tables
        )
    """

    credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
    credentials_dict = json.loads(credentials_dict_str)
    google_credentials = gspread.service_account_from_dict(credentials_dict)
    try:
        spreadsheet = google_credentials.open(gs_name)
    except gspread.exceptions.SpreadsheetNotFound as err:
        if create:
            spreadsheet = google_credentials.create(gs_name)
        else:
            raise err

    worksheets = []
    worksheet_dfs = []
    try:
        for ws_name in ws_names:
            worksheet = spreadsheet.worksheet(ws_name)
            worksheets.append(worksheet)
            worksheet_df = pd.DataFrame(worksheet.get_all_records())
            worksheet_dfs.append(worksheet_df)
    except gspread.exceptions.WorksheetNotFound as err:
        if len(ws_name) == 1 and ws_names.startswith(ws_name):
            message = "You probably haven't put your worksheets into the list!"
            raise WorksheetNameNotInList(message) from err
        elif create:
            assert len(ws_names) < 5, "You're creating too many worksheets!"
            for ws_name in ws_names:
                worksheet = spreadsheet.add_worksheet(
                    ws_name, rows="10000", cols="20"
                )
                worksheets.append(worksheet)
                worksheet_df = pd.DataFrame(worksheet.get_all_records())
                worksheet_dfs.append(worksheet_df)
        else:
            raise err

    return worksheets, worksheet_dfs


def update_worksheet(ws, ws_df):
    """Updates worksheet with dataframe.

    Args:
        ws_df (pandas.core.frame.DataFrame): worksheet dataframe table
        ws (gspread.worksheet.Worksheet): worksheet table
    """

    ws_df = ws_df.fillna("")
    df_list = [ws_df.columns.values.tolist()]
    df_list += ws_df.values.tolist()
    ws.update(df_list, value_input_option="USER_ENTERED")
