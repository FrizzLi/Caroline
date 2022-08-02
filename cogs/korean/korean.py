import glob
import json
import os
import random
from collections import defaultdict
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from cogs.korean.create_vocab import dl_vocab


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
        return f'level_{self.config["level"]}'
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
        data_user_path = Path(f"{data_path}/{interaction.user.name}")
        Path(data_user_path).mkdir(parents=True, exist_ok=True)
        custom_path = Path(f"{data_user_path}/{self.custom}.json")

        if os.path.exists(custom_path):
            with open(custom_path, "r", encoding="utf-8") as file:
                custom_vocab = json.load(file)
        else:
            custom_vocab = {}

        level_path = Path(f"{data_path}/{self.level}.json")
        with open(level_path, "r", encoding="utf-8") as file:
            level_vocab = json.load(file)

        custom_vocab = {**custom_vocab, **level_vocab[self.lesson]}
        with open(custom_path, "w", encoding="utf-8") as file:
            json.dump(custom_vocab, file, indent=4, ensure_ascii=False)

        msg = f"{self.lesson} from {self.level} was saved into {self.custom}."
        await interaction.response.send_message(msg)

    @app_commands.command()
    async def create_vocab(self, interaction, lesson_only: int = 1, text_only: int = 1):
        """Creates audio and json files from the text files."""

        lesson = self.lesson if lesson_only else False

        await interaction.response.send_message("Downloading and creating vocab...")
        dl_vocab(self.level, lesson, text_only)
        await interaction.followup.send("Vocab has been created!")

    @app_commands.command(name="e")
    async def exercise(self, interaction):
        """Start vocab exercise."""

        source_dir = Path(__file__).parents[0]
        level_path = Path(f"{source_dir}/data/{self.level}.json")

        with open(level_path, "r", encoding="utf-8") as f:
            all_vocab = json.load(f)

            starting_msg = f'Vocabulary practice mode activated! Start by writing lesson \
                name: {", ".join(all_vocab.keys())}, Exit by typing "EXIT"'
            await interaction.response.send_message(starting_msg)
            await self.bot.change_presence(
                activity=discord.Game(name="Korean vocabulary")
            )

            # message.author.name?, channel..?
            response = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == interaction.user.name
                and message.channel == interaction.channel,
            )
            lesson = response.content

            sub_vocab = list(all_vocab[lesson].items())
            random.shuffle(sub_vocab)

        if self.personalization:
            stats = defaultdict(list)
            nick = response.author.nick
            if os.path.exists(f"cogs/data/{nick}-{lesson}.json"):
                with open(
                    f"cogs/data/{nick}-{lesson}.json", "r", encoding="utf-8"
                ) as f:
                    stats = defaultdict(list, json.load(f))  # optimize maybe
        attempts = 0
        corrects = 0
        incorrect_words = set()

        # get audio
        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")  # slash commands?!
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        audio_paths = glob.glob(f"cogs/data/{self.level}/{lesson}/*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        while not response.content.startswith("EXIT"):  # while True:
            q = sub_vocab[0]
            guessing, answer = q if self.show_eng_word else q[::-1]
            await interaction.followup.send(guessing)
            response = await self.bot.wait_for(
                "message",
                check=lambda message: message.author == interaction.user.name
                and message.channel == interaction.channel,
            )

            if response.content.lower() == answer.lower():
                stats[answer].append(True)
                await interaction.followup.send("Correct!")
                corrects += 1
                sub_vocab.append(sub_vocab.pop(0))
            elif response.content == "?":
                break
            else:
                stats[answer].append(False)
                await interaction.followup.send(f"Incorrect! The right answer is {answer}")
                incorrect_words.add(guessing)
                new_index = len(sub_vocab) // 5
                # old_index = sub_vocab.index(q)
                sub_vocab.insert(new_index, sub_vocab.pop(0))
            attempts += 1

            # play sound
            if answer in name_to_path_dict:
                voice.play(
                    discord.FFmpegPCMAudio(
                        name_to_path_dict[answer],
                        executable="C:/ffmpeg/ffmpeg.exe",
                    )
                )

            # set queuer
            # level, lesson
            # answer

            # requires optimalization
            continue_ = False
            for word in stats.values():
                for last_result in word[-1::]:
                    if not last_result:
                        continue_ = True

            if not continue_ and len(sub_vocab) <= attempts:
                await interaction.followup.send(
                    f"You answered all words correctly twice in a row! \
                    (or once if you only guessed once). \
                    Incorrect words are: {incorrect_words}"
                )
                break

        # print and save stats
        accuracy = corrects / attempts * 100
        msg = f"{corrects} answers were right out of {attempts}! \
            ({accuracy:.2f}%)"
        await interaction.followup.send(msg)
        if self.personalization:
            with open(
                f"cogs/data/{nick}-{lesson}.json", "w", encoding="utf-8"
            ) as f:
                json.dump(stats, f, sort_keys=True, ensure_ascii=False)
            await interaction.followup.send("Score has been saved.")
        await interaction.followup.send(f"Exiting {lesson} exercise..")

    @app_commands.command(name="el")
    async def exercise_listening(self, interaction, custom: int = 0):
        """Start listening vocab exercise.

        In the case of customized lesson, audio files will be loaded only
        from level that is set in the settings.
        """

        voice = get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        await self.bot.change_presence(activity=discord.Game(name="Korean"))

        # get vocab
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "\\data"
        if custom:
            full_path = f"{dir_path}\\{interaction.user.name}\\{self.custom}.json"
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    all_vocab = json.load(f)
            else:
                await interaction.response.send_message("Custom file does not exist.")
                raise commands.CommandError("Custom file does not exist.")
            all_vocab = [(k, v) for k, v in all_vocab.items()]
        else:
            full_path = f"{dir_path}\\{self.level}.json"
            with open(full_path, "r", encoding="utf-8") as f:
                all_vocab = json.load(f)
            all_vocab = [(k, v) for k, v in all_vocab[self.lesson].items()]
            random.shuffle(all_vocab)

        # load audio files
        audio_paths = f"{dir_path}\\{self.level}\\"
        if custom:  # from whole level
            audio_paths = glob.glob(f"{audio_paths}\\*\\*")
        else:  # from one lesson
            audio_paths = glob.glob(f"{audio_paths}\\{self.lesson}\\*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        i = 1
        n = len(all_vocab)
        if custom:
            practice = self.custom
        else:
            practice = f"{self.level} - {self.lesson}"

        msg_counter = await interaction.followup.send(f"[{practice}]: {i}. out of {n}.")
        msg = await interaction.followup.send("Starting...")
        msg_stats = await interaction.followup.send("Turning on stats...")
        await msg_stats.add_reaction("✅")  # next: know well
        await msg_stats.add_reaction("⏭️")  # next: know okayish
        await msg_stats.add_reaction("❌")  # next: don't know
        await msg_stats.add_reaction("🔁")  # repeat
        await msg_stats.add_reaction("🔚")  # end

        # nobody except the command sender can interact with the "menu"
        def check(reaction, user):
            return user == interaction.user.name and reaction.emoji in [
                "🔚",
                "⏭️",
                "🔁",
                "❌",
                "✅",
            ]

        def compute_percentages(good, ok, bad):
            total = good + ok + bad
            return (
                round(good * 100 / total, 1),
                round(ok * 100 / total, 1),
                round(bad * 100 / total, 1),
            )

        unknown_words = []
        good = g = 0
        ok = o = 0
        bad = b = 0

        # edit last message with spoiled word
        run = True
        while run:
            eng, kor = all_vocab[-1]

            # handling word that has no audio
            if kor in name_to_path_dict:
                msg_display = f"||{kor} = {eng}||"
                try:
                    p, e = name_to_path_dict[kor], "C:/ffmpeg/ffmpeg.exe"
                    voice.play(discord.FFmpegPCMAudio(p, executable=e))
                except Exception:
                    await interaction.followup.send("Wait, press 🔁 to play unplayed audio.")
            else:
                msg_display = f"{kor} = ||{eng}||"

            await msg.edit(content=msg_display)
            reaction, user = await self.bot.wait_for(
                "reaction_add", check=check
            )

            if reaction.emoji == "🔚":
                msg_display = "Ending listening session."
                run = False

                # save unknown words to file for future
                unknown_words = {k: v for k, v in unknown_words}
                path = f"{dir_path}\\{interaction.user.name}\\"
                if custom:
                    path += f"{self.custom}_unknown.json"
                else:
                    path += f"{self.level}_unknown.json"
                    unknown_words = {self.lesson: unknown_words}
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as cf:
                        old_unknown_words = json.load(cf)
                else:
                    old_unknown_words = {}
                unknown_words = {**unknown_words, **old_unknown_words}
                with open(f"{path}", "w", encoding="utf-8") as cf:
                    json.dump(unknown_words, cf, indent=4, ensure_ascii=False)

                # save vocab queue to file
                if custom:
                    dict_vocab = {k: v for k, v in all_vocab}
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(dict_vocab, f, indent=4, ensure_ascii=False)

            elif reaction.emoji != "🔁":
                word_to_move = all_vocab.pop()
                if reaction.emoji == "✅":
                    all_vocab.insert(0, word_to_move)
                    good += 1
                elif reaction.emoji == "⏭️":
                    all_vocab.insert(len(all_vocab) // 2, word_to_move)
                    ok += 1
                    n += 1
                elif reaction.emoji == "❌":
                    unknown_words.append(word_to_move)
                    if custom:
                        all_vocab.insert(-10, word_to_move)
                    else:
                        new_index = len(all_vocab) // 5
                        all_vocab.insert(-new_index, word_to_move)
                    bad += 1
                    n += 1

                i += 1
                g, o, b = compute_percentages(good, ok, bad)

            stats = f"{g}%,   {o}%,   {b}%"
            counter = f"[{practice}]: {i}. out of {n}"

            await msg_stats.remove_reaction(reaction, user)
            await msg_stats.edit(content=stats)
            await msg_counter.edit(content=counter)
            await msg.edit(content=msg_display)


async def setup(bot):
    await bot.add_cog(Language(bot), guilds=[discord.Object(id=os.environ.get("SERVER_ID"))])

# TODO: Apply Slash commands, Fix MMPEG to play
# TODO: Guessing, Bigger buttons, Mix lessons
# TODO: Improve vocab explanation (text files)

# TODO: remove keep_alive (repl.it)
