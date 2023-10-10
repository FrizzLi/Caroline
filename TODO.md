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
  - [ ] IMP: Auto-repeat every 5 sec (check all audio get max length) + stop sound if buttoned
  - [ ] IMP: Auto connect + Auto disconnect from voice when interacting with interface
  - [ ] IMP: When to go for new words or stick with review? - automatically calculate, 
  - [ ] IMP: New words session without the words i encountered?
  - [ ] IMP: Implement Grammar patterns
  - [ ] IMP: Elastic search instead of gsheet? --> Publish
  - [ ] IMP: Add translations for reading/listening
  - [ ] IMP: Note - more meanings chaos (with numbers, without numbers[;;;])
  - [ ] UPD: Check percentage calculation
  - [ ] UPD: Rearranged columns in google sheets --> might need update for that
  - [ ] FIX: Disconnected from voice during session -> "Wait a bit, ..." [ Not connected to voice.]
  - [ ] FIX: Left voice -> bot left, and forgot about session in text channel (no guesses(?))

  - [ ] Discarded:
    - [ ] IMP: Visualize: streak play, daily q, graph of practice intensity like on github
    - [ ] IMP: Writing vocab f.: vocab_writing [REM] vocab writing function
    - [ ] IMP: Audio for reading too (?) Lvl 3 already done
  
    - [ ] LLM/ChatGPT Problems:
      - [ ] IMP: Sentences creation for listening / reading idea
      - [ ] IMP: Example sentences do not distinguish synonyms issue
      - [ ] IMP: Add more pics (automate without checking them)
      - [ ] IMP: Base form detection for Reading/Listening (vocab building)
      - [ ] UPD: Gspread: Phrases/Two words - split, find words, if both exist, create () with 를/을 ...
      - [ ] IMP: Similarity between words in vocab session (meanings/spelling/antonyms)
      - [ ] IMP: Listening, Reading: Sentence Click for exploration -> grammar, vocab, translation
      - [ ] IMP: Create questions for reading/listening
      - [ ] Create dynamic adaptable content... sth they can build on, commit
         - [ ] D&D idea of learning (inventory - nouns, adjs, etc. --- together/solo)
         - [ ] Create your own learning vocab list! (getting the vocab - kdrama, sub.)
         - [ ] Creating content with your Vocab
         - [ ] Clustering words relations (similar words opts!)
         - [ ] Well known story concept .. harry potter... take ur favo char... Be with it

### Done ✓

- [x] Create my first TODO.md  
