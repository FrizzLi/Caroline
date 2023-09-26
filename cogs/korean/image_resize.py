import os
import re
from glob import glob
from pathlib import Path

import cv2
import numpy as np


def get_labelled_file_paths(glob_paths):
    print("Getting labelled file paths... ", end="")

    src_dir = Path(__file__).parents[0]
    paths = []
    for path in glob_paths:
        paths += glob(f"{src_dir}/{path}")

    paths_labelled = {}
    for path in paths:
        file_name = Path(path).stem
        paths_labelled[file_name] = path

    print("Done!")
    return paths_labelled
