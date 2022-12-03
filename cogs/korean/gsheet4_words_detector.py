# updates a row - fills up Listening_Used column
# adds a row - occurences for each word in a lesson

import json
import os
from collections import defaultdict
from pathlib import Path

import gspread
import pandas as pd
from konlpy.tag import Okt

def tokenize_text(file):
    print("Tokenizing Korean text... ", end="")
    okt = Okt()
    try:
        with open(f_listen, encoding="utf-8") as file:
            korean_text = file.read()
            tokenized_text = okt.pos(korean_text, norm=True, stem=True)
            print("Done!")
    except FileNotFoundError as err:
        print(err)
        exit()

    return tokenized_text

def group_by_count(tokenized_text):
    print("Grouping into occurs count and finding duplicates... ", end="")
    occurs = defaultdict(int)
    occurs_check = defaultdict(int)
    word_types = {}

    log_file.write("Detailed tokenization cuz of grouping chaos.\n")
    for token in tokenized_text:
        try:
            if token[1] == "Punctuation" or token[1] == "Foreign":
                log_file.write(f"Skipping garbage... ({token}\n")
                continue
        except Exception as e:
            log_file.write(f"Error skipping token: {e} \n")
        occurs[(token[0])] += 1
        occurs_check[((token[0]), token[1])] += 1  # dup check
        word_types[token[0]] = token[1]

        str_ = " ".join(((token[0]), (token[1])))
        log_file.write(str_ + "\n")

    words = []
    for i in occurs_check:
        words.append(i[0])
    dup_words = [w for w in words if words.count(w) > 1]
    uniq_dup = set(dup_words)
    if uniq_dup:
        print("Found duplicates! There are two different types of word", uniq_dup)
        exit()
    else:
        print("Done!")
    
    return occurs, word_types

def create_df(vocab_g_ws, occurs_g_ws):

    def write_line_msg(portion, word, occurs, word_types, vocab_base_word):
        head = f"Out of {portion}:"
        occur = str(occurs[vocab_base_word])
        type_ = word_types[vocab_base_word]
        str_ = " ".join((head, word, occur, type_))

        log_file.write(str_ + "\n")

    vocab_df = pd.DataFrame(vocab_g_ws.get_all_records())
    occurs_df = pd.DataFrame(occurs_g_ws.get_all_records())

    missing_vocab_set = set()
    log_file.write("\n")
    for row in vocab_df.itertuples():
        w = row.Korean
        vocab_base_word = w[:-1] if w[-1].isdigit() else w
        if vocab_base_word in occurs:
            if row.Lesson != lesson:
                missing_vocab_set.add(w)
                write_line_msg("lesson", w, occurs, word_types, vocab_base_word)
                continue

            # update vocab
            if not row.Listening_Used:
                vocab_df.at[row.Index, "Listening_Used"] = level * 100 + lesson
            
            # update occurances
            count = occurs.pop(vocab_base_word)
            row_dict = {"Word": w, f"Listen_{lesson}": count}
            df = pd.DataFrame(row_dict, columns=occurs_df.columns, index=[0])
            occurs_df = pd.concat([occurs_df, df])

    log_file.write("\n")
    for leftover in occurs:
        if leftover not in missing_vocab_set:
            write_line_msg("vocab", leftover, occurs, word_types, leftover)
    
    return vocab_df, occurs_df

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

lesson = input("Enter: <Lesson> (3 digits)")

source_dir = Path(__file__).parents[0]
lesson_dir = f"{source_dir}/data/level_{level[0]}/lesson_{lesson[-2:]}/"
listen_path_str = f"{lesson_dir}listening_text.txt"
listen_explo_path_str = f"{lesson_dir}explo.txt"
f_listen = Path(listen_path_str)
f_listen_explo = Path(listen_explo_path_str)

# parsing the text into single words
tokenized_text = tokenize_text(f_listen)

# count grouping word occurences and finding duplicates
log_file = open(f_listen_explo, "w", encoding="utf-8")
occurs, word_types = group_by_count(tokenized_text)

# updating google sheets
print("Updating google sheets... ", end="")

vocab_g_ws = get_worksheet("Level 1-2 (Modified)")
occurs_g_ws = get_worksheet("Book occurences")

vocab_df, occurs_df = create_df(vocab_g_ws, occurs_g_ws)
log_file.close()

update_worksheet(vocab_df, vocab_g_ws)
update_worksheet(occurs_df, occurs_g_ws)

print("Done!")

# TODO: implement logging~ no comments / printing needed! imports inside f?
