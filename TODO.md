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
