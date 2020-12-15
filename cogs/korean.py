import json
import random
import numpy as np
import collections as col
import os
from scipy.stats import expon
#
import os, random, shutil, glob
import discord
from discord.ext import commands
from discord.utils import get, find
from mutagen.mp3 import MP3

from collections import defaultdict

class Language(commands.Cog):
    def __init__(self, client):
        self.client = client

    unit = "school_2"
    show_eng_word = 1  # 0 - write in english
    personalization = True  # for now, just add bools of correctness

    # change options of unit, show_eng_word, personalization


    @commands.command(brief="start vocab exercise")
    async def exercise(self, ctx):

        with open('cogs/edu/knowledge.json', 'r', encoding='utf-8') as f:
            all_vocab = json.load(f)

            await ctx.send(f'Vocabulary practice mode activated! Start by writing unit name: {", ".join(all_vocab.keys())}, Exit by "{ctx.prefix}"')
            await self.client.change_presence(activity=discord.Game(name='Korean vocabulary'))
            response = await self.client.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
            unit = response.content

            sub_vocab = list(all_vocab[unit].items())
            random.shuffle(sub_vocab)

        if self.personalization:
            stats = defaultdict(list)
            nick = response.author.nick
            if os.path.exists(f"cogs/edu/{nick}-{unit}.json"):
                with open(f'cogs/edu/{nick}-{unit}.json', 'r', encoding='utf-8') as f:
                    stats = defaultdict(list, json.load(f))  # optimize maybe
        probs = expon.pdf(np.linspace(0, 5, len(sub_vocab)))   # expon.ppf(0.01), expon.ppf(0.99)
        attempts = 0
        corrects = 0

        while not response.content.startswith(f'{ctx.prefix}'):  # while True:
            q = random.choices(sub_vocab, weights=probs)[0]
            guessing, answer = q if self.show_eng_word else q[::-1]
            await ctx.send(f"{guessing}")   # response = input(guessing + '   ')  # DISCORD INPUT
            response = await self.client.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
            sub_vocab.append(sub_vocab.pop(sub_vocab.index(q)))  # lower prob

            if response.content.lower() == answer.lower():
                stats[answer].append(True)
                await ctx.send("Correct!")
                corrects += 1
            elif response.content == "?":
                break
            else:
                stats[answer].append(False)
                await ctx.send(f"Uncorrect! The right answer is {answer}")
                # simple implementation is to not append, but put in 33% of the queue or so
            attempts += 1

        # print and save stats
        await ctx.send('{} answers were right out of {}! ({:.2f}%)'.format(corrects, attempts, corrects/attempts*100))
        if self.personalization:
            with open(f'cogs/edu/{nick}-{unit}.json', 'w', encoding='utf-8') as f:
                json.dump(stats, f, sort_keys=True, ensure_ascii=False)
            await ctx.send('Score has been saved.')
        await ctx.send('Exiting exercise..')

def setup(client):
    client.add_cog(Language(client))

##############################################################
# vypocitat kolko % sa bralo z KNOW a REPE
# y2 = tpQueue / len(probs)          # vaha UPLNE nahodne vybraneho
# z2 = y2 * 100 / tpQueue            # percento UPLNE nahodneho vybraneho (priemernej vahy) (100 / len(probs)
# w2 = pQueue[queue.index(guessing)]     # vaha vybraneho
# u2 = w2 * 100 / tpQueue            # percento vybraneho
# h2 = u2 * 100 / z2                  # hodnota predstavujuca rozdiel medzi vybranym a uplne nahodne vybranym

# DISCORD ToDo: 
#   competitive mode -> ked je nespravne nic sa nestane, nieje personalizacia
#   vyhodnotenie vsetkych co sa zustastnili
#   vykreslenie vedenia pismen/slov [KNOW_HISTORY] 
#   stats function - Pismena, Slova (z akeho konca) -> Total spravne, total attemptov, (GLOBAL)
