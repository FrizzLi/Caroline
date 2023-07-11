import json
import os
import pickle
import random
from collections import defaultdict
from datetime import datetime
from glob import glob
from pathlib import Path
from statistics import fmean

import discord
import numpy as np
import pandas as pd
import pytz
from discord import app_commands
from discord.ext import commands
from gspread.exceptions import WorksheetNotFound

import utils
from cogs.korean.session_views import SessionListenView, SessionVocabView


class Language(commands.Cog):
    def __init__(self, bot):
        self.vocab_audio_paths = self._get_vocab_audio_paths()
        self.vocab_df = self._get_vocab_table()
        self.bot = bot
        self.ffmpeg_path = (
            "C:/ffmpeg/ffmpeg.exe" if os.name == "nt" else "/usr/bin/ffmpeg"
        )
        self.timezone = ""

    personalization = True  # NotImplemented
    show_eng_word = 1  # works for writing exercise

    def _get_vocab_table(self):
        """Gets the whole vocabulary table dataframed from google spreadsheet.

        Returns:
            pandas.core.frame.DataFrame: worksheet dataframe table
        """

        _, ws_dfs = utils.get_worksheets("Korea - Vocabulary", ("Level 1-2 (modified)",))

        # ignore rows with no Lesson cell filled (duplicates)
        vocab_df = ws_dfs[0]
        vocab_df["Lesson"].replace("", np.nan, inplace=True)
        vocab_df.dropna(subset=["Lesson"], inplace=True)

        return vocab_df

    def _get_vocab_audio_paths(self):
        """Gets vocab's local audio paths of all levels.

        Not all words have audio file, it will load only the ones that are
        present in vocabulary_audio directory that is in each of the lessons.
        Just so we dont have to read through all the lessons every time this
        module is loaded, the audio paths are stored in pickle file. (cached)
        Audio files are located in data/level_x/lesson_x/vocabulary_audio dir.

        Returns:
            Dict[str, str]: words and their audio paths (word being the key)
        """

        src_dir = Path(__file__).parents[0]
        pickle_path = f"{src_dir}/data/vocab_audio_path.pickle"
        if os.path.isfile(pickle_path):
            with open(pickle_path, "rb") as handle:
                audio_paths_labelled = pickle.loads(handle.read())
        else:
            audio_paths = glob(f"{src_dir}/data/*/*/vocabulary_audio/*")
            audio_paths_labelled = {}
            for audio_path in audio_paths:
                word = Path(audio_path).stem
                audio_paths_labelled[word] = audio_path

            with open(pickle_path, "wb") as file:
                pickle.dump(audio_paths_labelled, file)

        return audio_paths_labelled

    def get_session_number(self, ws_log, session_column):
        """Gets ordinal number of lesson or review of session. Begins with 1.

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_column (int): column index used to retrieve session number

        Returns:
            int: ordinal session number
        """

        session_numbers = ws_log.col_values(session_column)
        if len(session_numbers) > 1:
            session_number = int(session_numbers[-1]) + 1
        else:
            session_number = 1

        return session_number

    def get_score_distribution(self, amount=10, reducer=0.8):
        """Gets score distribution for vocabulary picking.

        Args:
            amount (int, optional): amount of values. Defaults to 10.
            reducer (float, optional): reducing coefficient. Defaults to 0.8.

        Returns:
            List[float]: distribution values
        """

        score = 1
        distribution_vals = []
        for _ in range(amount):
            distribution_vals.append(score)
            score = round(score * reducer, 3)

        return distribution_vals

    def get_time_penalty_data(self, row_date, now_date, coefficient = 0.005):
        """Gets time score penalty and emoji visualization for worksheet.

        Args:
            row_date (str): row's (word's) guess date
            now_date (datetime.datetime): current date
            coefficient (float, optional): Penalty coefficient.
                Defaults to 0.005.

        Returns:
            Tuple[int, List[str]]: score penalty, time marks
        """

        # score penalty
        row_date = datetime.strptime(row_date, "%Y-%m-%d %H:%M:%S")
        days_diff = (now_date - row_date).days
        score_penalty = days_diff * coefficient

        # emoji visualizations
        months, days = divmod(days_diff, 30)
        weeks, days = divmod(days, 7)
        time_marks = ["🌙"] * months + ["📅"] * weeks + ["🌞"] * days

        return score_penalty, time_marks

    def get_score(self, ws_log):
        """Gets score of words and visualizing list of rows for worksheet.

        Scoring system takes into account: 
         - first guesses in a session, by each latter session, the importance
           of score is being reduced by distribution values
         - time of the last guess of a certain word

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs

        Returns:
            Tuple[List[str, int, str, str]]: (
                word, score, (knowledge_marks, time_marks)
            )
        """

        score_table = {"✅": 1, "⏭️": 2, "❌": 4}
        distr_vals = self.get_score_distribution()
        considering_amount = len(distr_vals)
        table_rows = []

        df = pd.DataFrame(ws_log.get_all_records())
        df = df.sort_values(["Word", "Date"])
        previous_row = df.iloc[0]
        knowledge_marks = [previous_row.Knowledge]
        knowledge_scores = [score_table[previous_row.Knowledge]]
        df.drop(0)

        for row in df.itertuples():
            if previous_row.Word != row.Word:
                knowledge_scores.reverse()
                knowledge_scores = knowledge_scores[:considering_amount]
                knowledge_scores_mean = fmean(knowledge_scores)
                extension_amount = abs(len(knowledge_scores) - len(distr_vals))
                knowledge_scores += [knowledge_scores_mean] * extension_amount
                distr_score = np.array(knowledge_scores) * np.array(distr_vals)

                time_score_penalty, time_marks = self.get_time_penalty_data(
                    previous_row.Date,
                    datetime.now()
                )

                knowledge_marks.reverse()
                knowledge_marks = knowledge_marks[:considering_amount]

                final_score = sum(distr_score) + time_score_penalty

                table_rows.append(
                    [
                        previous_row.Word,
                        final_score,
                        "".join(knowledge_marks),
                        "".join(time_marks)
                    ]
                )

                knowledge_marks = [row.Knowledge]
                knowledge_scores = [score_table[row.Knowledge]]

            # take into account only the first guesses in one session
            elif previous_row.Session_number != row.Session_number:
                knowledge_marks.append(row.Knowledge)
                knowledge_scores.append(score_table[row.Knowledge])

            previous_row = row

        table_rows = sorted(table_rows, key=lambda x:x[1], reverse=True)

        return table_rows

    def get_random_words(self, words, consider_amount=150, pick_amount=50):
        """Gets randomly chosen words for session.

        Creates linear probability distribution and uses it to pick words
        randomly from the most unknown ones to the more known ones.

        Args:
            words (List[str]): words that were guessed
            consider_amount (int, optional): Amount of words to consider into
                random picking. Defaults to 150.
            pick_amount (int, optional): Amount of words to pick.
                Defaults to 50.

        Returns:
            numpy.ndarray: (list of) picked words
        """

        consider_amount = len(words) if len(words) < consider_amount else consider_amount
        size = consider_amount if consider_amount < pick_amount else pick_amount
        weights = np.linspace(1, 0, consider_amount)
        weights /= weights.sum()
        picked_words = np.random.choice(words[:consider_amount], p=weights, size=size, replace=False)

        return picked_words

    def get_ending_session_stats(self, stats):
        """Gets stats that will be displayed when the session ends.

        Contains top 5 wrongly guessed words and overall percentages for each
        mark.

        Args:
            stats (List[str, str, str, int]): time, word, mark, session number

        Returns:
            str: stats
        """

        # get marks count and scoring per word
        marks_count = {"✅": 0, "⏭️": 0, "❌": 0}
        scoring = {"✅": 0, "⏭️": 1, "❌": 2}
        word_scores = {}
        for _, word, mark, _ in stats:
            if word not in word_scores:
                word_scores[word] = scoring[mark]
                marks_count[mark] += 1
            else:
                word_scores[word] += scoring[mark]

        # get hardest words
        word_scores_sorted = sorted(word_scores.items(), key=lambda x:x[1], reverse=True)
        hardest_words = []
        for word, _ in word_scores_sorted[:5]:
            if word:
                hardest_words.append(word)
        hardest_words_string = ", ".join(hardest_words)

        # get mark percentages
        total = sum(marks_count.values())
        for mark in marks_count:
            marks_count[mark] = round(marks_count[mark] * 100 / total, 1)

        percentages_summary = (
            f"{marks_count['✅']}%,"
            f"   {marks_count['⏭️']}%,"
            f"   {marks_count['❌']}%"
        )

        stats = f"Total guesses: {total}\nHardest words: {hardest_words_string}\n{percentages_summary}"

        return stats

    def get_lesson_vocab(self, level_lesson_number):
        """Gets vocabulary for a given lesson.

        Hundred decimals represent level of the vocabulary. 
        The other two numbers range from 1 to 30 that represent a lesson.

        Args:
            level_lesson_number (int): lesson number

        Returns:
            List[Tuple[str, str, Tuple[str, str]]]: [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
        """

        vocab = []
        for row in self.vocab_df.itertuples():
            if not row.Lesson:
                continue
            if row.Lesson > level_lesson_number:
                break
            if row.Lesson == level_lesson_number:
                vocab.append((row.Book_English, row.Korean, (row.Example_EN, row.Example_KR)))

        random.shuffle(vocab)

        return vocab

    def get_review_vocab(self, ws_log, level_number, user_name):
        """Gets vocabulary review of all guessed words for a given level.

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            level_number (int): level number
            user_name (str): user name (used for worksheet name)

        Returns:
            List[Tuple[str, str, Tuple[str, str]]]: [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
        """

        score_data = self.get_score(ws_log)

        # create worksheet of scores
        ws_scores_list, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{user_name}-score-{level_number}",),
            create=True,
            size=(10_000, 4)
        )
        ws_scores = ws_scores_list[0]
        ws_scores.clear()
        ws_scores.append_rows(score_data)

        guessed_words = [row[0] for row in score_data]
        picked_words = self.get_random_words(guessed_words)

        # getting english data from worksheet
        korean_word_data = pd.Series(
            zip(
                self.vocab_df.Book_English,
                self.vocab_df.Example_EN,
                self.vocab_df.Example_KR
            ),
            index=self.vocab_df.Korean
            ).to_dict()

        # creating vocab list with all of the content
        vocab = []
        for kor in picked_words:
            eng = korean_word_data[kor][0]
            exs = korean_word_data[kor][1:]
            vocab.append((eng, kor, exs))

        return vocab

    def get_listening_files(self, level_lesson_number):
        """Gets listening contents text and path to audio files.

        Args:
            level_lesson_number (int): lesson number

        Returns:
            Tuple[List[str]]: (audio text, audio paths)
        """

        src_dir = Path(__file__).parents[0]
        level = level_lesson_number // 100
        lesson = level_lesson_number % 100
        lesson_path = f"{src_dir}/data/level_{level}/lesson_{lesson}"
        audio_path = Path(f"{lesson_path}/listening_audio")
        text_path = Path(f"{lesson_path}/listening_text.txt")
        try:
            with open(text_path, encoding="utf-8") as f:
                text = f.read()
            audio_texts = text.split("\n\n")
            audio_paths = sorted(glob(f"{audio_path}/listening_audio/*"))
            # sorted it because linux system reverses it
        except Exception as err:
            print(err)
            exit()

        return audio_texts, audio_paths

    async def get_voice(self, interaction):
        """Gets or connects to the voice channel.
        
        Gets the voice channel in which the bot is currently in. If it is not
        connected, it connects to channel in which the user is currently in.

        Returns:
            discord.voice_client.VoiceClient: voice channel
        """

        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            await interaction.followup.send("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        return voice

    async def get_level_lesson(self, interaction, level_lesson_number):
        """Gets level and lesson numbers with validation checks.

        There are 3 types of level_lesson_number:
         - One ("1") finds the next user's unknown lesson
         - Pure hundreds ("100", ..., "400") review session of one levels words
         - Hundreds up to 30 ("101", ..., "130") specific lesson number

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            level_lesson_number (int): level lesson number

        Raises:
            commands.CommandError: Wrong lesson number!

        Returns:
            Tuple[int, int]: (level_number, lesson_number)
        """

        # get next level_lesson_number
        if level_lesson_number == 1:
            df = self.vocab_df
            user_name = interaction.user.name
            ws_names = (
                f"{user_name}-score-1", 
                f"{user_name}-score-2",
                f"{user_name}-score-3",
                f"{user_name}-score-4"
            )
            try:
                _, scores_df_list = utils.get_worksheets("Korea - Users stats", ws_names)
            except WorksheetNotFound:
                level_lesson_number = 101

            for i, scores_df in enumerate(scores_df_list, 1):
                known_set = set(scores_df[df.columns[0]])
                level_set = set(df.loc[df["Lesson"] // 100 == i, "Korean"])
                unknown_set = level_set - known_set
                if unknown_set:
                    unknown_word_lessons = df.loc[df["Korean"].isin(unknown_set), "Lesson"]
                    level_lesson_number = int(sorted(unknown_word_lessons)[0])
                    break

            if level_lesson_number == 1:
                level_lesson_number += 100 + len(scores_df_list) * 100

        # get level and lesson number with validation check
        level_number = level_lesson_number // 100
        lesson_number = level_lesson_number % 100
        if not (0 < level_number < 5 and lesson_number < 31):
            await interaction.followup.send("Wrong lesson number!")
            raise commands.CommandError("Wrong lesson number!")

        return level_number, lesson_number

    async def run_vocab_session_loop(self, interaction, voice, ws_log, session_number, vocab):
        """Runs session loop for vocabulary words.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            voice (discord.voice_client.VoiceClient): voice client channel
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_number (int): session number
            vocab (List[Tuple[str, str, Tuple[str, str]]]): [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
        """

        i = 1
        max_spaces = 30  # using for discord bug with spoiled words
        unchecked = set(vocab)
        msg_str = f"{len(unchecked)} words remaining."
        stat_labels = {"easy": "✅", "medium": "⏭️", "hard": "❌"}
        view = SessionVocabView()
        stats = []

        msg = await interaction.channel.send(msg_str)
        while True:
            eng, kor, ex = vocab[-1]
            example = f"\n{ex[1]} = {ex[0]}" if ex[0] else ""
            kor_no_num = kor[:-1] if kor[-1].isdigit() else kor

            # handling word with audio
            if kor_no_num in self.vocab_audio_paths:
                msg_display = f"||{kor} = {eng:20}" + " " * (i % max_spaces) + f"{example}||"
                try:
                    voice.play(
                        discord.FFmpegPCMAudio(
                            self.vocab_audio_paths[kor_no_num],
                            executable=self.ffmpeg_path,
                        )
                    )
                except Exception as err:
                    print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")
            else:
                msg_display = f"{kor} = ||{eng:20}" + " " * (i % max_spaces) + f"{example}||"

            msg_str = f"{len(unchecked)} words remaining"
            content = f"{msg_str}\n{msg_display}"
            await msg.edit(content=content, view=view)

            # wait for interaction
            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )

            # button interactions
            button_id = interaction.data["custom_id"]
            if button_id == "repeat":
                continue

            word_to_move = vocab.pop()
            if button_id == "easy":
                vocab.insert(0, word_to_move)
                if word_to_move in unchecked:
                    unchecked.remove(word_to_move)
            elif button_id == "medium":
                vocab.insert(len(vocab) // 2, word_to_move)
            elif button_id == "hard":
                vocab.insert(- len(vocab) // 5, word_to_move)
            elif button_id == "end":
                stats_str = self.get_ending_session_stats(stats)
                content = f"{msg_str}\n{stats_str}"
                await msg.edit(content=content, view=view)
                ws_log.append_rows(stats)
                break

            i += 1
            time = datetime.now(pytz.timezone(self.timezone))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            stats.append(
                [
                    time_str,
                    word_to_move[1],
                    stat_labels[button_id],
                    session_number,
                ]
            )

    async def run_listening_session_loop(self, interaction, voice, audio_texts, audio_paths):
        # TODO LISTEN: Error when long time no use.. (listening)
        # TODO LISTEN: Pause for listening + 10s backwards
        i = 0
        count_n = len(audio_paths)

        counter_text = f"{i+1}. lesson out of {count_n}."
        msg = await interaction.followup.send(counter_text)
        view = SessionListenView()

        while True:
            if i >= count_n:
                i = 0
            try:
                voice.play(
                    discord.FFmpegPCMAudio(
                        audio_paths[i],
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            content = f"```{counter_text}\n{audio_texts[i]}```"

            try:
                await msg.edit(content=content, view=view)
            except discord.errors.HTTPException as err:
                # TODO LISTEN: err resolve, cannot delete or edit msg, workarounded (TODO.MD stuff)
                print(err)
                msg = await interaction.followup.send(content)
                await msg.edit(content=content, view=view)

            # wait for interaction
            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )

            # button interactions
            button_id = interaction.data["custom_id"]
            if button_id == "pauseplay":
                # TODO LISTEN: this doesn't work
                # need to add player, pause NN crucially atm
                button_id2 = None
                while button_id2 != "pauseplay":
                    interaction = await self.bot.wait_for(
                        "interaction",
                        check=lambda inter: "custom_id" in inter.data.keys()
                        and inter.user.name == interaction.user.name,
                    )
                    button_id2 = interaction.data["custom_id"]
            elif button_id == "next":
                i += 1
            elif button_id == "repeat":
                pass
            elif button_id == "end":
                content = f"```{counter_text}\nEnding listening session.```"
                try:
                    await msg.edit(content=content, view=view)
                except discord.errors.HTTPException as err:
                    print(str(err).encode("utf-8"))
                    break
                break

            counter_text = f"{i+1}. lesson out of {count_n}"

    # Button commands
    async def pause(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return
        elif vc.is_paused():
            return

        vc.pause()

    async def resume(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return
        elif not vc.is_paused():
            return

        vc.resume()

    @commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded, it initializes timezone.

        This could have been initialized in __init__ method, but to make it
        consistent with all cogs, on_ready is being used for config loading.
        Surveillance module needs to load it there."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]

    @app_commands.command(name="vl")
    async def vocab_listening(self, interaction, level_lesson_number: int):
        """Start listening vocabulary exercise."""

        await interaction.response.send_message(
            "...Setting up vocab session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Vocabulary")
        )

        level_number, lesson_number = await self.get_level_lesson(interaction, level_lesson_number)

        # get users stats worksheet
        columns = 4
        ws_logs, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{interaction.user.name}-{level_number}",),
            create=True,
            size=(10_000, columns)
        )
        ws_log = ws_logs[0]
        if not ws_log.get_values("A1"):
            ws_log.append_row(["Date", "Word", "Knowledge", "Session_number"])

        session_number = self.get_session_number(ws_log, columns)

        if lesson_number:
            vocab = self.get_lesson_vocab(level_lesson_number)
            await interaction.followup.send(f"Lesson {level_lesson_number}]")
        else:
            vocab = self.get_review_vocab(ws_log, level_number, interaction.user.name)
            await interaction.followup.send(f"Review session: {session_number}")

        await self.run_vocab_session_loop(interaction, voice, ws_log, session_number, vocab)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

    @app_commands.command(name="vw")
    async def vocab_writing(self, interaction):
        """Start vocab exercise."""

        # TODO WRITING: opt, remake (TODO.MD stuff)
        src_dir = Path(__file__).parents[0]
        level_path = Path(f"{src_dir}/data/{self.level}.json")
        await interaction.response.send_message('Exit by "EXIT"')
        await self.bot.change_presence(
            activity=discord.Game(name="Vocab typing")
        )

        with open(level_path, encoding="utf-8") as file:

            # set vocab
            level_vocab = json.load(file)
            lesson_vocab = list(level_vocab[self.lesson].items())
            random.shuffle(lesson_vocab)
            if not self.show_eng_word:
                lesson_vocab = [word[::-1] for word in lesson_vocab]

        # personalization
        if self.personalization:
            stats = defaultdict(list)

            name = interaction.user.name
            file_name = f"{name}-{self.level}-{self.lesson}.json"
            users_dir = Path(f"{src_dir}/data/users")
            Path(users_dir).mkdir(parents=True, exist_ok=True)
            file_score_path = Path(f"{users_dir}/{file_name}")
            if os.path.exists(file_score_path):
                with open(file_score_path, encoding="utf-8") as file:
                    json_content = json.load(file)
                    stats = defaultdict(list, json_content)

        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:  # slash commands?!
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        # session starts
        attempts = 0
        corrects = 0
        incorrect_words = set()
        while True:
            guessing, answer = lesson_vocab[0]
            await interaction.followup.send(guessing)
            response = await self.bot.wait_for(
                "message",
                check=lambda msg: msg.author == interaction.user
                and msg.channel == interaction.channel,
            )
            if response.content == "EXIT":
                break

            if response.content.lower() == answer.lower():
                await interaction.followup.send("Correct!")
                stats[answer].append(True)
                corrects += 1
                lesson_vocab.append(lesson_vocab.pop(0))
            else:
                await interaction.followup.send(f"Incorrect! It is {answer}")
                stats[answer].append(False)
                incorrect_words.add(guessing)
                new_index = len(lesson_vocab) // 5
                lesson_vocab.insert(new_index, lesson_vocab.pop(0))
            attempts += 1

            # play sound
            if answer in self.vocab_audio_paths:
                voice.play(
                    discord.FFmpegPCMAudio(
                        self.vocab_audio_paths[answer],
                        executable=self.ffmpeg_path,
                    )
                )

            if not all(stats[answer][-1:-3:-1]):
                continue_ = True

            # check if last two answers are correct in stats, if not, continue
            continue_ = False
            for word in stats.values():
                if not all(word[-1:-3:-1]):
                    continue_ = True

            if not continue_ and len(lesson_vocab) <= attempts:
                await interaction.followup.send(
                    f"You answered all words correctly twice in a row! \
                    (or once if you only guessed once). \
                    Incorrect words were: {incorrect_words}"
                )
                break

        # print and save stats
        accuracy = corrects / attempts * 100
        msg = f"{corrects} answers were right out of {attempts}! \
            ({accuracy:.2f}%)"
        await interaction.followup.send(msg)

        if self.personalization:
            with open(file_score_path, "w", encoding="utf-8") as file:
                json.dump(stats, file, sort_keys=True, ensure_ascii=False)
            await interaction.followup.send("Score has been saved.")

        await interaction.followup.send(f"Exiting {self.lesson} exercise..")

    @app_commands.command(name="l")
    async def listening(self, interaction, lesson_number: int):
        """Start listening exercise."""

        await interaction.response.send_message(
            "...Setting up listening session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Listening")
        )

        audio_texts, audio_paths = self.get_listening_files(lesson_number)

        await interaction.followup.send(f"Lesson {lesson_number}]")

        await self.run_listening_session_loop(interaction, voice, audio_texts, audio_paths)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

    @app_commands.command(name="r")
    async def reading(self, interaction, lesson_number: int):
        """Start listening exercise."""

        await interaction.response.send_message(
            "...Setting up listening session..."
        )

        # TODO READING: NOT Have to be connected to turn on reading lesson
        # load audio files
        src_dir = Path(__file__).parents[0]
        level = lesson_number // 100
        lesson = lesson_number % 100
        data_path = f"{src_dir}/data/level_{level}/lesson_{lesson}"
        audio_paths = glob(f"{data_path}/*")
        name_to_path_dict = {}

        for audio_path in audio_paths:
            word = Path(audio_path).stem
            name_to_path_dict[word] = audio_path

        if "reading_text" in name_to_path_dict:
            with open(name_to_path_dict["reading_text"], encoding="utf-8") as f:
                reading_text = f.read()
        else:
            return

        await interaction.followup.send(f"[Lesson {lesson_number}]")
        # view = SessionListenView()
        await interaction.followup.send(f"```{reading_text}```")

async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Language(bot), guilds=[discord.Object(id=os.environ["SERVER_ID"])]
    )
