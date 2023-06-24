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
from discord.utils import get

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
        if session_numbers:
            last_session_number = max(map(int, session_numbers[1:]))
            session_number = last_session_number + 1
        else:
            session_number = 1

        return session_number

    def get_score_distribution(self):
        """Gets score distribution for vocabulary picking.

        Returns:
            Dict[int, float]: indexed distribution values
        """

        amount = 10
        score = 1
        reducer = 0.8
        distribution_vals = []
        for i in range(amount):
            distribution_vals.append(score)
            score *= reducer

        scores = {i: round(j, 3) for i, j in enumerate(distribution_vals)}

        return scores

    def get_score_of_words(self, ws_log, scores):
        df = pd.DataFrame(ws_log.get_all_records())
        df.sort_values(["Word", "Date"], ascending=[True, False], inplace=True)

        datetime_now = datetime.now()
        score_list = []
        knowledge = []
        knowledge_marks = []  # redundant,, but will opt later
        word_scores = {}
        new_word = ""
        debug_compute = []
        new_word_time_penalty_total = 0
        new_word_score_total = 0
        new_word_counter = 0
        for row in df.itertuples():
            if new_word_counter >= 10 and new_word == row.Word:
                continue  # needs opt -> use pd
            if new_word == row.Word:
                new_word_counter += 1
            else:
                if new_word:
                    mean = fmean(knowledge)
                    empty_fill_sum = 0
                    for i in range(new_word_counter+1, 10):
                        empty_fill = mean * scores[i]
                        empty_fill_sum += empty_fill
                        debug_compute.append(empty_fill)
                        # print(f"i({i}){new_word}: empty_fill")

                    # empty_fill = fmean(knowledge) * (10-new_word_counter)
                    word_score = new_word_score_total + empty_fill_sum
                    # word_score_time_penalized = word_score + new_word_time_penalty_total
                    word_scores[new_word] = word_score
                    score_list.append(
                        [
                            new_word,
                            word_score,
                            "".join(knowledge_marks),
                            ", ".join(str(round(x,2)) for x in debug_compute)
                        ]
                    )
                    # score_list2.append(
                    #     [
                    #         new_word,
                    #         word_score_time_penalized,
                    #         "".join(knowledge_marks),
                    #         ", ".join(str(round(x,2)) for x in debug_compute)
                    #     ]
                    # )
                    new_word_score_total = 0
                    new_word_counter = 0
                    new_word_time_penalty_total = 0

                    debug_compute = []
                    knowledge = []
                    knowledge_marks = []
                new_word = row.Word

            if row.Knowledge == "✅":
                knowledge_multiplier = 1
            elif row.Knowledge == "⏭️":
                knowledge_multiplier = 2
            elif row.Knowledge == "❌":
                knowledge_multiplier = 4
            # new_word_score.append(f"{knowledge_multiplier}*{scores[new_word_counter]}")

            new_word_score = knowledge_multiplier * scores[new_word_counter]
            debug_compute.append(new_word_score)
            new_word_score_total += new_word_score
            knowledge.append(knowledge_multiplier)
            knowledge_marks.append(row.Knowledge)

            row_datetime = datetime.strptime(row.Date, "%Y-%m-%d %H:%M:%S")
            now_datetime = datetime_now
            days_diff = (now_datetime - row_datetime).days
            new_word_time_penalty_total += days_diff * 0.001
        
        score_list = sorted(score_list, key=lambda x:x[1], reverse=True)

        return score_list, word_scores


    def compute_percentages(self, easy_c, medium_c, hard_c):
        # TODO: this might not be needed, so no docs yet (TODO.MD stuff)
        total_c = easy_c + medium_c + hard_c
        return (
            round(easy_c * 100 / total_c, 1),
            round(medium_c * 100 / total_c, 1),
            round(hard_c * 100 / total_c, 1),
        )

    def get_lesson_vocab(self, lesson_number):
        """Gets vocabulary for a given lesson.

        Hundred decimals represent level of the vocabulary. The other two
        numbers range from 1 to 30 that represent a lesson.

        Args:
            lesson_number (int): lesson number

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
            if row.Lesson > lesson_number:
                break
            if row.Lesson == lesson_number:
                vocab.append((row.Book_English, row.Korean, (row.Example_EN, row.Example_KR)))

        random.shuffle(vocab)

        return vocab

    def get_review_vocab(self, ws_log, level_number, user_name):
        """Gets vocabulary review of all encountered word for a given level.

        LOREM IPSUM

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

        score_vals = self.get_score_distribution()
        score_list, word_scores = self.get_score_of_words(ws_log, score_vals)

        ws_scores, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{user_name}-score-{level_number}",),
            create=True,
            size=(10_000, 4)
        )
        ws_score = ws_scores[0]
        ws_score.clear()
        ws_score.append_rows(score_list)

        # TIMED SCORE
        # score_g_ws2 = get_worksheet("Korea - Users stats", f"score_monitor-{level_number}-timed")
        # score_g_ws2.clear()
        # score_list2 = []
        #
        # score_list2 = sorted(score_list2, key=lambda x:x[1], reverse=True)
        # score_g_ws2.append_rows(score_list2)

        # Arranging words, score, marks
        sorted_word_score = sorted(word_scores.items(), key=lambda item: item[1], reverse=True)
        number_of_words = len(score_list) if len(score_list) < 100 else 100
        sorted_words = [sorted_word_score[i][0] for i in range(number_of_words)]

        # Use probability distribution to pick the most unknown words to known words
        # Create a list of probabilities that decrease linearly from left to right
        size = number_of_words if number_of_words < 50 else 50
        weights = np.linspace(1, 0, number_of_words)
        weights /= weights.sum()
        nl = np.random.choice(sorted_words, p=weights, size=size, replace=False)

        # TIMED SCORE
        # nl2 = []
        # size = 10
        # for i in range(0, len(sorted_word_score), size):
        #     if i > size * 4:
        #         # nl += sorted_word_score[i::]
        #         break
        #     subset = sorted_word_score[i:i+size]
        #     random.shuffle(subset)
        #     nl2 += subset

        nl = list(nl)[::-1]
        # TIMED SCORE
        # nl2 = nl2[::-1]

        kor_to_eng = pd.Series(
            self.vocab_df.Book_English.values, index=self.vocab_df.Korean
        )[::-1].to_dict()

        kor_to_eng_exs = pd.Series(
            zip(self.vocab_df.Example_EN, self.vocab_df.Example_KR), 
                index=self.vocab_df.Korean
            )[::-1].to_dict()

        vocab = []
        for kor in nl:
            eng = kor_to_eng[kor]
            exs = kor_to_eng_exs[kor]
            vocab.append((eng, kor, exs))

        random.shuffle(vocab)

        return vocab

    def get_listening_files(self, lesson_number):
        """Gets text content and path to audio files.

        Args:
            lesson_number (int): lesson number

        Returns:
            Tuple[List[str]]: (audio text, audio paths)
        """

        src_dir = Path(__file__).parents[0]
        level = lesson_number // 100
        lesson = lesson_number % 100
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

        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            await interaction.followup.send("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = get(self.bot.voice_clients, guild=interaction.guild)

        return voice

    async def run_vocab_session_loop(self, interaction, voice, ws_log, vocab, session_number):
        """Runs session loop of vocabulary words.

        _extended_summary_

        Args:
            interaction (discord.interactions.Interaction): _description_
            voice (discord.voice_client.VoiceClient): _description_
            ws_log (gspread.worksheet.Worksheet): _description_
            vocab (List[Tuple[str, str, Tuple[str, str]]]): _description_
            session_number (int): _description_
        """

        # TODO: first priority, not that hard (TODO.MD stuff)
        # ? percentages, know when to end (try all)
        # ? stats_list append row by row
        i = 1
        count_n = len(vocab)
        counter = f"{i}. word out of {count_n}."
        msg = await interaction.followup.send(counter)

        stats_label = {"easy": "✅", "medium": "⏭️", "hard": "❌"}
        stats_list = []
        easy_c = easy_p = 0
        medium_c = medium_p = 0
        hard_c = hard_p = 0
        stats = ""
        view = SessionVocabView()
        # vocab = list of tuples of eng, kor, ex
        # ex = eng--kor

        while True:
            eng, kor, ex = vocab[-1]    # pops a list!, ex is other
            example = f"\n{ex[1]} = {ex[0]}" if ex[0] else ""
            kor_no_num = kor[:-1] if kor[-1].isdigit() else kor

            # handling word that has no audio
            if kor_no_num in self.vocab_audio_paths:
                msg_display = f"||{kor} = {eng:20}" + " " * (i % 15) + f"{example}||"
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
                msg_display = f"{kor} = ||{eng:20}" + " " * (i % 15) + f"{example}||"

            content = f"{counter}\n{msg_display}\n{stats}"
            try:
                await msg.edit(content=content, view=view)
            except discord.errors.HTTPException as err:
                # TODO: err resolve, cannot delete or edit msg, workarounded
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
            if button_id == "easy":
                word_to_move = vocab.pop()

                vocab.insert(0, word_to_move)
                easy_c += 1


                i += 1
                easy_p, medium_p, hard_p = self.compute_percentages(
                    easy_c, medium_c, hard_c
                )
            elif button_id == "medium":
                word_to_move = vocab.pop()

                vocab.insert(len(vocab) // 2, word_to_move)
                medium_c += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = self.compute_percentages(
                    easy_c, medium_c, hard_c
                )
            elif button_id == "hard":
                word_to_move = vocab.pop()

                new_index = len(vocab) // 5
                vocab.insert(-new_index, word_to_move)
                hard_c += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = self.compute_percentages(
                    easy_c, medium_c, hard_c
                )


            elif button_id == "end":
                msg_display = "Ending listening session."

                # ending message
                content = f"{counter}\n{msg_display}\n{stats}"
                try:
                    await msg.edit(content=content, view=view)
                except discord.errors.HTTPException as err:
                    print(err)
                    ws_log.append_rows(stats_list)
                    break
                ws_log.append_rows(stats_list)
                break
            elif button_id == "repeat":
                continue

            stats = f"{easy_p}%,   {medium_p}%,   {hard_p}%"
            counter = f"{i}. word out of {count_n}"

            time = datetime.now(pytz.timezone(self.timezone))
            time = time.strftime("%Y-%m-%d %H:%M:%S")
            stats_list.append(
                [
                    time,
                    word_to_move[1],
                    stats_label[button_id],
                    session_number,
                ]
            )

    async def run_listening_session_loop(self, interaction, voice, audio_texts, audio_paths):
        # TODO: (TODO.MD stuff)
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
                # TODO: err resolve, cannot delete or edit msg, workarounded (TODO.MD stuff)
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
                # TODO: this doesn't work
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
    async def vocab_listening(self, interaction, lesson_number: int):
        """Start listening vocabulary exercise."""

        await interaction.response.send_message(
            "...Setting up vocab session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Vocabulary")
        )

        columns = 4

        level_number = lesson_number // 100
        review_session = False if lesson_number % 100 else True
        ws_logs, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{interaction.user.name}-{level_number}",),
            create=True,
            size=(10_000, columns)
        )
        ws_log = ws_logs[0]
        if not ws_log.get_values("A1"):
            ws_log.append_row(["Date", "Word", "Knowledge", "Session number"])

        session_number = self.get_session_number(ws_log, columns)

        if review_session:
            vocab = self.get_review_vocab(ws_log, level_number, interaction.user.name)
            await interaction.followup.send(f"Review session: {session_number}")
        else:
            vocab = self.get_lesson_vocab(lesson_number)
            await interaction.followup.send(f"Lesson {lesson_number}]")

        await self.run_vocab_session_loop(interaction, voice, ws_log, vocab, session_number)

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

        # TODO: opt, remake (TODO.MD stuff)
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

        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:  # slash commands?!
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )

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

# TODO: Look at TODOs, prioritize and implement
