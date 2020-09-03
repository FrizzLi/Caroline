import random

import discord
from discord.ext import commands

import cogs.model.evolution as evo
import cogs.model.forward_chain as chain
import cogs.model.pathfinding as path
import cogs.view as view


class Commands(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(brief="Rolls a number between 1 and 100. (roll 1000)")
    async def roll(self, ctx, end=100):
        await ctx.send(ctx.message.author.mention + ' rolls ' + str(random.randint(1, end)) + ' (1-' + str(end) + ')')

    @commands.command(brief="Enables Python interactive shell.")
    async def python(self, ctx):
        await ctx.send(f'Python mode activated! Exit by "{ctx.prefix}"')
        await self.client.change_presence(activity=discord.Game(name='Python'))

        ans = 0
        msg = await self.client.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)

        while not msg.content.startswith(f'{ctx.prefix}'):
            try:                                # evaluating with value return
                ans = eval(msg.content)
                await ctx.send(ans)
            except:                             # executing without return
                try:
                    exec(msg.content)
                except Exception as e:          # invalid input
                    await ctx.send(e)
            msg = await self.client.wait_for('message', check=lambda message: message.author == ctx.author and message.channel == ctx.channel)
       
        await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{ctx.prefix}help'))
        await ctx.send("Python mode deactivated!")

    @commands.command(brief="Deletes specified number of messages. (clear 5)")
    async def clear(self, ctx, amount=5):
        channel = ctx.message.channel
        async for message in channel.history(limit=int(amount) + 1):
            await message.delete()
        await ctx.send(f'{amount} messages has been deleted.')

    @commands.command(brief="Creates gif and shows it.")
    async def create(self, ctx):

        # walls uses: query, fname, max_runs, points_amount
        # terrain uses: fname, max_runs, points_amount
        # properties uses: fname, points_amount
        begin_create = "walls"
        query = "10x12 (1,5) (2,1) (3,4) (4,2) (6,8) (6,9) (6,7)"
        fname = "queried"
        max_runs = 1
        points_amount = 10

        movement = "M"
        climb = False
        algorithm = "HK"
        subset_size = None

        save_fname_facts = "facts"
        load_fname_facts = "facts_init"
        load_fname_rules = "rules"
        step_by_step = True
        facts_random_order = True

        evo_parameters = dict(
            begin_create=begin_create,
            query=query,
            fname=fname,
            max_runs=max_runs,
            points_amount=points_amount,
        )

        path_parameters = dict(
            fname=fname,
            movement=movement,
            climb=climb,
            algorithm=algorithm,
            subset_size=subset_size,
        )

        chain_parameters = dict(
            save_fname_facts=save_fname_facts,
            load_fname_facts=load_fname_facts,
            load_fname_rules=load_fname_rules,
            step_by_step=step_by_step,
            facts_amount=points_amount + 1,
            facts_random_order=facts_random_order,
            fname=fname,
        )

        evo.createMaps(**evo_parameters)
        path.findShortestPath(**path_parameters)
        chain.runProduction(**chain_parameters)

        skip_rake = True

        view.createGif(fname, skip_rake, climb)

        with open("cogs/data/test.gif", "rb") as f:
            await ctx.message.channel.send(file=discord.File(f))


def setup(client):
    client.add_cog(Commands(client))
