import glob
import os
import json
import urllib.request
import codecs
import math
import time

from pathlib import Path


def getLessonNames(paths):
    return paths.split("\\")[-1][:-4]


# parameters
dir_name = "level_4"
lesson_num = "5"
reverse_lang = "1"
unfounded_words_save = False

# select vocabulary text files
lesson_path = f"{dir_name}\\lesson_{lesson_num}.txt"
lesson_paths = glob.glob(lesson_path, recursive=True)
name_paths = list(map(getLessonNames, lesson_paths))

# create lesson directories
current_path = Path().absolute()
for lesson_name in name_paths:
    full_path = f"{current_path}/{dir_name}/{lesson_name}"
    Path(full_path).mkdir(parents=True, exist_ok=True)

# create vocabulary json file from text files.
vocabd = {}
for path in lesson_paths:
    lesson_key = path.split("\\")[-1][:-4]
    vocabd[lesson_key] = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line == "\n":
                continue
            key, val = line.split(" - ")
            val = val.strip()
            key, val = (val, key) if int(reverse_lang) else (key, val)
            vocabd[lesson_key][key] = val

if vocabd:
    if os.path.exists(f"{dir_name}.json"):
        with open(f"{dir_name}.json", "r", encoding="utf-8") as f:
            old_vocabd = json.load(f)
            vocabd = {**old_vocabd, **vocabd}
    with open(f"{dir_name}.json", "w", encoding="utf-8") as f:
        json.dump(vocabd, f, indent=4, sort_keys=True, ensure_ascii=False)


def searchWords(koreanWords):
    url = ('https://ko.dict.naver.com/api3/koko/search?' + urllib.parse.urlencode({'query': koreanWords}) + '&range=word&page=1')
    response = urllib.request.urlopen(url)
    reader = codecs.getreader("utf-8")
    jsonInfo = json.load(reader(response))
    pageCount = jsonInfo["pagerInfo"]["totalPages"]
    searchData = jsonInfo["searchResultMap"]["searchResultListMap"]["WORD"]["items"]

    for pageCountInc in range(0, pageCount):
        if pageCountInc != 0:
            url = ('https://ko.dict.naver.com/api3/koko/search?' + urllib.parse.urlencode({'query': koreanWords}) + '&range=word&page=' + str(pageCountInc+1))
        response = urllib.request.urlopen(url)
        reader = codecs.getreader("utf-8")
        jsonInfo = json.load(reader(response))
        searchData = jsonInfo["searchResultMap"]["searchResultListMap"]["WORD"]["items"]
        for z in range(0, len(searchData)):
            if searchData[z]["handleEntry"] in unchangedWordList:
                if searchData[z]["searchPhoneticSymbolList"]:
                    if searchData[z]["searchPhoneticSymbolList"][0]["phoneticSymbolPath"] != "":
                        timesDownloaded[unchangedWordList.index(searchData[z]["handleEntry"])] += 1
                        mp3Link = searchData[z]["searchPhoneticSymbolList"][0]["phoneticSymbolPath"]
                        if mp3Link not in mp3Links:
                            mp3Links.append(mp3Link)
                            counter = str(timesDownloaded[unchangedWordList.index(searchData[z]["handleEntry"])])
                            if int(counter) > 1:
                                print("Skipping one word")
                                continue
                            paath = f"{os.path.abspath(os.getcwd())}/{dir_name}/{lesson_name}/{searchData[z]['handleEntry']}.mp3"
                            try:
                                urllib.request.urlretrieve(mp3Link, paath)
                            except Exception:
                                print("HTTP error..?")

                            time.sleep(.3)


def parseWords(listOfWords):
    for x in range(0, math.floor(len(listOfWords)/10)):
        tempWords = []
        for y in range(0, 10):
            tempWords.append(listOfWords[x*10+y])

        print("Searching: " + str(x+1) + "/" + str(math.ceil(len(listOfWords)/10)))
        searchWords(tempWords)

    tempWords = []
    for y in range(math.floor(len(listOfWords)/10)*10+1, len(listOfWords)):
        tempWords.append(listOfWords[y])
    print("Searching: " + str((math.ceil(len(listOfWords)/10))) + "/" + str(math.ceil(len(listOfWords)/10)))
    searchWords(tempWords)


# download audio part
for lesson_name in name_paths:
    print(f"Creating audio for {lesson_name}...")

    korean_lesson_words = []
    for word in vocabd[lesson_name]:
        dict_val = vocabd[lesson_name][word]
        korean_lesson_words.append(dict_val)

    unfoundWords = []
    unchangedWordList = []
    timesDownloaded = []
    mp3Links = []
    wordInputs = unchangedWordList = korean_lesson_words
    timesDownloaded = [0] * len(unchangedWordList)
    parseWords(wordInputs)

    for z in range(0, len(timesDownloaded)):
        if timesDownloaded[z] == 0:
            unfoundWords.append(unchangedWordList[z])

    if unfoundWords:
        print(",".join(str(x) for x in unfoundWords) + " could not be found.")
        print("Rerunning individual searches for unfound words.")
        print(unfoundWords)
        oldUnfoundWords = unfoundWords
        unfoundWords = []
        for x in range(0, len(oldUnfoundWords)):
            print("Searching: " + str(x + 1) + "/" + str(len(oldUnfoundWords)))
            searchWords(oldUnfoundWords[x])

        for z in range(0, len(timesDownloaded)):
            if timesDownloaded[z] == 0:
                unfoundWords.append(unchangedWordList[z])

        # saving unfounded words into text files
        if unfoundWords and unfounded_words_save:
            unfoundWords_str = ", ".join(str(x) for x in unfoundWords)
            n = lesson_name[-1] if lesson_name[-2] == "_" else lesson_name[-2:]
            path = f"{dir_name}/{n}unfoundWords.txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(unfoundWords_str)
            print(unfoundWords_str + " could not be found.")

# https://www.reddit.com/r/Korean/comments/a0wkq7/tip_mass_download_audio_files_from_naver/
