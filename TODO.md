# TODO List

### In Progress

- [ ]

### Todo

- [ ] Opt: Pylint (errs, with cmd! -> 9.0 score above), Async, Logs; Document
- [ ] Discord bots -> voice chat leaving - dont take other bots into account
- [ ] ai_algo.py: Tests (_apply_actions test (rmv), docs)
- [ ] surveillance.py: Voice stats graphs, Process old logs
- [ ] music.py:
  - [ ] IMP: Dont lose queue upon leaving, async attach (for voice continent change, 10sec?)
  - [ ] IMP: Most played dropdown choose at all times
  - [ ] IMP: Create radio (automatically picks songs)
  - [ ] IMP: Like button (to remember URL for next time)
  - [ ] FIX: When the queue is fully played, it stops listening to requests
  - [ ] FIX: when the bot leaves the voice, refresh button still works..
  - [ ] UPD: Deep opt., polishing with other bots as insp., apply logs instead of prints (+wrappers?)

- [ ] korean.py
  - [ ] IMP: Clarify notes for certain session types with bold font
  - [ ] IMP: Remind to leave the voice chat when its over
  - [ ] IMP: Inform that you can uncover the expressions to see the answer
  - [ ] IMP: Notes command? /help only for the session, too much text might drive users away
  - [ ] IMP: Resolve pressing the same option in dropdown
  - [ ] FIX: Disconnected from voice during session -> Wait a bit, repeat the unplayed audio!!! [ Not connected to voice.]
  - [ ] UPD: Rearranged columns in google sheets --> might need update for that
  - [ ] IMP: Auto-repeat every 5 sec (check all audio get max length) + stop sound if buttoned
  - [ ] FIX: Left voice -> bot left, and forgot about session in text channel (no guesses(?))
  - [ ] IMP: Auto connect + Auto disconnect from voice when interacting with interface
  - [ ] IMP: When to go for new words or stick with review? - automatically calculate, 
  - [ ] IMP: New words session without the words i encountered?
  - [ ] UPD: Check percentage calculation
  - [ ] IMP: Implement Grammar patterns

  - [ ] Publishing it: Make it in your server (networking) [UPON WEBSITE BUILDING], Elastic search for gsheet data for all users?
  - [ ] Example sentences do not distinguish synonyms issue
  - [ ] Brainstorm: Together chat with listening tracks / texts... Who don't know what.... Score, explain... Sessions 
  - [ ] IMP: Add translations for reading/listening

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
         - [ ] Well known story concept .. harry potter,,, take ur favo char... Be with it

### Done ✓

- [x] Create my first TODO.md  
