import json
import os
from glob import glob
from pathlib import Path

import gspread
import pandas as pd


def get_worksheet(ws_name):
    credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
    credentials_dict = json.loads(credentials_dict_str)
    g_credentials = gspread.service_account_from_dict(credentials_dict)
    g_sheet = g_credentials.open("Korea - Vocabulary")
    worksheet = g_sheet.worksheet(ws_name)

    return worksheet


def update_worksheet(dataframe, worksheet):
    dataframe = dataframe.fillna("")
    df_list = [dataframe.columns.values.tolist()]
    df_list += dataframe.values.tolist()
    worksheet.update(df_list, value_input_option="USER_ENTERED")


vocab_g_ws = get_worksheet("Level 1-2 (modified)")
vocab_df = pd.DataFrame(vocab_g_ws.get_all_records())

lesson = input("Enter lesson in 3 digits: ")
src_dir = Path(__file__).parents[0]
data_path = f"{src_dir}/data/level_{lesson[0]}/lesson_{int(lesson[-2:])}"
audio_paths = glob(f"{data_path}/vocabulary_audio/*")
audio_words = [Path(audio_path).stem for audio_path in audio_paths]
lesson = int(lesson)

for row in vocab_df.itertuples():
    if row.Lesson > lesson:
        break
    w = row.Korean
    vocab_base_word = w[:-1] if w[-1].isdigit() else w
    if vocab_base_word in audio_words:
        vocab_df.at[row.Index, "Naver_Audio"] = True

update_worksheet(vocab_df, vocab_g_ws)
