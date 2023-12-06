"""Here are utilities - functions that are being used in multiple cogs."""

import json
import os

import gspread
import pandas as pd


class WorksheetNameNotInList(Exception):
    """Exception for Worksheet variable type: only lists are allowed."""


def get_worksheets(gs_name, ws_names, create=False, size=(10_000, 20)):
    """Gets worksheets of spreadsheet. (max 4 worksheets are allowed)

    If create is False and if at least one worksheet was found, it returns the
    worksheet instead of raising an error.

    Args:
        gs_name (str): google spreadsheet name
        ws_names (Tuple[str]): worksheet names (a tab of spreadsheet)
        create (bool, optional): Create new spreadsheet/worksheet if it doesn't
            exist. Defaults to False.
        size (Tuple[str], optional: Number of rows and columns for all
            worksheets. Defaults to (10_000, 20).

    Raises:
        err: SpreadsheetNotFound
        WorksheetNameNotInList: Worksheets are not in a tuple!
        err: WorksheetNotFound

    Returns:
        List[gspread.worksheet.Worksheet, pandas.core.frame.DataFrame]: (
            list of worksheet tables,
            list of worksheet dataframe tables
        )
    """

    print("Getting worksheets... ", end="")

    credentials_dict_str = os.environ["GOOGLE_GSHEET_CREDENTIALS"]
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
            try:
                worksheet_df = pd.DataFrame(worksheet.get_all_records())
                worksheet_dfs.append(worksheet_df)
            except IndexError:
                worksheet_dfs = []
    except gspread.exceptions.WorksheetNotFound as err:
        if len(ws_name) == 1 and ws_names.startswith(ws_name):
            message = "You probably havent put your worksheets into the tuple!"
            raise WorksheetNameNotInList(message) from err
        elif create:
            assert len(ws_names) < 5, "You're creating too many worksheets!"
            for ws_name in ws_names:
                worksheet = spreadsheet.add_worksheet(
                    ws_name, rows=size[0], cols=size[1]
                )
                # worksheets.append(worksheet)
                # listen = ["Listening 1", "Listening 2", "Listening 3", "Listening 4"]
                # read = ["Reading 1", "Reading 2", "Reading 3", "Reading 4"]
                # row = ["Username"] + listen + read
                # if not tracking_ws.get_values("A1"):
                #     tracking_ws.append_row(row)
                try:
                    worksheet_df = pd.DataFrame(worksheet.get_all_records())
                    worksheet_dfs.append(worksheet_df)
                except IndexError:
                    worksheet_dfs = []
                
        elif not worksheet_dfs:
            raise err

    print("Done!")

    return worksheets, worksheet_dfs


def update_worksheet(ws, ws_df):
    """Updates worksheet with dataframe.

    Args:
        ws_df (pandas.core.frame.DataFrame): worksheet dataframe table
        ws (gspread.worksheet.Worksheet): worksheet table
    """

    print("Updating worksheets... ", end="")

    ws_df = ws_df.fillna("")
    df_list = [ws_df.columns.values.tolist()]
    df_list += ws_df.values.tolist()
    ws.update(df_list, value_input_option="USER_ENTERED")

    print("Done!")
