import json
import random
import os
import glob
import discord
from discord.ext import commands
from discord.utils import get
from collections import defaultdict


class Language(commands.Cog):
    def __init__(self, client):
        self.client = client

    show_eng_word = 1  # NotImplemented (0 - write in english)
    personalization = True  # NotImplemented

    # TODO: parser, tasks
    unfounded_words_save = False
    level = "3"
    lesson = ""

    @commands.command(brief="start listening vocab exercise", aliases=["el"])
    async def exerciseListening(self, ctx):
        with open(f"cogs/edu/{self.level}.json", "r", encoding="utf-8") as f:
            all_vocab = json.load(f)
            await ctx.send(
                f'Type lesson number up to {len(all_vocab)},\
                Exit by "{ctx.prefix}"'
            )
            await self.client.change_presence(
                activity=discord.Game(name="Korean vocabulary")
            )
            response = await self.client.wait_for(
                "message",
                check=lambda message: message.author == ctx.author
                and message.channel == ctx.channel,
            )
            unit = response.content

            all_vocab = {v: k for k, v in all_vocab[unit].items()}
            # sub_vocab = list(all_vocab[unit].items())
            # random.shuffle(sub_vocab)

            # ### get audio
            voice = get(self.client.voice_clients, guild=ctx.guild)
            user_voice = ctx.message.author.voice
            if not voice and not user_voice:
                await ctx.send(
                    "You or bot have to be connected to voice channel first."
                )
                raise commands.CommandError("No bot nor you is connected.")
            elif not voice:
                await user_voice.channel.connect()
            voice = discord.utils.get(
                self.client.voice_clients, guild=ctx.guild
            )
            audio_paths = glob.glob(f"cogs/edu/{self.level}/{unit}/*")
            path_to_name_dict = {}
            for audio_path in audio_paths:
                word = audio_path.split("\\")[-1][:-4]
                path_to_name_dict[word] = audio_path

            # get questioning words from vocab and shuffle it
            keys = list(all_vocab.keys())
            random.shuffle(keys)
            i = 0

            msg = await ctx.send("STARTING...")
            await msg.add_reaction("⏭️")
            await msg.add_reaction("🔁")
            await msg.add_reaction("🔚")  # repeat, next, end

            # nobody except the command sender can interact with the "menu"
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in "🔚⏭️🔁"

            # edit last message with spoiled word
            while True:
                if i == len(keys):
                    await ctx.send("All words from the lesson have been sent")
                    i = 0

                eng, kor = all_vocab[keys[i]], keys[i]
                if kor in path_to_name_dict:
                    msg_display = f"||{kor} = {eng}||"
                    try:
                        p, e = path_to_name_dict[kor], "C:/ffmpeg/ffmpeg.exe"
                        voice.play(discord.FFmpegPCMAudio(p, executable=e))
                    except Exception:
                        await ctx.send("Wait, press 🔁 to play unplayed audio.")
                else:
                    msg_display = f"{kor} = ||{eng}||"

                await msg.edit(content=msg_display)
                reaction, user = await self.client.wait_for(
                    "reaction_add", check=check
                )

                if str(reaction.emoji) == "🔚":
                    await msg.edit(content="Ending listening session.")
                    await msg.remove_reaction(reaction, user)
                    break

                if str(reaction.emoji) == "⏭️":
                    await msg.edit(content=msg_display)
                    await msg.remove_reaction(reaction, user)
                    i += 1

                elif str(reaction.emoji) == "🔁":
                    await msg.edit(content=msg_display)
                    await msg.remove_reaction(reaction, user)

    @commands.command(brief="start vocab exercise", aliases=["e"])
    async def exercise(self, ctx):

        with open(f"cogs/edu/{self.level}.json", "r", encoding="utf-8") as f:
            all_vocab = json.load(f)

            await ctx.send(
                f'Vocabulary practice mode activated! Start by writing unit \
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
            unit = response.content

            sub_vocab = list(all_vocab[unit].items())
            random.shuffle(sub_vocab)

        if self.personalization:
            stats = defaultdict(list)
            nick = response.author.nick
            if os.path.exists(f"cogs/edu/{nick}-{unit}.json"):
                with open(
                    f"cogs/edu/{nick}-{unit}.json", "r", encoding="utf-8"
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
        audio_paths = glob.glob(f"cogs/edu/{self.level}/{unit}/*")
        path_to_name_dict = {}
        for audio_path in audio_paths:
            word = audio_path.split("\\")[-1][:-4]
            path_to_name_dict[word] = audio_path
        ####

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
            if answer in path_to_name_dict:
                voice.play(
                    discord.FFmpegPCMAudio(
                        path_to_name_dict[answer],
                        executable="C:/ffmpeg/ffmpeg.exe",
                    )
                )

            # set queuer
            # level, unit

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
                f"cogs/edu/{nick}-{unit}.json", "w", encoding="utf-8"
            ) as f:
                json.dump(stats, f, sort_keys=True, ensure_ascii=False)
            await ctx.send("Score has been saved.")
        await ctx.send(f"Exiting {unit} exercise..")


def setup(client):
    client.add_cog(Language(client))


# DISCORD ToDo:
#   competitive mode -> ked je nespravne nic sa nestane, nieje personalizacia
#   vyhodnotenie vsetkych co sa zustastnili
#   vykreslenie vedenia pismen/slov [KNOW_HISTORY] stats
