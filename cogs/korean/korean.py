import json
import os
import random
from collections import defaultdict
from glob import glob
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from cogs.korean.search_and_create_vocab import dl_vocab
from cogs.korean.session_view import SessionView


class Language(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()

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
            config = {"level": "1", "lesson": "1", "custom": "default"}
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

        # TODO: get audio
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
            word = audio_path.split("/")[-1][:-4]
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
                        executable="C:/ffmpeg/bin/ffmpeg.exe",
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

        # get vocab
        source_dir = Path(__file__).parents[0]
        data_path = f"{source_dir}/data"

        if custom:
            custom_file_path = Path(f"{data_path}/users/{self.custom}.json")
            if os.path.exists(custom_file_path):
                with open(custom_file_path, encoding="utf-8") as file:
                    custom_vocab = json.load(file)
            else:
                msg = "Custom file does not exist."
                await interaction.response.send_message(msg)
                raise commands.CommandError("Custom file does not exist.")
            vocab = list(custom_vocab.items())
        else:
            custom_file_path = Path(f"{data_path}/{self.level}.json")
            with open(custom_file_path, encoding="utf-8") as f:
                vocab = json.load(f)
            vocab = list(vocab[self.lesson].items())

        random.shuffle(vocab)

        # load audio files
        level_path = f"{data_path}/{self.level}"
        if custom:  # from whole level
            audio_paths = glob(f"{level_path}/*/*")
        else:  # from one lesson
            audio_paths = glob(f"{level_path}/{self.lesson}/vocabulary_audio/*")

        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        i = 1
        count_n = len(vocab)
        if custom:
            practice = self.custom
        else:
            practice = f"{self.level} - {self.lesson}"

        await interaction.response.send_message(f"[{practice}]")
        counter = f"{i}. word out of {count_n}."
        msg = await interaction.followup.send(counter)

        def compute_percentages(easy, medium, hard):
            total = easy + medium + hard
            return (
                round(easy * 100 / total, 1),
                round(medium * 100 / total, 1),
                round(hard * 100 / total, 1),
            )

        unknown_words = []
        easy = easy_p = 0
        medium = medium_p = 0
        hard = hard_p = 0
        stats = ""

        # edit last message with spoiled word
        run = True
        view = SessionView()

        while run:
            eng, kor = vocab[-1]

            # handling word that has no audio
            if kor in name_to_path_dict:
                msg_display = f"||{kor} = {eng}||"
                try:
                    voice.play(
                        discord.FFmpegPCMAudio(
                            name_to_path_dict[kor],
                            executable="C:/ffmpeg/bin/ffmpeg.exe",
                        )
                    )
                except Exception:
                    print("Wait, press 🔁 to play unplayed audio!!!")
            else:
                msg_display = f"{kor} = ||{eng}||"

            content = f"{counter}\n{msg_display}\n{stats}"
            await msg.edit(content=content, view=view)

            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )
            button_id = interaction.data["custom_id"]
            if button_id == "end":
                msg_display = "Ending listening session."
                run = False

                # save unknown words to file for future
                unknown_words = dict(unknown_words)
                path_str = f"{data_path}/{interaction.user.name}"
                if custom:
                    path = Path(f"{path_str}/{self.custom}_unknown.json")
                else:
                    path = Path(f"{path_str}/{self.level}_unknown.json")
                    unknown_words = {self.lesson: unknown_words}
                if os.path.exists(path):
                    with open(path, encoding="utf-8") as file:
                        old_unknown_words = json.load(file)
                else:
                    old_unknown_words = {}
                unknown_words = {**unknown_words, **old_unknown_words}
                with open(path, "w", encoding="utf-8") as file:
                    json.dump(
                        unknown_words, file, indent=4, ensure_ascii=False
                    )

                # save vocab queue to file
                if custom:
                    dict_vocab = dict(vocab)
                    with open(custom_file_path, "w", encoding="utf-8") as file:
                        json.dump(
                            dict_vocab, file, indent=4, ensure_ascii=False
                        )

                content = f"{counter}\n{msg_display}\n{stats}"
                await msg.edit(content=content, view=view)

            elif button_id != "repeat":
                word_to_move = vocab.pop()
                if button_id == "easy":
                    vocab.insert(0, word_to_move)
                    easy += 1
                elif button_id == "medium":
                    vocab.insert(len(vocab) // 2, word_to_move)
                    medium += 1
                    count_n += 1
                elif button_id == "hard":
                    unknown_words.append(word_to_move)
                    if custom:
                        vocab.insert(-10, word_to_move)
                    else:
                        new_index = len(vocab) // 5
                        vocab.insert(-new_index, word_to_move)
                    hard += 1
                    count_n += 1

                i += 1
                easy_p, medium_p, hard_p = compute_percentages(
                    easy, medium, hard
                )

            stats = f"{easy_p}%,   {medium_p}%,   {hard_p}%"
            counter = f"{i}. word out of {count_n}"


async def setup(bot):
    await bot.add_cog(
        Language(bot), guilds=[discord.Object(id=os.environ.get("SERVER_ID"))]
    )

# TODO: Mix lessons, Improve vocab explanation (text files, passively)
# TODO: Competitive mode, remake, lint
# TODO: GDocs and GSpreadsheet instead of gspread and local txt files
# vocab_lesson_x.json remake (customized files though!)