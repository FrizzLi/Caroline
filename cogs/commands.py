import discord, random
from discord.ext import commands

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
    
def setup(client):
    client.add_cog(Commands(client))
