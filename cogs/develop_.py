import discord
from discord.ext import commands
import os, random
import json

class Develop(commands.Cog):
    def __init__(self, client):
        self.client = client

    possible_responses = ['That is a resounding no', 'It is not looking likely', 'Too hard to tell', 'It is quite possible', 'Definitely']
    jokes = [line.rstrip('\n') for line in open('data/jokes.txt')]

    @commands.command(brief="Tells a joke about Chuck Norris.")
    async def joke(self, ctx):
        await ctx.send(random.choice(self.jokes))
        
    @commands.command(brief="Answers a yes/no question.++", aliases=['answer', 'question'])
    async def ask(self, ctx):
        " Possible answers are: 'That is a resounding no', 'It is not looking likely', 'Too hard to tell', 'It is quite possible', 'Definitely' "
        await ctx.send(random.choice(self.possible_responses) + ", " + ctx.message.author.mention)

    @commands.command(brief="Chooses an item between given arguments.")
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    @commands.command(brief="Replies specified message.++")
    async def echo(self, ctx, *args):
        ''' For voice put '-v' after echo. E.g. ?echo -v Hello world!'''
        
        if args[0] == '-v':
            await ctx.send(' '.join(args[1:]), tts=True)
        else:
            await ctx.send(' '.join(args)) 

    @commands.command(brief="Logouts bot from the server.")
    async def close(self, ctx):
        await self.client.close()

    @commands.command(brief="Changes the player's volume in percentages.")
    async def volume(self, ctx, volume: int):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))









    @commands.command(brief='Shows all passive functionalities of GLaDOS.')
    async def docs(self, ctx):
        await ctx.send(f"""```
EVENTS:
1. Surveillance - reactions/messages/deletions are posted into surveillance channel ++
2. Bot statuses - changing bot status depending on its activity
3. Nick change - GLaDOS will not allow users to change their nickname into existing ones
4. Welcome - GLaDOS will send welcoming message to the newly joined user
5. WeebCom - GLaDOS will remind you not to post non-command messages in bot channel

COMMANDS:
1. Config - change which actions are being sent into surveillance
2. Bypass - prevent actions being sent to surveillance in certain channels
3. Cogs load - load or unload set of functions
4. VOICE ...

FIXES:
1. Error handles
```""")

    # await member.add_roles(discord.utils.get(member.guild.roles, name='Test subject'))

    
    # add experience for each message user sent
    '''

    # Basic functions
    async def update_data(users, user):
        id = str(user.id)
        if not id in users:
            users[id] = {}
            users[id]['name'] = user.name
            users[id]['experience'] = 0
            users[id]['level'] = 1

    async def add_experience(users, user, exp):
        users[str(user.id)]['experience'] += exp

    async def level_up(users, user, channel):
        id = str(user.id)
        experience = users[id]['experience']
        lvl_start = users[id]['level']
        lvl_end = int(experience ** (1/3))

        if lvl_start < lvl_end:
            await channel.send(f'{user.mention} has leveled up to level {lvl_end}')
            users[id]['level'] = lvl_end

    # ON MESSAGE
    # Update experience
    with open('users.json', 'r') as fopen:
        users = json.load(fopen)
        await update_data(users, message.author)
        await add_experience(users, message.author, 5)
        await level_up(users, message.author, message.channel)
    with open('users.json', 'w') as fopen:
        json.dump(users, fopen)


    # ON MEMBER JOIN
    # Storing user info into database
    with open('users.json', 'r') as f:
        users = json.load(f)
        await update_data(users, member)
    with open('users.json', 'w') as f:
        json.dump(users, f)
    '''


    # TODO: Helping method for stats observing in graphs
    '''
    messages = 0
    async def update_stats():
        await client.wait_until_ready()

        while not client.is_closed():
            try:
                with open("stats.txt", "a") as f:
                    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"Time: {time}, Messages: {messages}\n") #int(time.time())
            except Exception as e:
                print(e)
            await asyncio.sleep(60)

    IN MAIN FUNCTION:
    client.loop.create_task(update_stats())
    '''

def setup(client):
    client.add_cog(Develop(client))