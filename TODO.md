# TODO List

### In Progress

- [ ]

### Todo

- [ ] Polish Discord related stuff: Pylint, Document, Optimize code, and Async, Logs
- [ ] Pylint - resolve all errors (or at least have above 9.0 score)
- [ ] Opts prompts: find mistakes in following code, Write a docstring for the following function

- [ ] Integrate ChatGPT with my Discord server
- [ ] ai_algo.py: Tests (_apply_actions test (rmv), docs)
- [ ] surveillance.py: Voice stats graphs, Process old logs
- [ ] music.py: 
  - [ ] Create radio (automatically picks songs)
  - [ ] Do deep opt., polishing with other bots as insp., apply logs instead of prints (+wrappers?)
  - [ ] Bug: when the bot leaves the voice, refresh button still works..
  - [ ] Voice: dont leave right away when everybody leaves, wait 10 seconds at least
  - [ ] Like button (to remember URL for next time)

- [ ] korean.py
  - [ ] Bug - msg not removed, why (left the channel too soon maybe)
  - [ ] IMP - when to go for new words or stick with review - automatically calculate
  - [ ] FIX: left voice -> bot left, and forgot about session in text channel (no guesses(?))
  - [ ] Check percentage calculation
  - [ ] Add translations for reading/listening
  - [ ] Calculate avg scores, whether there was improvement (watch time though, only at end update)
  - [ ] Session time, unselect opt. (cannot select mistaken opt.)

  - [ ] create spreadsheet for each user?
  - [ ] Publishing it: Make it in your server (networking) [UPON WEBSITE BUILDING], Elastic search for gsheet data for all users?
  - [ ] Example sentences do not distinguish synonyms issue

  - [ ] Discarded:
    - [ ] Scoring system, vocab picking:
      - [ ] Create longer expressions as partial listening idea
      - [ ] ~create stats before session..!? At the start of the day or sth? (after longer time, the scorings would be different, but its not that important)
      - [ ] ~Add visualization on worksheet, streak play, daily q, graph of practice intensity like on github
      - [ ] ~Buttons: Disable during play
      - [ ] ~Function vocab_writing [REM] vocab writing function (IMP maybe later)
      - [ ] ~Add audio for reading texts?
  
    - [ ] AI/ChatGPT Problems:
      - [ ] Add pictures for each word - those images are kinda weird, maybe donable, but not paying attention to it now
      - [ ] More meanings chaos (with numbers, without numbers[;;;])
      - [ ] No precise base form detection for Reading/Listening vocabulary detection (ChatGPT isn't sufficient, combine it with my script? For now 10 Lessons are enough... can include it;; take chatgpt output, pass it into konlpy, check only words that are not in the vocab)
      - [ ] Pharses/Two words in vocab gspread - split, find words, if both exist, create () with 를/을 / 이/가 (+eng)
      - [ ] Similarity: meanings(vs) / spelling / antonyms (level 2 and more); 대충, 정도, 주소, 조사
      - [ ] Listening, Reading: Sentence Click for exploration -> grammar, vocab, translation
      - [ ] Create questions for reading/listening
      - [ ] Create dynamic adaptable content... (many ideas, brainstorming) - sth they can build on, commit
         - [ ] DND idea of learning (inventory - nouns, adjs, etc. --- together/solo)
         - [ ] Create your own learning vocab list! (getting the vocab - kdrama, sub.)
         - [ ] Creating content with your Vocab
         - [ ] Intercativity with button, ephimwral personalize (guide, line translate, words during reading)
         - [ ] clustering words relations (similar words opts!)

### Done ✓

- [x] Create my first TODO.md  
