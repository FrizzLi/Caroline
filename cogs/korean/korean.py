import json
import random
import os
import glob
import discord
from discord.ext import commands
from discord.utils import get
from collections import defaultdict
from pathlib import Path

from cogs.korean.edu.create_vocab import createVocab as crVocab


class Language(commands.Cog):
    def __init__(self, client):
        kor_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f"{kor_dir}\\kor_config.json", "r") as cf:
            config = json.load(cf)

        self.client = client
        self.config = config

    # These parameters doesn't need to be in config, they're not so usable
    personalization = True  # NotImplemented
    unfounded_save = 0
    show_eng_word = 1

    @property
    def level(self):
        return f'level_{self.config["level"]}'

    @property
    def lesson(self):
        return f'lesson_{self.config["lesson"]}'

    @property
    def review(self):
        return f'review_{self.config["review"]}'

    def saveJsonConfig(self):
        kor_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f"{kor_dir}\\kor_config.json", "w") as cf:
            json.dump(self.config, cf)

    @level.setter
    def level(self, number):
        self.config["level"] = number
        self.saveJsonConfig()

    @lesson.setter
    def lesson(self, number):
        self.config["lesson"] = number
        self.saveJsonConfig()

    @review.setter
    def review(self, fname):
        self.config["review"] = fname
        self.saveJsonConfig()

    @commands.command()
    async def setLevel(self, ctx, number):
        self.level = number
        await ctx.send(f"Level number was set to {number}.")

    @commands.command()
    async def setLesson(self, ctx, number):
        self.lesson = number
        await ctx.send(f"Lesson number was set to {number}.")

    @commands.command()
    async def setReviewFilename(self, ctx, fname):
        self.review = fname
        await ctx.send(f"Review file name was set to {fname}.")

    @commands.command(brief="shows level, lesson, review settings.")
    async def koreanSettings(self, ctx):
        embed = discord.Embed(
            title="Korean settings",
            description="Settings for choosing lessons and reviews sessions",
            colour=discord.Colour.blue(),
        )
        for setting in self.config:
            embed.add_field(name=setting, value=self.config[setting])

        await ctx.send(embed=embed)

    @commands.command(brief="adds a lesson to review file (par. by settings)")
    async def addLesson(self, ctx):
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "\\edu"

        path_to_author = f"{dir_path}\\{ctx.author}"
        Path(path_to_author).mkdir(parents=True, exist_ok=True)
        path_to_review = f"{path_to_author}\\{self.review}.json"
        if os.path.exists(path_to_review):
            with open(path_to_review, "r", encoding="utf-8") as f:
                review_vocab = json.load(f)
        else:
            review_vocab = {}

        path_to_lesson = f"{dir_path}\\{self.level}.json"
        with open(path_to_lesson, "r", encoding="utf-8") as cf:
            level_vocab = json.load(cf)

        review_vocab = {**review_vocab, **level_vocab[self.lesson]}
        with open(f"{path_to_review}", "w", encoding="utf-8") as cf:
            json.dump(review_vocab, cf, indent=4, ensure_ascii=False)

        await ctx.send(
            f"{self.lesson} from {self.level} was saved into {self.review}."
        )

    @commands.command(brief="creates vocab from text file [lesson_only]")
    async def createVocab(self, ctx, lesson_only=1):
        lesson = self.lesson if lesson_only else False
        crVocab(self.level, lesson, self.show_eng_word, self.unfounded_save)
        await ctx.send("Vocab has been created!")

    @commands.command(brief="start listening vocab exercise++", aliases=["el"])
    async def exerciseListening(self, ctx, review=0):
        """In the case of review session, audio files will be loaded only from
        level that is set in the settings."""

        # TODO: this could be placed in a wrapper (voice.py) (?)
        voice = get(self.client.voice_clients, guild=ctx.guild)
        user_voice = ctx.message.author.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)

        await self.client.change_presence(activity=discord.Game(name="Korean"))

        # get vocab
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "\\edu"
        if review:
            full_path = f"{dir_path}\\{ctx.author}\\{self.review}.json"
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    all_vocab = json.load(f)
            else:
                await ctx.send("Review vocab file does not exist.")
                raise commands.CommandError(
                    "Review vocab file does not exist."
                )
            all_vocab = [(k, v) for k, v in all_vocab.items()]
        else:
            full_path = f"{dir_path}\\{self.level}.json"
            with open(full_path, "r", encoding="utf-8") as f:
                all_vocab = json.load(f)
            all_vocab = [(k, v) for k, v in all_vocab[self.lesson].items()]
            random.shuffle(all_vocab)

        # load audio files
        audio_paths = f"{dir_path}\\{self.level}\\"
        if review:  # from whole level
            audio_paths = glob.glob(f"{audio_paths}\\*\\*")
        else:  # from one lesson
            audio_paths = glob.glob(f"{audio_paths}\\{self.lesson}\\*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        i = 1
        if review:
            practice = self.review
        else:
            practice = f"{self.level} - {self.lesson}"
        msg_counter = await ctx.send(
            f"[{practice}]: {i}. word out of {len(all_vocab)}."
        )
        msg = await ctx.send("STARTING...")
        await msg.add_reaction("✅")  # next: know well
        await msg.add_reaction("⏭️")  # next: know okayish
        await msg.add_reaction("❌")  # next: don't know
        await msg.add_reaction("🔁")  # repeat
        await msg.add_reaction("🔚")  # end

        # nobody except the command sender can interact with the "menu"
        def check(reaction, user):
            return user == ctx.author and reaction.emoji in "🔚⏭️🔁❌✅"

        unknown_words = []

        # edit last message with spoiled word
        while True:
            eng, kor = all_vocab[-1]

            # handling word that has no audio
            if kor in name_to_path_dict:
                msg_display = f"||{kor} = {eng}||"
                try:
                    p, e = name_to_path_dict[kor], "C:/ffmpeg/ffmpeg.exe"
                    voice.play(discord.FFmpegPCMAudio(p, executable=e))
                except Exception:
                    await ctx.send("Wait, press 🔁 to play unplayed audio.")
            else:
                msg_display = f"{kor} = ||{eng}||"

            await msg.edit(content=msg_display)
            reaction, user = await self.client.wait_for(
                "reaction_add", check=check
            )

            await msg.remove_reaction(reaction, user)

            if reaction.emoji == "🔚":
                await msg.edit(content="Ending listening session.")

                # save unknown words to file for future
                unknown_words = {k: v for k, v in unknown_words}
                path = f"{dir_path}\\{ctx.author}\\"
                if review:
                    path += f"{self.review}_unknown.json"
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
                if review:
                    dict_vocab = {k: v for k, v in all_vocab}
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(dict_vocab, f, indent=4, ensure_ascii=False)
                break

            await msg.edit(content=msg_display)

            if reaction.emoji == "🔁":
                continue

            word_to_move = all_vocab.pop()
            if reaction.emoji == "✅":
                all_vocab.insert(0, word_to_move)
            elif reaction.emoji == "⏭️":
                all_vocab.insert(len(all_vocab) // 2, word_to_move)
            elif reaction.emoji == "❌":
                unknown_words.append(word_to_move)
                if review:
                    all_vocab.insert(-10, word_to_move)
                else:
                    new_index = len(all_vocab) // 5
                    all_vocab.insert(-new_index, word_to_move)

            i += 1
            await msg_counter.edit(
                content=f"[{practice}]: {i}. word out of {len(all_vocab)}."
            )

    # TODO: needs paths fix and polish
    @commands.command(brief="start vocab exercise", aliases=["e"])
    async def exercise(self, ctx):

        with open(f"cogs/edu/{self.level}.json", "r", encoding="utf-8") as f:
            all_vocab = json.load(f)

            await ctx.send(
                f'Vocabulary practice mode activated! Start by writing lesson \
                name: {", ".join(all_vocab.keys())}, Exit by "{ctx.prefix}"'
            )
            await self.client.change_presence(
                activity=discord.Game(name="Korean vocabulary")
            )
            response = await self.client.wait_for(
                "message",
                check=lambda message: message.author == ctx.author
                and message.channel == ctx.channel,
            )
            lesson = response.content

            sub_vocab = list(all_vocab[lesson].items())
            random.shuffle(sub_vocab)

        if self.personalization:
            stats = defaultdict(list)
            nick = response.author.nick
            if os.path.exists(f"cogs/edu/{nick}-{lesson}.json"):
                with open(
                    f"cogs/edu/{nick}-{lesson}.json", "r", encoding="utf-8"
                ) as f:
                    stats = defaultdict(list, json.load(f))  # optimize maybe
        attempts = 0
        corrects = 0
        incorrect_words = set()

        # get audio
        voice = get(self.client.voice_clients, guild=ctx.guild)
        user_voice = ctx.message.author.voice
        if not voice and not user_voice:
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)
        audio_paths = glob.glob(f"cogs/edu/{self.level}/{lesson}/*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        while not response.content.startswith(f"{ctx.prefix}"):  # while True:
            q = sub_vocab[0]
            guessing, answer = q if self.show_eng_word else q[::-1]
            await ctx.send(
                f"{guessing}"
            )  # response = input(guessing + '   ')  # DISCORD INPUT
            response = await self.client.wait_for(
                "message",
                check=lambda message: message.author == ctx.author
                and message.channel == ctx.channel,
            )

            if response.content.lower() == answer.lower():
                stats[answer].append(True)
                await ctx.send("Correct!")
                corrects += 1
                sub_vocab.append(sub_vocab.pop(0))
            elif response.content == "?":
                break
            else:
                stats[answer].append(False)
                await ctx.send(f"Incorrect! The right answer is {answer}")
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
                await ctx.send(
                    f"You answered all words correctly twice in a row! \
                    (or once if you only guessed once). \
                    Incorrect words are: {incorrect_words}"
                )
                break

        # print and save stats
        await ctx.send(
            "{} answers were right out of {}! ({:.2f}%)".format(
                corrects, attempts, corrects / attempts * 100
            )
        )
        if self.personalization:
            with open(
                f"cogs/edu/{nick}-{lesson}.json", "w", encoding="utf-8"
            ) as f:
                json.dump(stats, f, sort_keys=True, ensure_ascii=False)
            await ctx.send("Score has been saved.")
        await ctx.send(f"Exiting {lesson} exercise..")


def setup(client):
    client.add_cog(Language(client))


# TODO: competitive mode, stats summary after session, knowledge visualization
