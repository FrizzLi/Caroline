"""
"Korea - Vocabulary" Spreadsheet:
 - fills up "Naver_Audio" column in "Level 1-2 (raw)" tab with TRUE value
   if we have audio for that word, otherwise leave it empty
"""

import sys
from glob import glob
from pathlib import Path


def _fill_df(audio_words, lesson, ws_lvl_df):
    """Fills Audio_Naver column with True if audio file is present for word.

    Args:
        audio_words (List[str]): words that have audio files
        lesson (int): number of lesson we're choosing the words from
        ws_lvl_df (pandas.core.frame.DataFrame): worksheet df to be filled

    Returns:
        pandas.core.frame.DataFrame: filled worksheet dataframe
    """

    for row in ws_lvl_df.itertuples():
        if not row.Lesson:
            continue
        if row.Lesson > lesson:
            break
        word = row.Korean
        vocab_base_word = word[:-1] if word[-1].isdigit() else word
        if vocab_base_word in audio_words:
            ws_lvl_df.at[row.Index, "Naver_Audio"] = True

    return ws_lvl_df


def fill_audio_occurences(gs_name, ws_names):
    """Fills Naver_Audio occurences in worksheet.

    Args:
        gs_name (str): google spreadsheet name
        ws_names (str): names of the worksheet
    """

    wss, ws_dfs = utils.get_worksheets(gs_name, ws_names)
    ws_lvl, ws_lvl_df = wss[0], ws_dfs[0]

    lesson = input("Enter lesson in 3 digits: ")
    src_dir = Path(__file__).parents[0]
    data_path = f"{src_dir}/data/level_{lesson[0]}/lesson_{int(lesson[-2:])}"
    audio_paths = glob(f"{data_path}/vocabulary_audio/*")
    audio_words = [Path(audio_path).stem for audio_path in audio_paths]

    lesson_num = int(lesson)

    ws_lvl_df = _fill_df(audio_words, lesson_num, ws_lvl_df)

    utils.update_worksheet(ws_lvl, ws_lvl_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    SPREADSHEET_NAME = "Korea - Vocabulary"
    WORKSHEET_NAMES = ("Level 1-2 (raw)",)

    fill_audio_occurences(SPREADSHEET_NAME, WORKSHEET_NAMES)
