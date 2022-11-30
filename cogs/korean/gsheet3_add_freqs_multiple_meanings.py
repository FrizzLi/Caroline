# "Korea - Vocabulary" Google Spreadsheet
# add numbered freq words (more meanings) below base word in "Level 1-2" tab

# (this was also used to transition topic words into freq. vocab)

import json
import os
from pathlib import Path

import gspread
import pandas as pd

# Function to insert row in the dataframe
def Insert_row_(row_number, df, row_value):
    # Slice the upper half of the dataframe
    df1 = df[0:row_number]

    # Store the result of lower half of the dataframe
    df2 = df[row_number:]

    # Insert the row in the upper half dataframe
    df1.loc[row_number]=row_value

    # Concat the two dataframes
    df_result = pd.concat([df1, df2])

    # Reassign the index labels
    df_result.index = [*range(df_result.shape[0])]

    # Return the updated dataframe
    return df_result

credentials_dict_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(credentials_dict_str)
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet_main = g_credentials.open("Korea - Vocabulary")


source_dir = Path(__file__).parents[0]
fre_json = Path(f"{source_dir}/data/gsheet/freq_dict_kor.json")

with open(fre_json, encoding="utf-8") as fre:
    freq = json.load(fre)

lvl_1_2_g_work_sheet = g_sheet_main.worksheet("Level 1-2")
lvl_1_2_df = pd.DataFrame(lvl_1_2_g_work_sheet.get_all_records())

added_num = 0

# copy + freq + topi
for row in lvl_1_2_df.itertuples():
    for num in range(1, 6):
        numered_word = f"{row.Korean}{num}"
        if numered_word in freq:
            added_num += 1
            word = freq.pop(numered_word)
            row_value = [
                word["rank"],
                numered_word,
                "",
                word["content"],
                "",
                word["example_en"],
                word["example_kr"],
                "",
                "",
                word["type"],
                word["romanization"],
                word["frequency"],
                word["disp"],
                ""
            ]
            lvl_1_2_df = Insert_row_(row.Index + added_num, lvl_1_2_df, row_value)

df = lvl_1_2_df.sort_index().reset_index(drop=True)

# save to gsheets
lvl_1_2_df = lvl_1_2_df.fillna("")
lvl_1_2_list = [lvl_1_2_df.columns.values.tolist()]  # header
lvl_1_2_list += lvl_1_2_df.values.tolist()
lvl_1_2_g_work_sheet.update(lvl_1_2_list, value_input_option="USER_ENTERED")
