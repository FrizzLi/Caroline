import json
import pytz
import discord
from discord.ext import commands
from datetime import datetime
import os


class Surveillance(commands.Cog):
    def __init__(self, client):
        surv_dir = os.path.dirname(os.path.abspath(__file__))
        with open(surv_dir + "\\surv_config.json", "r") as cf:
            config = json.load(cf)

        self.client = client
        self.config = config

    # Helping functions
    def get_timeRole(self, member):
        time = datetime.now(pytz.timezone('Europe/Bratislava')).strftime('%Y-%m-%d %H:%M:%S')
        toprole = '(' + str(member.top_role) + ')' if self.config['logs']['member_role'] == '1' else ''
        return time, toprole
    
    def get_logsChannel(self):
        return self.client.get_channel(self.config['IDs']['logs'])

    async def cond_write(self, msg, member_type):
        if self.config['logs'][member_type] != '0':
            await self.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_message(ctx, message):
        # await ctx.client.process_commands(message)

        # Dont read bot's messages
        if "Skynet" in [y.name for y in message.author.roles]:
            return

        if not message.content:  # can happen on on_member_join
            return

        # Surveillance posting
        time, topRole = ctx.get_timeRole(message.author)
        msg = f'{time}: {message.author.name}{topRole} sent "{message.content}" to {message.channel}.'

        if ctx.config['logs']['msg_post'] == '1' and message.channel.name not in ctx.config['bypass_channels']:
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_message_delete(ctx, message):
        if "Skynet" in [y.name for y in message.author.roles]:  # dont read bot's action
            return
        if ctx.get_logsChannel() == message.channel:               # dont read actions in log channel
            return
        if message.channel.name in ctx.config['bypass_channels']:  # config restriction
            return

        time, topRole = ctx.get_timeRole(message.author)
        msg = f'{time}: {message.author.name}\'s{topRole} message "{message.content}" was deleted in {message.channel}.'

        if ctx.config['logs']['msg_delete'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_message_edit(ctx, before, after):
        if "Skynet" in [y.name for y in after.author.roles]:
            return
        if after.channel.name in ctx.config['bypass_channels']:
            return

        time, topRole = ctx.get_timeRole(after.author)
        msg = f'{time}: {after.author.name}{topRole} has edited message "{before.content}" to "{after.content}" in {after.channel}.'

        if ctx.config['logs']['msg_edit'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_typing(ctx, channel, user, when):
        if channel.name in ctx.config['bypass_channels']:
            return

        time, topRole = ctx.get_timeRole(user)
        msg = f'{time}: {user.name}{topRole} is typing into {channel}.'

        if ctx.config['logs']['on_typing'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_reaction_add(ctx, reaction, user):
        if reaction.message.channel.name in ctx.config['bypass_channels']:
            return

        time, topRole = ctx.get_timeRole(user)
        msg = f'{time}: {user.name}{topRole} has added {reaction.emoji} to {reaction.message.author.name}\'s{topRole} "{reaction.message.content}" in {reaction.message.channel}.'

        if ctx.config['logs']['reaction_add'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_reaction_remove(ctx, reaction, user):
        if reaction.message.channel.name in ctx.config['bypass_channels']:
            return

        time, topRole = ctx.get_timeRole(user)
        msg = f'{time}: {user.name}{topRole} has removed {reaction.emoji} from {reaction.message.author.name}\'s{topRole} "{reaction.message.content}" in {reaction.message.channel}.'

        if ctx.config['logs']['reaction_remove'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_member_join(ctx, member):
        role = discord.utils.get(ctx.client.guilds[0].roles, name="Member")
        await member.add_roles(role)

        time, topRole = ctx.get_timeRole(member)
        msg = f'{time}: {member.name}{topRole} has joined this server.'

        if ctx.config['logs']['member_join'] != '0':
            await ctx.get_logsChannel().send(msg)

    @commands.Cog.listener()
    async def on_member_remove(ctx, member):
        time, topRole = ctx.get_timeRole(member)
        msg = f'{time}: {member.name}{topRole} has left this server.'

        if ctx.config['logs']['member_remove'] != '0':
            await ctx.get_logsChannel().send(msg)

    ##################################
    @commands.Cog.listener()
    async def on_member_update(ctx, before, after):
        time, topRole = ctx.get_timeRole(after)
        if topRole == "(@everyone)":
            return

        # do not allow users to change nicknames into already existing ones
        if before.nick != after.nick:
            if after.nick and discord.utils.get(after.guild.members, name=after.display_name):
                await after.edit(nick=(before.display_name + '_stop'))
            if not after.nick:
                await ctx.cond_write(f'{time}: {before.name}{topRole} has changed his nick to {after.name}.', 'member_update')
            else:
                await ctx.cond_write(f'{time}: {before.name}{topRole} has changed his nick to {after.nick}.', 'member_update')
        if (before.status == discord.Status.offline) and after.status != discord.Status.offline:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has come online.', 'member_update')
        if (before.status == discord.Status.idle) and after.status != discord.Status.idle:
            await ctx.cond_write(f'{time}: {after.name}{topRole} is no longer idle.', 'member_update')
        if (before.status != discord.Status.dnd) and after.status == discord.Status.dnd:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has set DND status.', 'member_update')
        if (before.status == discord.Status.dnd) and after.status != discord.Status.dnd:
            await ctx.cond_write(f'{time}: {after.name}{topRole} is no longer DND.', 'member_update')
        if (before.status != discord.Status.idle) and after.status == discord.Status.idle:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has gone idle.', 'member_update')
        elif before.activity != after.activity and after.activity == None:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has stopped {before.activity.name}.', 'member_update')
        elif before.activity != after.activity and before.activity == None:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has started {after.activity.name}.', 'member_update')
        if (before.status != discord.Status.offline) and after.status == discord.Status.offline:
            await ctx.cond_write(f'{time}: {after.name}{topRole} has gone offline.', 'member_update')

    @commands.Cog.listener()
    async def on_voice_state_update(ctx, member, before, after):
        time, topRole = ctx.get_timeRole(member)

        if ((before.deaf == False) and after.deaf) or ((before.self_deaf == False) and after.self_deaf):
            await ctx.cond_write(f'{time}: {member.name}{topRole} has been deafened.', 'member_voice')
        elif ((before.deaf == True) and not after.deaf) or ((before.self_deaf == True) and not after.self_deaf):
            await ctx.cond_write(f'{time}: {member.name}{topRole} has been undeafened.', 'member_voice')
        elif ((before.mute == False) and after.mute) or ((before.self_mute == False) and after.self_mute):
            await ctx.cond_write(f'{time}: {member.name}{topRole} has been muted.', 'member_voice')
        elif ((before.mute == True) and not after.mute) or ((before.self_mute == True) and not after.self_mute):
            await ctx.cond_write(f'{time}: {member.name}{topRole} has been unmuted.', 'member_voice')
        elif (before.self_video == False) and after.self_video:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has started broadcasting a video.', 'member_voice')
        elif (before.self_video == True) and not after.self_video:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has stopped broadcasting a video.', 'member_voice')
        elif (before.afk == False) and after.afk:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has gone afk.', 'member_voice')
        elif (before.afk == True) and not after.afk:
            await ctx.cond_write(f'{time}: {member.name}{topRole} is no longer afk.', 'member_voice')
        elif before.channel != after.channel and after.channel == None:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has left {before.channel} channel.', 'member_voice')
        elif before.channel != after.channel and before.channel == None:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has joined {after.channel} channel.', 'member_voice')
        elif before.channel != after.channel:
            await ctx.cond_write(f'{time}: {member.name}{topRole} has moved from {before.channel} channel into {after.channel}.', 'member_voice')


    ### Main commands ###
    @commands.is_owner()
    @commands.command(brief="Bypass surveillance settings.++")
    async def bypass(self, ctx, channel=None, val=None):
        ''' "?bypass <channel_name> 1" - adds channel for bypassing
        "?bypass <channel_name> 0" - removes channel from bypassing'''

        if channel and val:
            val = "1" if val != "0" else "0"
            if val == "1" and channel in self.config['bypass_channels']:
                return await ctx.send(f'"{channel}" channel is already being bypassed!')
            elif val == "0" and channel not in self.config['bypass_channels']:
                return await ctx.send('"{}" channel isnt bypassed!'.format(channel))

            if val != "0":
                self.config['bypass_channels'].append(channel)
                msg = f'{channel} channel is now being untracked.'
            else:
                self.config['bypass_channels'].remove(channel)
                msg = f'{channel} channel is now being tracked.'

            surv_dir = os.path.dirname(os.path.abspath(__file__))
            with open(surv_dir + "\\surv_config.json", 'w') as f4:
                json.dump(self.config, f4, sort_keys=True, indent=4)
            await self.get_logsChannel().send(msg)
            return await ctx.send(msg)

        else:  # display current bypass settings
            embed = discord.Embed(colour=discord.Colour.blue())
            embed.add_field(name='Bypass configuration', value=self.config['bypass_channels'])
            return await ctx.send(embed=embed)

    @commands.command(brief="Surveillance settings properties.++")
    async def configure(self, ctx, action=None, val=None):
            ''' "?configure" - shows current settings
    "?configure on_typing 1" - turns on tracking for typing into channels
    "?configure on_typing 0" - turns off tracking for typing into channels

    Types of actions: 
    msg_post (when somebody sends a message), 
    msg_delete (somebody deletes a message), 
    msg_edit (somebody edits a message), 
    on_typing (somebody starts writing into channel), 
    reaction_add (somebody adds a reaction to message), 
    reaction_remove (somebody removes a reaction from message), 
    member_join (somebody has joined the server), 
    member_remove (somebody has left the server), 
    member_update (nick change, on/off, dnd, idle, activity), 
    member_voice (deaf, mute, broadcast, afk, join/move voice channel),
    member_role (shows user's role after name)'''

            if action and val:
                val = "1" if val != "0" else "0"
                if action not in self.config['logs']:
                    return await ctx.send(f"{action} doesnt exist in logs configuration.")
                elif val == self.config['logs'][action]:
                    track = "untracked" if val == "0" else "tracked"
                    return await ctx.send(f"{action} action is already being {track}.")

                self.config['logs'][action] = val
                surv_dir = os.path.dirname(os.path.abspath(__file__))
                with open(surv_dir + "\\surv_config.json", 'w') as fopen:
                    json.dump(self.config, fopen, sort_keys=True, indent=4)
                track = "untracked" if val == "0" else "tracked"
                msg = f'{action} action is now being {track}'
                await self.get_logsChannel().send(msg)
                await ctx.send(msg)
            else:
                embed = discord.Embed(
                    title = 'Surveillance configuration',
                    #description = 'To This is a description',
                    colour = discord.Colour.blue()
                )
                #embed.set_footer(text='This is a footer.')
                #embed.set_image(url='')
                #embed.set_thumbnail(url='')
                #embed.set_author(name='Author Name') #icon_url
                for action in self.config['logs']:
                    embed.add_field(name=action, value=self.config['logs'][action])
                await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Surveillance(client))

# NotImplemented
# TODO: Helping method for stats observing in graphs
"""
messages = 0
async def update_stats():
    await client.wait_until_ready()

    while not client.is_closed():
        try:
            with open("stats.txt", "a") as f:
                time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"Time: {time},
                Messages: {messages}\n") #int(time.time())
        except Exception as e:
            print(e)
        await asyncio.sleep(60)

IN MAIN FUNCTION:
client.loop.create_task(update_stats())
"""

# add experience for each message user sent
"""

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
        await channel.send(f'{user.mention}
        has leveled up to level {lvl_end}')
        users[id]['level'] = lvl_end

# ON MESSAGE
# Update experience
with open('users.json', 'r') as fopen:
    users = json.load(fopen)
    await update_data(users, message.author)
    await add_experience(users, message.author, 5)
    await level_up(users, message.author, message.channel)
with open('users.json', 'w') as fopen:
    json.dump(users, fopen) #### WATCH THE PATH


# ON MEMBER JOIN
# Storing user info into database
with open('users.json', 'r') as f:
    users = json.load(f)
    await update_data(users, member)
with open('users.json', 'w') as f:
    json.dump(users, f) #### WATCH THE PATH
"""

