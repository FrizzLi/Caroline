import json
import random
import os
import glob
import discord
from discord.ext import commands
from discord.utils import get
from collections import defaultdict
from pathlib import Path


class Language(commands.Cog):
    def __init__(self, client):
        self.client = client

    show_eng_word = 1  # NotImplemented (0 - write in english)
    personalization = True  # NotImplemented

    # TODO: hint somewhere in order to cancel session, press ctx.prefix
    unfounded_words_save = False

    # TODO: write level/lesson automatically into variables
    # TODO: hint out the number possibilities of level/lesson
    level = "level_3"
    lesson = "lesson_2"

    # TODO: function to add lesson to queue file (with file creation too)
    review_fname = "review_3"

    @commands.command(brief="start listening vocab exercise", aliases=["el"])
    async def exerciseListening(self, ctx, review=False):

        # TODO: this could be placed in a wrapper (voice.py)
        voice = get(self.client.voice_clients, guild=ctx.guild)
        user_voice = ctx.message.author.voice
        if not voice and not user_voice:
            await ctx.send(
                "You or bot have to be connected to voice channel first."
            )
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)

        await self.client.change_presence(activity=discord.Game(name="Korean"))

        # get vocab
        dir_path = os.path.dirname(os.path.abspath(__file__)) + "\\edu"
        if review:
            full_path = f"\\{ctx.author}"  # /{self.review_fname}
            Path(full_path).mkdir(parents=True, exist_ok=True)
            full_path = f"{full_path}\\{self.review_fname}.json"
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    all_vocab = json.load(f)
            else:
                await ctx.send("Review vocab file does not exist.")
                raise commands.CommandError(
                    "Review vocab file does not exist."
                )
            all_vocab = [(k, v) for k, v in all_vocab[self.lesson].items()]
        else:
            full_path = f"{dir_path}\\{self.level}.json"
            with open(full_path, "r", encoding="utf-8") as f:
                all_vocab = json.load(f)
            all_vocab = [(k, v) for k, v in all_vocab[self.lesson].items()]
            random.shuffle(all_vocab)

        # load all audio files in one lesson
        # TODO: in review, load all audio files in one level
        audio_paths = glob.glob(f"{dir_path}\\{self.level}\\{self.lesson}\\*")
        name_to_path_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            name_to_path_dict[word] = audio_path

        # TODO: counting how many words are in a lesson/level(?)
        #       and how many I had quessed
        # #msg = await ctx.send("")
        msg = await ctx.send("STARTING...")
        await msg.add_reaction("✅")  # next: know well
        await msg.add_reaction("⏭️")  # next: know okayish
        await msg.add_reaction("❌")  # next: don't know
        await msg.add_reaction("🔁")  # repeat
        await msg.add_reaction("🔚")  # end

        # nobody except the command sender can interact with the "menu"
        def check(reaction, user):
            return user == ctx.author and reaction.emoji in "🔚⏭️🔁❌✅"

        # edit last message with spoiled word
        while True:
            eng, kor = all_vocab[0]

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
                if review:
                    dict_vocab = {k: v for k, v in all_vocab}
                    with open(full_path, "w", encoding="utf-8") as f:
                        json.dump(dict_vocab, f, indent=4, ensure_ascii=False)
                break
            await msg.edit(content=msg_display)

            if reaction.emoji == "🔁":
                continue
            word_to_move = all_vocab.pop(0)
            if reaction.emoji == "✅":
                all_vocab.append(word_to_move)
            elif reaction.emoji == "⏭️":
                all_vocab.insert(len(all_vocab) // 2, word_to_move)
            elif reaction.emoji == "❌":
                if review:
                    all_vocab.insert(10, word_to_move)
                else:
                    new_index = len(all_vocab) // 5
                    all_vocab.insert(new_index, word_to_move)

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
            await ctx.send(
                "You or bot have to be connected to the voice channel first."
            )
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
