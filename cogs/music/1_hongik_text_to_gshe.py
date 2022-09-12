import json
import os
import gspread
import pandas as pd
from pathlib import Path

credentials_dict = os.environ.get("GOOGLE_CREDENTIALS")
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet = g_credentials.open("Korea - Vocabulary")

# cr: g_sheet.add_worksheet("Commands Log", df.shape[0], df.shape[1])
g_work_sheet = g_sheet.worksheet("Level 1-2")
g_work_sheeta = g_sheet.worksheet("Level 1-2a")
g_work_sheetb = g_sheet.worksheet("Level 1-2b")

# table_data = []
# df = pd.DataFrame(table_data, index=None)
cmd_df = pd.DataFrame(g_work_sheet.get_all_records())

# fill missing cells
source_dir = Path(__file__).parents[0]
fre_json = Path(f"{source_dir}/freq_dict_kor.json")
top_json = Path(f"{source_dir}/topik_vocab.json")
with open(fre_json, encoding="utf-8") as file:
    fre = json.load(file)

lesson = ""
level = ""
WORDS = {}
for row in cmd_df.itertuples():
    WORDS[row.Korean] = row.Index

new_words1 = []
for word in fre:
    if word in WORDS:
        cmd_df.at[WORDS[word], "Rank"] = fre[word]["rank"]
        cmd_df.at[WORDS[word], "Romanization"] = fre[word]["romanization"]
        cmd_df.at[WORDS[word], "Type"] = fre[word]["type"]
        cmd_df.at[WORDS[word], "Freq_English"] = fre[word]["content"]
        cmd_df.at[WORDS[word], "Example_KR"] = fre[word]["example_kr"]
        cmd_df.at[WORDS[word], "Example_EN"] = fre[word]["example_en"]
        cmd_df.at[WORDS[word], "Frequency"] = fre[word]["frequency"]
        cmd_df.at[WORDS[word], "Dispersion"] = fre[word]["disp"]
    else:
        new_words1.append({
            "Rank": fre[word]["rank"],
            "Korean": word,
            "Romanization": fre[word]["romanization"],
            "Type": fre[word]["type"],
            "Freq_English": fre[word]["content"],
            "Example_KR": fre[word]["example_kr"],
            "Example_EN": fre[word]["example_en"],
            "Frequency": fre[word]["frequency"],
            "Dispersion": fre[word]["disp"]
        })





with open(top_json, encoding="utf-8") as file:
    top = json.load(file)

new_words2 = []
for word in top:
    if word in WORDS:
        cmd_df.at[WORDS[word], "TOPIK"] = "I"
        cmd_df.at[WORDS[word], "Topik_English"] = top[word]
    else:
        new_words2.append({
            "Korean": word,
            "TOPIK": "I",
            "Topik_English": top[word],
        })


#cmd_df = pd.concat([cmd_df, new_words_df1])
#cmd_df = pd.concat([cmd_df, new_words_df2])

    # copying from gdoc
    # kr_en = row.Rank.split(" - ")
    # if len(kr_en) > 1:
    #     cmd_df.at[row.Index, "Korean"] = kr_en[0]
    #     cmd_df.at[row.Index, "Book_English"] = kr_en[1]
    #     cmd_df.at[row.Index, "Book_Level"] = level
    #     cmd_df.at[row.Index, "Book_Lesson"] = lesson
    # if 2 < len(row.Rank) < 5:
    #     level, lesson = row.Rank.split(";")

    # cmd_df.at[row.Index, "Rank"] = ""

# save to gsheets
# cmd_df.fillna("")
listed_table_result = [cmd_df.columns.values.tolist()]  # header
listed_table_result += cmd_df.values.tolist()
g_work_sheet.update(
    listed_table_result, value_input_option="USER_ENTERED"
)  # value_input_option='USER_ENTERED' / 'RAW'


new_words_df1 = pd.DataFrame.from_records(new_words1)
new_words_df2 = pd.DataFrame.from_records(new_words2)

listed_table_result1 = [new_words_df1.columns.values.tolist()]  # header
listed_table_result1 += new_words_df1.values.tolist()
g_work_sheeta.update(
    listed_table_result1, value_input_option="USER_ENTERED"
)  # value_input_option='USER_ENTERED' / 'RAW'

listed_table_result2 = [new_words_df2.columns.values.tolist()]  # header
listed_table_result2 += new_words_df2.values.tolist()
g_work_sheetb.update(
    listed_table_result2, value_input_option="USER_ENTERED"
)  # value_input_option='USER_ENTERED' / 'RAW'