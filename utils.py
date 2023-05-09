"""Here are utilities - functions that are being used in multiple cogs."""

import json
import os

import gspread
import pandas as pd


class WorksheetNameNotInList(Exception):
    """Exception for Worksheet variable type: only lists are allowed."""


def get_worksheets(gs_name, ws_names):
    """Gets worksheets of spreadsheet.

    Args:
        gs_name (str): name of the spreadsheet
        ws_names (Tuple[str]): name of the worksheets (a tab of spreadsheet)

    Returns:
        List[gspread.worksheet.Worksheet, pandas.core.frame.DataFrame]: (
            list of worksheet tables,
            list of worksheet dataframe tables
        )
    """

    credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
    credentials_dict = json.loads(credentials_dict_str)
    google_credentials = gspread.service_account_from_dict(credentials_dict)
    spreadsheet = google_credentials.open(gs_name)
    # TODO cr: g_sheet.add_worksheet("Commands Log", df.shape[0], df.shape[1])

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
