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
import gspread
import numpy as np
import pandas as pd
import pytz
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from cogs.korean.session_views import SessionListenView, SessionVocabView
from cogs.korean.vocab_audio_search import dl_vocab


class Language(commands.Cog):
    def __init__(self, bot):
        self.vocab_audio_paths = self.get_vocab_audio_paths()
        self.vocab_df = self.get_vocab_table()
        self.bot = bot
        self.korean_config = self.load_korean_config()
        self.ffmpeg_path = (
            "C:/ffmpeg/ffmpeg.exe" if os.name == "nt" else "/usr/bin/ffmpeg"
        )
        self.timezone = ""

    # These parameters doesn't need to be in config, they're not so usable
    personalization = True  # NotImplemented  # !
    show_eng_word = 1  # works for writing exercise  # !

    def get_vocab_table(self):
        """Gets the whole vocabulary table dataframed from google spreadsheet.

        Returns:
            pandas.core.frame.DataFrame: worksheet dataframe table
        """

        _, ws_dfs = utils.get_worksheets("Korea - Vocabulary", ("Level 1-2 (modified)",))

        # ignore rows with no Lesson cell filled (duplicates)
        df = ws_dfs[0]
        df["Lesson"].replace("", np.nan, inplace=True)
        df.dropna(subset=["Lesson"], inplace=True)

        return df

    def get_vocab_paths(self):
        src_dir = Path(__file__).parents[0]
        pickle_path = f"{src_dir}/data/vocab_audio_path.pickle"
        if os.path.isfile(pickle_path):
            with open(pickle_path, "rb") as handle:
                audio_paths_labelled = pickle.loads(handle.read())
        else:
            print("korean: Creating pickle file for vocab audio paths...", end=" ")
            audio_paths = glob(f"{src_dir}/data/*/*/vocabulary_audio/*")
            audio_paths_labelled = {}
            for audio_path in audio_paths:
                word = Path(audio_path).stem
                audio_paths_labelled[word] = audio_path

            with open(pickle_path, "wb") as file:
                pickle.dump(audio_paths_labelled, file)
            print("Done!")
        
        return audio_paths_labelled

    def load_korean_config(self):
        src_dir = Path(__file__).parents[0]
        config_path = Path(f"{src_dir}/config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as file:
                config = json.load(file)
        else:
            config = {"level": 1, "lesson": 1, "custom": "default"}
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(config, file)

        return config

    def save_config(self):
        src_dir = Path(__file__).parents[0]
        config_path = Path(f"{src_dir}/config.json")
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(self.korean_config, file)

    @property
    def level(self):
        return f'vocab_level_{self.korean_config["level"]}'

    @level.setter
    def level(self, number):
        self.korean_config["level"] = number
        self.save_config()

    @property
    def lesson(self):
        return f'lesson_{self.korean_config["lesson"]}'

    @lesson.setter
    def lesson(self, number):
        self.korean_config["lesson"] = number
        self.save_config()

    @property
    def custom(self):
        return f'custom_{self.korean_config["custom"]}'

    @custom.setter
    def custom(self, fname):
        self.korean_config["custom"] = fname
        self.save_config()

    @app_commands.command()
    async def zkorean_settings(self, interaction):
        """Shows level, lesson, custom settings."""

        embed = discord.Embed(
            title="Korean settings",
            description="Settings for choosing lessons",
            colour=discord.Colour.blue(),
        )
        for setting in self.korean_config:
            embed.add_field(name=setting, value=self.korean_config[setting])

        await interaction.response.send_message(embed=embed)

    # @app_commands.command()
    # async def zset_level(self, interaction, number: int):
    #     self.level = number
    #     msg = f"Level number was set to {number}."
    #     await interaction.response.send_message(msg)

    # @app_commands.command()
    # async def zset_lesson(self, interaction, number: int):
    #     self.lesson = number
    #     msg = f"Lesson number was set to {number}."
    #     await interaction.response.send_message(msg)

    # @app_commands.command()
    # async def zset_custom_filename(self, interaction, fname: str):
    #     self.custom = fname
    #     msg = f"Custom file name was set to {fname}."
    #     await interaction.response.send_message(msg)

    # @app_commands.command()
    # async def zadd_lesson(self, interaction):
    #     """Adds lesson into user's customized lesson file."""

    #     src_dir = Path(__file__).parents[0]
    #     data_path = Path(f"{src_dir}/data")
    #     data_user_path = Path(f"{data_path}/users/{interaction.user.name}")
    #     Path(data_user_path).mkdir(parents=True, exist_ok=True)
    #     custom_path = Path(f"{data_user_path}/{self.custom}.json")

    #     if os.path.exists(custom_path):
    #         with open(custom_path, encoding="utf-8") as file:
    #             custom_vocab = json.load(file)
    #     else:
    #         custom_vocab = {}

    #     level_path = Path(f"{data_path}/{self.level}.json")
    #     with open(level_path, encoding="utf-8") as file:
    #         level_vocab = json.load(file)

    #     custom_vocab = {**custom_vocab, **level_vocab[self.lesson]}
    #     with open(custom_path, "w", encoding="utf-8") as file:
    #         json.dump(custom_vocab, file, indent=4, ensure_ascii=False)

    #     msg = f"{self.lesson} from {self.level} was saved into {self.custom}."
    #     await interaction.response.send_message(msg)

    # @app_commands.command()
    # async def zcreate_vocab(
    #     self, interaction, lesson_only: int = 1, text_only: int = 1
    # ):
    #     """Creates audio and json files from the text files."""

    #     lesson = self.lesson if lesson_only else False
    #     msg = "Downloading and creating vocab..."
    #     await interaction.response.send_message(msg)
    #     dl_vocab(self.level, lesson, text_only)
    #     await interaction.followup.send("Vocab has been created!")

    # Listeners
    @commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded and inits timezone."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]

    @app_commands.command(name="zev")
    async def zexercise_vocab(self, interaction):
        """Start vocab exercise."""

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

        # TODO: [During polish] Get audio (what is this TODO?)
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

    @app_commands.command(name="zevl")
    async def zexercise_vocab_listening(self, interaction, lesson_number: int):
        """Start listening vocab exercise.

        In the case of customized lesson, audio files will be loaded only
        from level that is set in the settings. TODO!!! find that are in custom
        """

        await interaction.response.send_message(
            "...Setting up listening session..."
        )
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            await interaction.followup.send("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = get(self.bot.voice_clients, guild=interaction.guild)

        await self.bot.change_presence(
            activity=discord.Game(name="Vocab listening")
        )

        # get vocab words
        credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
        credentials_dict = json.loads(credentials_dict_str)
        g_credentials = gspread.service_account_from_dict(credentials_dict)

        gs_stats = g_credentials.open("Korea - Users stats")
        level_number = lesson_number // 100
        
        try:
            ws_stats = gs_stats.worksheet(f"{interaction.user.name}-{level_number}")
        except gspread.exceptions.WorksheetNotFound:
            ws_stats = gs_stats.add_worksheet(
                title=f"{interaction.user.name}-{level_number}", rows=10_000, cols=4
            )
        session_numbers = ws_stats.col_values(4)
        if session_numbers:
            last_session_number = max(map(int, session_numbers[1:]))
            current_session_number = last_session_number + 1
        else:
            current_session_number = 1

        
        vocab = []

        for row in self.vocab_df.itertuples():
            if not row.Lesson:
                continue
            if row.Lesson > lesson_number:
                break
            if row.Lesson == lesson_number:
                vocab.append((row.Book_English, row.Korean, (row.Example_EN, row.Example_KR)))

        random.shuffle(vocab)

        # prepping msgs for the loop session
        i = 1
        count_n = len(vocab)

        await interaction.followup.send(f"[Lesson {lesson_number}]")
        counter = f"{i}. word out of {count_n}."
        msg = await interaction.followup.send(counter)

        def compute_percentages(easy, medium, hard):
            total = easy + medium + hard
            return (
                round(easy * 100 / total, 1),
                round(medium * 100 / total, 1),
                round(hard * 100 / total, 1),
            )

        stats_label = {"easy": "✅", "medium": "⏭️", "hard": "❌"}
        stats_list = []
        easy = easy_p = 0
        medium = medium_p = 0
        hard = hard_p = 0
        stats = ""
        view = SessionVocabView()

        while True:
            eng, kor, ex = vocab[-1]
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
                easy += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )
            elif button_id == "medium":
                word_to_move = vocab.pop()

                vocab.insert(len(vocab) // 2, word_to_move)
                medium += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )
            elif button_id == "hard":
                word_to_move = vocab.pop()

                new_index = len(vocab) // 5
                vocab.insert(-new_index, word_to_move)
                hard += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )

            elif button_id == "end":
                msg_display = "Ending listening session."

                # ending message
                content = f"{counter}\n{msg_display}\n{stats}"
                try:
                    await msg.edit(content=content, view=view)
                except discord.errors.HTTPException as err:
                    print(err)
                    ws_stats.append_rows(stats_list)
                    break
                ws_stats.append_rows(stats_list)
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
                    current_session_number,
                ]
            )

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )


    @app_commands.command(name="zel")
    async def zexercise_listening(self, interaction, lesson_number: int = 102):
        """Start listening vocab exercise.

        In the case of customized lesson, audio files will be loaded only
        from level that is set in the settings. TODO!!! find that are in custom
        """

        await interaction.response.send_message(
            "...Setting up listening session..."
        )
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )

        await self.bot.change_presence(
            activity=discord.Game(name="Listening exercise")
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

        if (
            "listening_audio" in name_to_path_dict
            and "listening_text" in name_to_path_dict
        ):
            with open(name_to_path_dict["listening_text"], encoding="utf-8") as f:
                listening_text = f.read()
                listening_text_tracks = listening_text.split("\n\n")
            audio_paths2 = sorted(glob(f"{data_path}/listening_audio/*"))  # add sorted cuz linux reversed it

            name_to_audio_path_dict = {}
            for audio_path2 in audio_paths2:
                word = Path(audio_path2).stem
                name_to_audio_path_dict[word] = audio_path2
        else:
            return

        i = 1
        count_n = len(name_to_audio_path_dict)

        queue = []  # list(name_to_audio_path_dict)
        for track_name, track_text in zip(name_to_audio_path_dict, listening_text_tracks):
            queue.append((track_name, track_text))

        await interaction.followup.send(f"[Lesson {lesson_number}]")
        counter = f"{i}. lesson out of {count_n}."
        msg = await interaction.followup.send(counter)
        view = SessionListenView()

        while True:
            # handling word that has no audio
            try:
                play_track = queue.pop(0)
                voice.play(
                    discord.FFmpegPCMAudio(
                        name_to_audio_path_dict[play_track[0]],
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            content = f"```{counter}\n{play_track[1]}```"

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
                queue.append(play_track)
                i += 1
            elif button_id == "repeat":
                queue.insert(0, play_track)
            elif button_id == "end":
                listening_text = "Ending listening session."

                # ending message
                content = f"```{counter}\n{listening_text}```"
                try:
                    await msg.edit(content=content, view=view)
                except discord.errors.HTTPException as err:
                    print(str(err).encode("utf-8"))
                    break
                break

            counter = f"{i}. lesson out of {count_n}"

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

    @app_commands.command(name="zrvl")
    async def zreview_vocab_listening(self, interaction, level_number: int = 1):
        #"""Start listening vocab exercise.

        #In the case of customized lesson, audio files will be loaded only
        #from level that is set in the settings. TODO!!! find that are in custom
        #"""

        await interaction.response.send_message(
            "...Setting up listening session..."
        )

        # get voice
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )

        def get_worksheet(spread_name, sheet_name):
            credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
            credentials_dict = json.loads(credentials_dict_str)
            g_credentials = gspread.service_account_from_dict(credentials_dict)
            g_sheet = g_credentials.open(spread_name)
            worksheet = g_sheet.worksheet(sheet_name)
            return worksheet

        # TODO: update new sheet (has no header.. create it) (FFreezpmark-2)
        # TODO: create score_monitor-2 automatically,,, its missing now
        # TODO: review takes one less word into account bug..
        vocab_g_ws = get_worksheet("Korea - Users stats", f"{interaction.user.name}-{level_number}")
        score_g_ws = get_worksheet("Korea - Users stats", f"score_monitor-{level_number}")
        score_g_ws2 = get_worksheet("Korea - Users stats", f"score_monitor-{level_number}-timed")
        score_g_ws.clear()
        score_g_ws2.clear()
        score_list = []
        score_list2 = []

        # get current_session_number
        session_numbers = vocab_g_ws.col_values(4)
        if session_numbers:
            last_session_number = max(map(int, session_numbers[1:]))
            current_session_number = last_session_number + 1
        else:
            current_session_number = 1
        
        # get 50 sorted word scores
        df = pd.DataFrame(vocab_g_ws.get_all_records())
        df.sort_values(["Word", "Date"], ascending=[True, False], inplace=True)

        distr = (1, 0.8, 0.64, 0.512, 0.4096, 0.32768, 0.262144, 0.209715, 0.167772, 0.1342176, 0.107374)
        scores = {i: j for i, j in enumerate(distr)}
        datetime_now = datetime.now()

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
                    word_score_time_penalized = word_score + new_word_time_penalty_total
                    word_scores[new_word] = word_score
                    score_list.append(
                        [
                            new_word,
                            word_score,
                            "".join(knowledge_marks),
                            ", ".join(str(round(x,2)) for x in debug_compute)
                        ]
                    )
                    score_list2.append(
                        [
                            new_word,
                            word_score_time_penalized,
                            "".join(knowledge_marks),
                            ", ".join(str(round(x,2)) for x in debug_compute)
                        ]
                    )
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
        score_g_ws.append_rows(score_list)
        score_list2 = sorted(score_list2, key=lambda x:x[1], reverse=True)
        score_g_ws2.append_rows(score_list2)

        sorted_word_score = sorted(word_scores.items(), key=lambda item: item[1], reverse=True)
        number_of_words = len(score_list) if len(score_list) < 100 else 100
        sorted_words = [sorted_word_score[i][0] for i in range(number_of_words)]

        # word, score, marks arranged

        # Use probability distribution to pick the most unknown words to known words
        # Create a list of probabilities that decrease linearly from left to right
        size = number_of_words if number_of_words < 50 else 50
        weights = np.linspace(1, 0, number_of_words)
        weights /= weights.sum()
        nl = np.random.choice(sorted_words, p=weights, size=size, replace=False)

        # IPYNB #######################################
        # import numpy as np
        # import matplotlib.pyplot as plt

        # # Set up the range of values to sample from
        # values = np.arange(100)

        # weights = np.linspace(1, 0, 100)
        # weights /= weights.sum()
        # sampled_value = np.random.choice(values, p=weights, size=50, replace=False)

        # plt.hist(sampled_value, bins=20, density=True)  # , , density=True
        # plt.show()
        # print(sum(sampled_value[:25]))
        # print(sum(sampled_value[25:]))
        # sampled_value
        # IPYNB #######################################

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
        # nl2 = nl2[::-1]
        i = 1
        count_n = len(nl)
        kor_to_eng = pd.Series(self.vocab_df.Book_English.values, index=self.vocab_df.Korean)[::-1].to_dict()
        kor_to_eng_exs = pd.Series(zip(self.vocab_df.Example_EN, self.vocab_df.Example_KR), index=self.vocab_df.Korean)[::-1].to_dict()

        # ### there was a problem that it read duplication instead of first occurence.. so i just removed the row;; maybe just ::-1 is enough
        # vocab = []

        # for row in self.vocab_df.itertuples():
        #     if not row.Lesson:
        #         continue
        #     if row.Lesson > lesson_number:
        #         break
        #     if row.Lesson == lesson_number:
        #         vocab.append((row.Book_English, row.Korean))

        # random.shuffle(vocab)
        # ###

        await interaction.followup.send(f"[Review]; session: {current_session_number}")
        counter = f"{i}. word out of {count_n}."
        msg = await interaction.followup.send(counter)


        def compute_percentages(easy, medium, hard):
            total = easy + medium + hard
            return (
                round(easy * 100 / total, 1),
                round(medium * 100 / total, 1),
                round(hard * 100 / total, 1),
            )

        stats_label = {"easy": "✅", "medium": "⏭️", "hard": "❌"}
        stats_list = []
        easy = easy_p = 0
        medium = medium_p = 0
        hard = hard_p = 0
        stats = ""
        view = SessionVocabView()

        # change: vocab = nl[-1][0], eng = kor_to_eng

        while True:
            kor = nl[-1]
            example = f"\n{kor_to_eng_exs[kor][1]} = {kor_to_eng_exs[kor][0]}" if kor_to_eng_exs[kor][0] else ""
            kor_no_num = kor[:-1] if kor[-1].isdigit() else kor

            # handling word that has no audio
            if kor_no_num in self.vocab_audio_paths:
                msg_display = f"||{kor} = {kor_to_eng[kor]:20}" + " " * (i % 15) + f"{example}||"
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
                msg_display = f"{kor} = ||{kor_to_eng[kor]:20}" + " " * (i % 15) + f"{example}||"

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
                word_to_move = nl.pop()

                nl.insert(0, word_to_move)
                easy += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )
            elif button_id == "medium":
                word_to_move = nl.pop()

                nl.insert(len(nl) // 2, word_to_move)
                medium += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )
            elif button_id == "hard":
                word_to_move = nl.pop()

                new_index = len(nl) // 5
                nl.insert(-new_index, word_to_move)
                hard += 1
                count_n += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )

            elif button_id == "end":
                msg_display = "Ending listening session."

                # ending message
                content = f"{counter}\n{msg_display}\n{stats}"
                try:
                    await msg.edit(content=content, view=view)
                except discord.errors.HTTPException as err:
                    print(err)
                    vocab_g_ws.append_rows(stats_list)
                    msg = await interaction.followup.send(content)
                    await msg.edit(content=content, view=view)
                    break
                vocab_g_ws.append_rows(stats_list)
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
                    word_to_move,
                    stats_label[button_id],
                    current_session_number,
                ]
            )



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


    @app_commands.command(name="zer")
    async def zexercise_reading(self, interaction, lesson_number: int = 102):
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

# NOTE
# MAX Values: 4 * 1 (20% decr each) + 0.01 (per day difference)
# Refresh scoring after 10 attempts
