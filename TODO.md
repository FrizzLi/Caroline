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
  - [ ] Present on website - Show the graphs of right/wrongs for each person
  - [ ] FIX: Korean.py, first interaction is slow...
  - [ ] Maybe "thinking" emoji shouldnt come so late
  - [ ] Speech recognition (not only google's voice.. [because of phrases later!])
  - [ ] FIX: bug -- 48 words on lvl 2, why
  - [ ] FIX: The bot is not leaving for some reason
  - [ ] FIX: (maybe its ok now) self.np_msg.delete() --> discord.errors.NotFound: 404 Not Found (error code: 10008): Unknown Message
  - [ ] UPD: Format the output more nicely after session is done
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
  - [ ] FIX: /Improve audio downloading (current script is published in memo bookmark)
  - [ ] ???: Commit - [UPD] move connect/disconnect from music.py into shared utils https://github.com/freezpmark/personal-discord-bot/commit/e69a415341308cc6004442a331903421b5692099#diff-35606ac1b506923433a05188f57dfd000f0b13a62abc984a0ea8f41ab0a14fbf
  - [ ] Discarded:
    - [ ] IMP: Visualize: streak play, daily q, graph of practice intensity like on github
    - [ ] IMP: Writing vocab f.: vocab_writing [REM] vocab writing function
    - [ ] IMP: Audio for reading too (?) Lvl 3 already done
    - [ ] Images for words (text -> img -> text -> same text? (supervised))
  
    - [ ] LLM/ChatGPT Problems:
      - [ ] Knowledge graph? Similarity between Korean words (spaced in dash app) [2 syllables same, same base english word]
      - [ ] IMP: Make questions about listening, also with choices.. nn type!
      - [ ] IMP: Answering questions - Q&A for Grammar Book + TTMIK
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
