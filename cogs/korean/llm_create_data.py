import json
import os
import re
import sys
from pathlib import Path

import torch
from diffusers import DiffusionPipeline
from dotenv import find_dotenv, load_dotenv
from llm_chatgpt_utils import get_addition_word_data

load_dotenv(find_dotenv())
PATH = os.environ["STABLE_DIFFUSION_SRC"]

def get_pipeline():
    pipe = DiffusionPipeline.from_pretrained(PATH, custom_pipeline="lpw_stable_diffusion", torch_dtype=torch.float32)
    pipe.enable_sequential_cpu_offload()
    pipe = DiffusionPipeline.from_pretrained(PATH, custom_pipeline="lpw_stable_diffusion", torch_dtype=torch.float32)
    pipe = pipe.to("cuda")

    # maybe unnecessarily commented the checkers in diffusion lib
    pipe.safety_checker = None
    pipe.requires_safety_checker = False

    return pipe

def get_dir_paths(prev_lesson, current_lesson):
    jso_level, jso_lesson = divmod(prev_lesson, 100)
    img_level, img_lesson = divmod(current_lesson, 100)
    src_dir = Path(__file__).parents[0]
    word_data_json_path = Path(f"{src_dir}/data/level_{jso_level}/lesson_{jso_lesson}/word_data.json")
    img_dir_path = Path(f"{src_dir}/data/level_{img_level}/lesson_{img_lesson}/vocabulary_images")
    img_dir_path.mkdir(parents=True, exist_ok=True)

    return img_dir_path, word_data_json_path

def get_sentence_example(sentence_example):
    pattern = r'\(.*?\)'
    bracket_text = re.findall(pattern, sentence_example)
    bracket_text = [sentence[1:-1] for sentence in bracket_text]
    split_text = re.split(pattern, sentence_example)
    clean_text = [t.strip() for t in split_text if t.strip()]

    return bracket_text, clean_text

def create_data(lesson_range, image_tags_add, negative_prompt):
    wss, ws_dfs = utils.get_worksheets("Korea - Vocabulary", ("Level 1-2 (modified)",))
    ws, ws_df = wss[0], ws_dfs[0]
    pipeline = get_pipeline()
    lesson_start, lesson_end = lesson_range.split("-")
    lesson_start = int(lesson_start)
    lesson_end = int(lesson_end)
    prev_lesson = 100

    all_word_data = []  # TODO this needs to store korean word as well, for easy debugging...!

    for row in ws_df.itertuples():
        print(f"{row.Lesson} - {row.Korean}")

        # skip missing lesson number
        if not row.Lesson:
            continue

        # skip low lesson number
        if row.Lesson < lesson_start:
            continue

        # end
        elif row.Lesson > lesson_end:
            with open(word_data_json_path, "w", encoding="utf-8") as file:
                json.dump(all_word_data, file, indent=4)
            break

        # next lesson, save json
        if prev_lesson != row.Lesson:
            # TODO: WHEN - upon next creating, check whether this words
            img_dir_path, word_data_json_path = get_dir_paths(prev_lesson, row.Lesson)
            if prev_lesson != 100:
                with open(word_data_json_path, "w", encoding="utf-8") as file:
                    json.dump(all_word_data, file, indent=4)
                all_word_data = []
            prev_lesson = row.Lesson

            # wtf how come that the json is being for every lesson but see no saving in code
            if row.Lesson > lesson_end:
                break

        english = row.Book_English
        korean = row.Korean
        korean_no_num = korean[:-1] if korean[-1].isdigit() else korean

        # creating additional data with ChatGPT
        word_data = get_addition_word_data(korean_no_num, english)
        all_word_data.append(word_data)

        # get sentence example text and split it into two vars for two rows
        en_text, kr_text = get_sentence_example(word_data["sentence_example"])

        # update gspread data
        ws_df.at[row.Index, "English_Add"] = word_data["additional_translations"]
        ws_df.at[row.Index, "Explanation"] = word_data["explanation_of_expression"]
        ws_df.at[row.Index, "Syllables"] = word_data["explanation_of_syllables"]
        ws_df.at[row.Index, "Example_EN2"] = "; ".join(en_text)
        ws_df.at[row.Index, "Example_KR2"] = "; ".join(kr_text)

        # create image
        image_prompts = [
            f"{word_data['image_description0']}; {word_data['image_tags']} {image_tags_add}",
            f"{word_data['image_description0']}; {image_tags_add}",
            f"{word_data['image_description1']}; {image_tags_add}",
            f"{word_data['image_description1']}; {word_data['image_tags']} {image_tags_add}",
            f"{word_data['image_description2']}; {word_data['image_tags']} {image_tags_add}",
            f"{word_data['image_description3']}; {word_data['image_tags']} {image_tags_add}",
        ]

        file_name_word = korean.replace("?", "")
        for letter, image_prompt in zip("abcdef", image_prompts):
            image = pipeline(image_prompt, negative_prompt=negative_prompt).images[0]
            fname_path = Path(f"{img_dir_path}/{file_name_word}{letter}.png")
            image.save(fname_path)

        utils.update_worksheet(ws, ws_df)


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    lesson_range = "106-110"
    image_tags_add = "((hyper realistic photograph)), (concept art), masterpiece, soft colors, happy"
    negative_prompt = "((text)), (letters), watermark, sign, signature, movie poster, username"

    create_data(lesson_range, image_tags_add, negative_prompt)

# include Expression alone prompt (kimbap)
