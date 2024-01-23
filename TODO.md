# TODO List

### In Progress

- [ ]

### Todo
- [ ] surveillance.py: Voice stats graphs, Process old logs
- [ ] Optimization of everything:
  - Pylint (errs, with cmd! -> 9.0 score above)
  - Async
  - Logs (function calls?!)
  - Document/Test (ai_algo.py - _apply_actions test (rmv))
- [ ] music.py:
  - [ ] UPD: Deep opt., polishing with other bots as insp., apply logs instead of prints (+wrappers?)
  - [ ] IMP: Most played dropdown choose at all times; auto select with distribution (radio)

- [ ] korean.py
  - [ ] UPD format the output more nicely after session is done (check opts; clarify notes for certain session types with bold font)
  - [ ] UPD inform that you can uncover the expressions to see the answer (help cmd)
  - [ ] IMP Notes command? /help only for the session, too much text might drive users away
  - [ ] UPD Note - more meanings chaos (with numbers, without numbers[;;;])

  - [ ] IMP Click to start button (resolve pressing the same option in dropdown) ---> FIX: ending the session and fast opening a new one will crash (cuz saving worksheets!)
  - [ ] FIX/IMP: Left voice -> bot left, and forgot about session in text channel (no guesses(?)), automatically cancel the session upon leave; Remind to leave the voice chat when its over, or disconnect the user (one more button!) / Auto connect + Auto disconnect from voice when interacting with interface

  - [ ] PORTFOLIO: Present on website - Show the graphs of right/wrongs for each person
  - [ ] IMP: Speech recognition (not only google's voice.. [because of phrases later!])
  - [ ] IMP: Audio downloading (current script is published in memo bookmark)
  - [ ] IMP: Auto-repeat (check all audio get max length) + stop sound if buttoned
  - [ ] IMP: New selection (no selection needed, auto calculate the best selection - new words (no 50!) / review)
  - [ ] IMP: Add Grammar
  - [ ] IMP: Vocab/User data opt. for publishing (Elastic search instead of gsheet)
  - [ ] IMP: Translation (for reading/listening)
  - [ ] IMP: Session visualization (streak play, github-like)
  - [ ] UPD: CHECK Rearranged columns in google sheets --> might need update for that, check it
  - [ ] ???: CHECK Commit - [UPD] move connect/disconnect from music.py into shared utils https://github.com/freezpmark/personal-discord-bot/commit/e69a415341308cc6004442a331903421b5692099#diff-35606ac1b506923433a05188f57dfd000f0b13a62abc984a0ea8f41ab0a14fbf

  - [ ] LLM/ChatGPT IMP:
    - [ ] IMP: Questions (reading & listening)
    - [ ] IMP: Create expressions (for listening/reading, grammar/vocab)
    - [ ] IMP: Spreadsheet update with extra info (issue with Example column - synonyms not recognized)
    - [ ] IMP: Stable Diffusion - add more pics (automate without checking them) [text -> img -> text -> same text? (supervised)]
    - [ ] IMP: LLM specialized for base form detection (for Reading/Listening to build vocab)
    - [ ] IMP: Gspread: Phrases/Two words - split, find words, if both exist, create () with 를/을 ...
    - [ ] IMP: Similarity between words in vocab session (meanings/spelling/antonyms)
    - [ ] IMP: Buttons for Listening, Reading (exploration with -> grammar used, vocab used, translation)

  - [ ] IDEAS TO IMPLEMENT:
    - [ ] Writing vocab f.: vocab_writing [REM] vocab writing function
    - [ ] Audio for reading too (?) Lvl 3 already done
  - [ ] LLM IDEAS TO IMPLEMENT:
    - [ ] D&D idea of learning (inventory - nouns, adjs, etc. --- together/solo)
    - [ ] Create your own learning vocab list! (getting the vocab - kdrama, sub.)
    - [ ] Creating content with your Vocab
    - [ ] Clustering words relations (similar words opts!)
    - [ ] Well known story concept .. harry potter... take ur favo char... Be with it
    - [ ] Create dynamic adaptable content... sth they can build on, commit
    - [ ] Knowledge graph? Similarity between Korean words (spaced in dash app) [2 syllables same, same base english word]

### Done ✓

- [x] Create my first TODO.md  






Korean Study Guide Text
        text_general = """
`/vocab ` (vocabulary learning)
`/listen ` (listening practice)
`/read ` (reading practice)

Followed by the command, you have to type a certain number that determines what kind of lesson is going to be picked. There are 4 levels and each contains 30 lessons.
ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        """
        text_vocab = """ 
1. One **(1)** - finds and starts the next user's unknown lesson session 
 - [use this when you want to learn something new]
2. Pure Hundreds **(100, ..., 400)** starts review session of words that you have already guessed at least once in a certain level (level is represented by the hundred decimal)
 - [use this when you want to practice what you've already learned in a certain level]
3. Hundreds up to 30 **(101, ..., 130)** starts session of one specific lesson in a certain level (hundred decimal represents the level, the number up to 30 represents a lesson).
 - [use this when you want to learn/practice one specific lesson]
        """
        text_vocab_interact = """
✅ - know without thinking
🤔 - know after thinking
🧩 - know only partially
❌ - not know
🔁 - repeat the audio
📄 - display more info about the word
🔚 - end the session

If you encounter a word for the first time, it displays all the info about the word. If you encountered it at least once, info will be hidden. The frequency of certain words showing up depend on the marks you click (especially in the review sessions that also take time into account)
ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ
        """
        text_listen = """ 
1. One **(1)** finds and starts the lesson with the highest number in which all the words were already guessed
2. Hundreds up to 30 **(101, ..., 130)** starts session of one specific lesson in a certain level
        """
        text_listen_interact = """
⏪ - rewind by 10 seconds
⏸️ - pause
⏩ - next track
🔁 - repeat track
🔚 - end the session

*Note that listening sessions starts from 102 and reading sessions from 105.*

**Used resources**:
 - Hongik University Language School audio files and grammar notes
- Vocabulary audio downloaded from Naver
- A Frequency Dictionary of Korean (book)
- content generated by ChatGPT
        """

        text_links = f"""
 - [Level 1 Grammar](https://docs.google.com/document/d/1BTBgvSy7VGwoD1AD4lCqpy0_7Zn-U_6smeU0GKdFjoU/edit?usp=sharing) (Google Doc - grammar reference that is being used in listening/reading sessions)
- [User's stats](https://docs.google.com/spreadsheets/d/1wFbxnhwc2BQAEAL_KNCPfBYoLwhdcGR5FuVKxlwjSJg/edit?usp=sharing) (Google Sheet - information about user's guessings and sorted knowledge of words)
- [Vocabulary](https://docs.google.com/spreadsheets/d/1mhYVWtqUWF-vVjwCz3cvlhZxH6GjfU6XyLVd2lNcWe0/edit?usp=sharing) (Google Sheet -  whole set of korean words)"""
