import json
import os
import random
from collections import defaultdict
from datetime import datetime
from glob import glob
from pathlib import Path

import discord
import pytz
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from cogs.korean.search_and_create_vocab import dl_vocab
from cogs.korean.session_view import SessionView


class Language(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()
        self.ffmpeg_path = (
            "C:/ffmpeg/ffmpeg.exe" if os.name == "nt" else "/usr/bin/ffmpeg"
        )

    # These parameters doesn't need to be in config, they're not so usable
    personalization = True  # NotImplemented
    show_eng_word = 1  # works for writing exercise

    def load_config(self):
        source_dir = Path(__file__).parents[0]
        config_path = Path(f"{source_dir}/config.json")
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as file:
                config = json.load(file)
        else:
            config = {"level": 1, "lesson": 1, "custom": "default"}
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(config, file)

        return config

    def save_config(self):
        source_dir = Path(__file__).parents[0]
        config_path = Path(f"{source_dir}/config.json")
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(self.config, file)

    @property
    def level(self):
        return f'vocab_level_{self.config["level"]}'

    @level.setter
    def level(self, number):
        self.config["level"] = number
        self.save_config()

    @property
    def lesson(self):
        return f'lesson_{self.config["lesson"]}'

    @lesson.setter
    def lesson(self, number):
        self.config["lesson"] = number
        self.save_config()

    @property
    def custom(self):
        return f'custom_{self.config["custom"]}'

    @custom.setter
    def custom(self, fname):
        self.config["custom"] = fname
        self.save_config()

    @app_commands.command()
    async def korean_settings(self, interaction):
        """Shows level, lesson, custom settings."""

        embed = discord.Embed(
            title="Korean settings",
            description="Settings for choosing lessons",
            colour=discord.Colour.blue(),
        )
        for setting in self.config:
            embed.add_field(name=setting, value=self.config[setting])

        await interaction.response.send_message(embed=embed)

    @app_commands.command()
    async def set_level(self, interaction, number: int):
        self.level = number
        msg = f"Level number was set to {number}."
        await interaction.response.send_message(msg)

    @app_commands.command()
    async def set_lesson(self, interaction, number: int):
        self.lesson = number
        msg = f"Lesson number was set to {number}."
        await interaction.response.send_message(msg)

    @app_commands.command()
    async def set_custom_filename(self, interaction, fname: str):
        self.custom = fname
        msg = f"Custom file name was set to {fname}."
        await interaction.response.send_message(msg)

    @app_commands.command()
    async def add_lesson(self, interaction):
        """Adds lesson into user's customized lesson file."""

        source_dir = Path(__file__).parents[0]
        data_path = Path(f"{source_dir}/data")
        data_user_path = Path(f"{data_path}/users/{interaction.user.name}")
        Path(data_user_path).mkdir(parents=True, exist_ok=True)
        custom_path = Path(f"{data_user_path}/{self.custom}.json")

        if os.path.exists(custom_path):
            with open(custom_path, encoding="utf-8") as file:
                custom_vocab = json.load(file)
        else:
            custom_vocab = {}

        level_path = Path(f"{data_path}/{self.level}.json")
        with open(level_path, encoding="utf-8") as file:
            level_vocab = json.load(file)

        custom_vocab = {**custom_vocab, **level_vocab[self.lesson]}
        with open(custom_path, "w", encoding="utf-8") as file:
            json.dump(custom_vocab, file, indent=4, ensure_ascii=False)

        msg = f"{self.lesson} from {self.level} was saved into {self.custom}."
        await interaction.response.send_message(msg)

    @app_commands.command()
    async def create_vocab(
        self, interaction, lesson_only: int = 1, text_only: int = 1
    ):
        """Creates audio and json files from the text files."""

        lesson = self.lesson if lesson_only else False
        msg = "Downloading and creating vocab..."
        await interaction.response.send_message(msg)
        dl_vocab(self.level, lesson, text_only)
        await interaction.followup.send("Vocab has been created!")

    @app_commands.command(name="e")
    async def exercise(self, interaction):
        """Start vocab exercise."""

        source_dir = Path(__file__).parents[0]
        level_path = Path(f"{source_dir}/data/{self.level}.json")
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
            users_dir = Path(f"{source_dir}/data/users")
            Path(users_dir).mkdir(parents=True, exist_ok=True)
            file_score_path = Path(f"{users_dir}/{file_name}")
            if os.path.exists(file_score_path):
                with open(file_score_path, encoding="utf-8") as file:
                    json_content = json.load(file)
                    stats = defaultdict(list, json_content)

        # TODO: Get audio
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:  # slash commands?!
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )
        audio_paths = glob(f"cogs/data/{self.level}/{self.lesson}/*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = Path(audio_path).stem
            name_to_path_dict[word] = audio_path

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
            if answer in name_to_path_dict:
                voice.play(
                    discord.FFmpegPCMAudio(
                        name_to_path_dict[answer],
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

    @app_commands.command(name="el")
    async def exercise_listening(self, interaction, custom: int = 0):
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
            activity=discord.Game(name="Vocab listening")
        )

        # get vocab words
        import gspread
        import pandas as pd

        credentials_dict_str = os.environ["GOOGLE_CREDENTIALS"]
        credentials_dict = json.loads(credentials_dict_str)
        g_credentials = gspread.service_account_from_dict(credentials_dict)
        gs_vocab = g_credentials.open("Korea - Vocabulary")
        ws_vocab = gs_vocab.worksheet("Level 1-2 (modified)")

        gs_stats = g_credentials.open("Korea - Users stats")
        try:
            ws_stats = gs_stats.worksheet(interaction.user.name)
        except gspread.exceptions.WorksheetNotFound:
            ws_stats = gs_stats.add_worksheet(
                title=interaction.user.name, rows=10000, cols=4
            )
        session_numbers = ws_stats.col_values(4)
        if session_numbers:
            last_session_number = max(map(int, session_numbers))
            current_session_number = last_session_number + 1
        else:
            current_session_number = 1

        df = pd.DataFrame(ws_vocab.get_all_records())
        vocab = []
        for row in df.itertuples():
            if not row.Lesson:
                continue
            if (
                row.Lesson // 100 > self.config["level"]
                or row.Lesson % 100 > self.config["lesson"]
            ):
                break
            if (
                row.Lesson // 100 == self.config["level"]
                and row.Lesson % 100 == self.config["lesson"]
            ):
                vocab.append((row.Book_English, row.Korean))

        random.shuffle(vocab)

        # load audio files
        source_dir = Path(__file__).parents[0]
        data_path = f"{source_dir}/data/level_{self.config['level']}/lesson_{self.config['lesson']}"
        audio_paths = glob(f"{data_path}/vocabulary_audio/*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = Path(audio_path).stem
            name_to_path_dict[word] = audio_path

        # prepping msgs for the loop session
        i = 1
        count_n = len(vocab)

        await interaction.followup.send(f"[Lesson {custom}]")
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
        unknown_words = []
        easy = easy_p = 0
        medium = medium_p = 0
        hard = hard_p = 0
        stats = ""
        view = SessionView()

        while True:
            eng, kor = vocab[-1]

            # handling word that has no audio
            if kor in name_to_path_dict:
                msg_display = f"||{kor} = {eng}||"
                try:
                    voice.play(
                        discord.FFmpegPCMAudio(
                            name_to_path_dict[kor],
                            executable=self.ffmpeg_path,
                        )
                    )
                except Exception as err:
                    print(f"Wait, press 🔁 to play unplayed audio!!! [{err}]")
            else:
                msg_display = f"{kor} = ||{eng}||"

            content = f"{counter}\n{msg_display}\n{stats}"
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

                unknown_words.append(word_to_move)
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
                await msg.edit(content=content, view=view)
                ws_stats.append_rows(stats_list)
                break

            stats = f"{easy_p}%,   {medium_p}%,   {hard_p}%"
            counter = f"{i}. word out of {count_n}"

            time = datetime.now(pytz.timezone("Europe/Bratislava"))
            time = time.strftime("%Y-%m-%d %H:%M:%S")
            stats_list.append(
                [
                    time,
                    word_to_move[1],
                    stats_label[button_id],
                    current_session_number,
                ]
            )


async def setup(bot):
    await bot.add_cog(
        Language(bot), guilds=[discord.Object(id=os.environ["SERVER_ID"])]
    )


# TODO: Vocab listening activity (session is over -> return fix)
# TODO: Not well known words practice (check stats!)
# TODO: Maybe no need to use pandas, gspread has operations too!
# TODO: Mix lessons
# TODO: Ending session: Stats Graph, sort hardest from easiest words!
# TODO: Competitive mode
# TODO: Download sound for all? (current script is in memo bookmark)
