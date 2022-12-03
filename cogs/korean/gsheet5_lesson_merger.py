import json
import os
from collections import defaultdict
from pathlib import Path

import gspread
import pandas as pd
from konlpy.tag import Okt

def create_df(vocab_g_ws):
    vocab_df = pd.DataFrame(vocab_g_ws.get_all_records())

    for row in vocab_df.itertuples():
        if not row.Book_Lesson:
            continue
        if isinstance(row.Book_Lesson, str):
            print("Lesson string bug:", row.Book_Lesson)
            continue
        elif isinstance(row.Book_Level, str):
            print("Level string bug:", row.Book_Level)
            continue
        vocab_df.at[row.Index, "Book_Level"] = row.Book_Level * 100 + row.Book_Lesson

    return vocab_df

def get_worksheet(ws_name):
    credentials_dict_str = os.environ.get("GOOGLE_CREDENTIALS")
    credentials_dict = json.loads(credentials_dict_str)
    g_credentials = gspread.service_account_from_dict(credentials_dict)
    g_sheet = g_credentials.open("Korea - Vocabulary")
    worksheet = g_sheet.worksheet(ws_name)

    return worksheet

def update_worksheet(dataframe, worksheet):
    dataframe = dataframe.fillna("")
    df_list = [dataframe.columns.values.tolist()]  # header
    df_list += dataframe.values.tolist()
    worksheet.update(df_list, value_input_option="USER_ENTERED")

vocab_g_ws = get_worksheet("Level 1-2 (backup)")
vocab_df = create_df(vocab_g_ws)
update_worksheet(vocab_df, vocab_g_ws)