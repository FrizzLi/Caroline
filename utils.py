import json
import os

import gspread
import pandas as pd


def get_worksheets(gs_name, ws_names):
    """Gets worksheets of spreadsheet.

    Args:
        gs_name (str): name of the spreadsheet
        ws_name (str): name of the worksheets (a tab of spreadsheet)

    Returns:
        List[gspread.worksheet.Worksheet, pandas.core.frame.DataFrame]: (
            list of worksheet tables,
            list of worksheet dataframe tables
        )
    """

    credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
    credentials_dict = json.loads(credentials_dict_str)
    g_credentials = gspread.service_account_from_dict(credentials_dict)
    g_sheet = g_credentials.open(gs_name)

    worksheets = []
    worksheet_dfs = []
    for ws_name in ws_names:
        worksheet = g_sheet.worksheet(ws_name)
        worksheets.append(worksheet)
        worksheet_df = pd.DataFrame(worksheet.get_all_records())
        worksheet_dfs.append(worksheet_df)

    return worksheets, worksheet_dfs


def update_worksheet(worksheet, worksheet_df):
    """Updates google worksheet with dataframe.

    Args:
        worksheet_df (pandas.core.frame.DataFrame): worksheet dataframe table
        worksheet (gspread.worksheet.Worksheet): worksheet table
    """

    worksheet_df = worksheet_df.fillna("")
    df_list = [worksheet_df.columns.values.tolist()]
    df_list += worksheet_df.values.tolist()
    worksheet.update(df_list, value_input_option="USER_ENTERED")
