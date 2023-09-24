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


if __name__ == "__main__":
    sys.path.append(str(Path(__file__).parents[2]))
    import utils

    lesson_range = "106-110"
    image_tags_add = "((hyper realistic photograph)), (concept art), masterpiece, soft colors, happy"
    negative_prompt = "((text)), (letters), watermark, sign, signature, movie poster, username"

    create_data(lesson_range, image_tags_add, negative_prompt)

# include Expression alone prompt (kimbap)
