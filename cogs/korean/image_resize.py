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

def create_resized_images(image_paths):
    print("Creating resized images... ", end="")

    for path in image_paths:
        image = cv2.imdecode(
            np.fromfile(path, dtype=np.uint8), cv2.IMREAD_UNCHANGED
        )
        image_resized = cv2.resize(image, (0,0), fx=0.25, fy=0.25)
        new_file_name = path[:-5] + path[-4:]
        _, im_buf_arr = cv2.imencode(".png", image_resized)
        im_buf_arr.tofile(new_file_name)
    
    print("Done!")

def delete_resized_images(image_paths, source_image_names):
    print("Deleting resized images worksheets... ", end="")

    resized_images = set(image_paths.values()) - set(source_image_names)
    for resized_image in resized_images:
        os.remove(resized_image)
    
    print("Done!")

def get_source_images(image_paths):
    print("Getting source images... ", end="")

    pattern = re.compile(r"[a-z]+\.png$")
    filtered_paths = []

    for path in image_paths.values():
        if pattern.search(path):
            filtered_paths.append(path)

    print("Done!")
    return filtered_paths

image_paths = get_labelled_file_paths(("data/*/*/vocabulary_images/*",))
source_image_names = get_source_images(image_paths)

# create_resized_images(source_image_names)
# delete_resized_images(image_paths, source_image_names)

# this is for finding out missing images, remember this for next pics
def find_missing_images(image_paths, up_to_lesson_number):
    def get_source_images2(image_paths):
        print("Getting source images... ", end="")

        pattern = re.compile(r"[a-z]+\.png$")
        filtered_paths = []

        for path in image_paths.values():
            if pattern.search(path):
                filtered_paths.append(Path(path).stem[:-1])

        print("Done!")
        return filtered_paths
