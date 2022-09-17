import json
import os
import gspread
import pandas as pd
from pathlib import Path

# create arranged vocab
credentials_dict_str = os.environ.get("GOOGLE_CREDENTIALS")
credentials_dict = json.loads(credentials_dict_str)
g_credentials = gspread.service_account_from_dict(credentials_dict)
g_sheet = g_credentials.open("Korea - Vocabulary")


raw_vocab_g_work_sheet = g_sheet.worksheet("raw vocab")
raw_vocab_df = pd.DataFrame(raw_vocab_g_work_sheet.get_all_records())

arranged_vocab_g_work_sheet = g_sheet.worksheet("arranged vocab")
arranged_vocab_df = pd.DataFrame(arranged_vocab_g_work_sheet.get_all_records())

lesson = ""
level = ""
index_add = 0
for row in raw_vocab_df.itertuples():
    kr_en = row.Frequency.split(" - ")
    if len(kr_en) > 1:
        arranged_vocab_df.at[row.Index - index_add, "Korean"] = kr_en[0]
        arranged_vocab_df.at[row.Index - index_add, "Book_English"] = kr_en[1]
        arranged_vocab_df.at[row.Index - index_add, "Book_Level"] = level
        arranged_vocab_df.at[row.Index - index_add, "Book_Lesson"] = lesson
    else:
        index_add += 1
    if 2 < len(row.Frequency) < 5:
        level, lesson = row.Frequency.split(";")

arranged_vocab_df = arranged_vocab_df.fillna("")
arranged_vocab_list = [arranged_vocab_df.columns.values.tolist()]  # header
arranged_vocab_list += arranged_vocab_df.values.tolist()
arranged_vocab_g_work_sheet.update(
    arranged_vocab_list, value_input_option="USER_ENTERED"
)  # value_input_option='USER_ENTERED' / 'RAW'

print("Created arranged vocab")
# check if sheet exist, if not, create one
# cr: g_sheet.add_worksheet("Commands Log", df.shape[0], df.shape[1])
# df = pd.DataFrame(table_data, index=None)









# create Level 1-2
source_dir = Path(__file__).parents[0]
fre_json = Path(f"{source_dir}/freq_dict_kor.json")
top_json = Path(f"{source_dir}/topik_vocab.json")

with open(fre_json, encoding="utf-8") as fre, open(top_json, encoding="utf-8") as top:
    freq = json.load(fre)
    topi = json.load(top)

arranged_vocab_g_work_sheet = g_sheet.worksheet("arranged vocab")
arranged_vocab_df = pd.DataFrame(arranged_vocab_g_work_sheet.get_all_records())

lvl_1_2_g_work_sheet = g_sheet.worksheet("Level 1-2")
lvl_1_2_df = pd.DataFrame(lvl_1_2_g_work_sheet.get_all_records())

# copy + freq + topi
for row in arranged_vocab_df.itertuples():
    lvl_1_2_df.at[row.Index, "Korean"] = row.Korean
    lvl_1_2_df.at[row.Index, "Book_English"] = row.Book_English
    lvl_1_2_df.at[row.Index, "Book_Level"] = row.Book_Level
    lvl_1_2_df.at[row.Index, "Book_Lesson"] = row.Book_Lesson
    if row.Korean in freq:
        word = freq.pop(row.Korean)
        lvl_1_2_df.at[row.Index, "Rank"] = word["rank"]
        lvl_1_2_df.at[row.Index, "Romanization"] = word["romanization"]
        lvl_1_2_df.at[row.Index, "Type"] = word["type"]
        lvl_1_2_df.at[row.Index, "Freq_English"] = word["content"]
        lvl_1_2_df.at[row.Index, "Example_KR"] = word["example_kr"]
        lvl_1_2_df.at[row.Index, "Example_EN"] = word["example_en"]
        lvl_1_2_df.at[row.Index, "Frequency"] = word["frequency"]
        lvl_1_2_df.at[row.Index, "Dispersion"] = word["disp"]
    if row.Korean in topi:
        word = topi.pop(row.Korean)
        lvl_1_2_df.at[row.Index, "TOPIK"] = "I"
        lvl_1_2_df.at[row.Index, "Topik_English"] = word

