import glob, os, json

# select directory     f'{dir_name}/{lesson_name[-1]}unfoundWords.txt'
dir_name = "level_2"
#dir_name = input(f"Which directory you want to make json from?\n\
#{[f for f in os.listdir() if f.startswith('vocab')]}\n")
paths = glob.glob(dir_name + "/lesson_?.txt", recursive=True)
lesson_file_names = []
for name in os.listdir("level_2"):
    if name.startswith("lesson_"):
        lesson_file_names.append(name)

# select keys and values
with open(paths[0], encoding="utf-8") as f:
    first_line = f.readline()
if not first_line:
    first_line = "<NO_CONTENT>"
reverse_lang = "1"
#reverse_lang = input(f"First line looks like this: {first_line}\
#Second is what you will have to write, do you want to switch it? (0/1)\n")

# create json files from text files
'''
for path in paths:
    with open(path, encoding="utf-8") as f:
        vocabd = {}
        for line in f:
            if line == "\n":
                continue
            key, val = line.split(" - ")
            val = val.strip()
            key, val = (val, key) if int(reverse_lang) else (key, val)
            vocabd[key] = val

    if vocabd:
        with open(path + '.json', "w", encoding="utf-8") as f:
            json.dump(vocabd, f, indent=4, sort_keys=True, ensure_ascii=False)
'''
# from pathlib import Path
# import pathlib

def getLessonNames(paths):
    return paths.split('\\')[-1][:-4]

paths2 = list(map(getLessonNames, paths))

from pathlib import Path
import pathlib
current_path = pathlib.Path().absolute()
for lesson_name in paths2:
    Path(f"{current_path}/{dir_name}/{lesson_name}").mkdir(parents=True, exist_ok=True)


vocabd = {}
for path in paths:
    lesson_key = path.split('\\')[-1][:-4]
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
    with open(dir_name + '.json', "w", encoding="utf-8") as f:
        json.dump(vocabd, f, indent=4, sort_keys=True, ensure_ascii=False)

print("Created vocabulary json file from text files.")
# download audio
import urllib.request
import re

'''
vocabAudio = {}
for lesson in vocabd:
    vocabAudio[lesson] = []
    for word in vocabd[lesson]:
        vocabAudio[lesson].append(vocabd[lesson][word])
'''
for lesson_name in paths2:
    print(f"Creating audio for {lesson_name}...")
    # lesson_name = input("From which lesson you want to create audio? (empty char for stopping)\n")
    # if not lesson_name:
    #     break

    korean_lesson_words = []
    for word in vocabd[lesson_name]:
        dict_val = vocabd[lesson_name][word]
        korean_lesson_words.append(dict_val)

    import urllib.request, json, codecs, math, time
    
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
            for z in range (0, len(searchData)):
                if searchData[z]["handleEntry"] in unchangedWordList:
                    if searchData[z]["searchPhoneticSymbolList"]:
                        if searchData[z]["searchPhoneticSymbolList"][0]["phoneticSymbolPath"] != "":
                            timesDownloaded[unchangedWordList.index(searchData[z]["handleEntry"])] += 1
                            mp3Link = searchData[z]["searchPhoneticSymbolList"][0]["phoneticSymbolPath"]
                            if mp3Link not in mp3Links:
                                mp3Links.append(mp3Link)
                                #
                                counter = str(timesDownloaded[unchangedWordList.index(searchData[z]["handleEntry"])])
                                if int(counter) > 1:
                                    print("Skipping one word")
                                    continue
                                paath = f"{os.path.abspath(os.getcwd())}/{dir_name}/{lesson_name}/{searchData[z]['handleEntry']}.mp3"
                                # paath = searchData[z]["handleEntry"] + ".mp3"
                                urllib.request.urlretrieve(mp3Link, paath)
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

    unfoundWords = []
    unchangedWordList = []
    timesDownloaded = []
    mp3Links = []
    # wordInputs = unchangedWordList = input('Enter Words: ').split()
    wordInputs = unchangedWordList = korean_lesson_words
    timesDownloaded = [0] * len(unchangedWordList)
    # Path(f"/{dir_name}/{lesson_name}").mkdir(parents=True, exist_ok=True)

    parseWords(wordInputs)
    
    for z in range(0, len(timesDownloaded)):
        if(timesDownloaded[z] == 0):
            unfoundWords.append(unchangedWordList[z])
    
    if unfoundWords:
        print(",".join(str(x) for x in unfoundWords) + " could not be found.")
        print("Rerunning individual searches for unfound words.")
        print(unfoundWords)
        oldUnfoundWords = unfoundWords
        unfoundWords = []
        for x in range(0, len(oldUnfoundWords)):
            print("Searching: " + str(x+1) + "/" + str(len(oldUnfoundWords)))
            searchWords(oldUnfoundWords[x])
    
        for z in range(0, len(timesDownloaded)):
            if(timesDownloaded[z] == 0):
                unfoundWords.append(unchangedWordList[z])
    
        if unfoundWords:
            unfoundWords_str = ", ".join(str(x) for x in unfoundWords)
            with open(f'{dir_name}/{lesson_name[-1]}unfoundWords.txt', 'w', encoding='utf-8') as f:
                f.write(unfoundWords_str)
            print(unfoundWords_str + " could not be found.")