print("Created vocab from arranged vocab, last duplicated word:", row.Korean)

# freq + topi
# df = pd.DataFrame(columns=["Rank", "Korean"])
for row in freq:
    row_dict = {
        "Korean": row,
        "Rank": freq[row]["rank"],
        "Romanization": freq[row]["romanization"],
        "Type": freq[row]["type"],
        "Freq_English": freq[row]["content"],
        "Example_KR": freq[row]["example_kr"],
        "Example_EN": freq[row]["example_en"],
        "Frequency": freq[row]["frequency"],
        "Dispersion": freq[row]["disp"],
    }
    if row in topi:
        row_dict["TOPIK"] = "I"
        row_dict["Topik_English"] = topi.pop(row)

    lvl_1_2_df.append(row_dict, ignore_index=True)

print("Created vocab from freq book vocab, last freq word:", row)

# topi
for row in topi:
    lvl_1_2_df.append({
        "Korean": row,
        "TOPIK": "I",
        "Topik_English": topi[row],
    }, ignore_index=True)

print("Created vocab from topi, last topi word:", row)



# # adding words from the freq. book
# new_words1 = []
# for word in fre:
#     if word in WORDS:  # if word in freq book is in WORDS in the spreadsheet we loaded
#         lvl_1_2_df.at[WORDS[word], "Rank"] = fre[word]["rank"]
#         lvl_1_2_df.at[WORDS[word], "Romanization"] = fre[word]["romanization"]
#         lvl_1_2_df.at[WORDS[word], "Type"] = fre[word]["type"]
#         lvl_1_2_df.at[WORDS[word], "Freq_English"] = fre[word]["content"]
#         lvl_1_2_df.at[WORDS[word], "Example_KR"] = fre[word]["example_kr"]
#         lvl_1_2_df.at[WORDS[word], "Example_EN"] = fre[word]["example_en"]
#         lvl_1_2_df.at[WORDS[word], "Frequency"] = fre[word]["frequency"]
#         lvl_1_2_df.at[WORDS[word], "Dispersion"] = fre[word]["disp"]
#     else:
#         new_words1.append({
#             "Rank": fre[word]["rank"],
#             "Korean": word,
#             "Romanization": fre[word]["romanization"],
#             "Type": fre[word]["type"],
#             "Freq_English": fre[word]["content"],
#             "Example_KR": fre[word]["example_kr"],
#             "Example_EN": fre[word]["example_en"],
#             "Frequency": fre[word]["frequency"],
#             "Dispersion": fre[word]["disp"]
#         })

# # adding words from topik vocab
# new_words2 = []
# for word in top:
#     if word in WORDS:
#         lvl_1_2_df.at[WORDS[word], "TOPIK"] = "I"
#         lvl_1_2_df.at[WORDS[word], "Topik_English"] = top[word]
#     else:
#         new_words2.append({
#             "Korean": word,
#             "TOPIK": "I",
#             "Topik_English": top[word],
#         })


# save to gsheets
lvl_1_2_df = lvl_1_2_df.fillna("")
listed_table_result = [lvl_1_2_df.columns.values.tolist()]  # header
listed_table_result += lvl_1_2_df.values.tolist()
lvl_1_2_g_work_sheet.update(
    listed_table_result, value_input_option="USER_ENTERED"
)  # value_input_option='USER_ENTERED' / 'RAW'


# new_words_df1 = pd.DataFrame.from_records(new_words1)
# new_words_df2 = pd.DataFrame.from_records(new_words2)

# g_work_sheeta = g_sheet.worksheet("Freq added words")
# g_work_sheetb = g_sheet.worksheet("Topi added words")

# listed_table_result1 = [new_words_df1.columns.values.tolist()]  # header
# listed_table_result1 += new_words_df1.values.tolist()
# g_work_sheeta.update(
#     listed_table_result1, value_input_option="USER_ENTERED"
# )  # value_input_option='USER_ENTERED' / 'RAW'

# listed_table_result2 = [new_words_df2.columns.values.tolist()]  # header
# listed_table_result2 += new_words_df2.values.tolist()
# g_work_sheetb.update(
#     listed_table_result2, value_input_option="USER_ENTERED"
# )  # value_input_option='USER_ENTERED' / 'RAW'
