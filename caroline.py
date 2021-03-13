import os, json, discord
from discord.ext import commands

with open('config.json', 'r') as f:
    gconfig = json.load(f)
client = commands.Bot(command_prefix=gconfig["prefix"])

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('BadArgument! [{}]'.format(error))
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send('MissingRequiredArgument! [{}]'.format(error))
    else:
        await ctx.send(error)

### Event and surveillance functions ###
@client.event
async def on_ready():
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=f'{gconfig["prefix"]}help'))
    print("Logged in as", client.user.name, "with", discord.__version__, 'version.')

### Main commands ###
@client.command(brief=[f for f in os.listdir("cogs") if f.endswith('.py')])
async def load(ctx, cog: str):
    try:
        client.load_extension(f'cogs.{cog}')
        await ctx.send('Loaded cog: {}'.format(cog))
    except Exception as error:
        await ctx.send('{} cannot be loaded. [{}]'.format(cog, error))

@client.command()
async def unload(ctx, cog: str):
    try:
        client.load_extension(f'cogs.{cog}')
        client.unload_extension(f'cogs.{cog}')
        await ctx.send('Unloaded cog: {}'.format(cog))
    except Exception as error:\
        await ctx.send('{} cannot be unloaded. [{}]'.format(cog, error))

if __name__ == '__main__':
    for file in os.listdir("cogs"):
        if file.endswith("_.py"):
            continue
        elif file.endswith(".py"):
            try:
                client.load_extension(f"cogs.{file.replace('.py','')}")
                print(f'{file} module has been loaded.')
            except Exception as e:
                print(f'{file} module cannot be loaded. [{e}]')

    client.run("NjU1NDYwOTE1MjgxNjU3ODc3..XfUbjA..tvHJtxhSBQ3tBuv6v_DBQFBrNA8")

# NOTE: Test scenarios for audio download: Youtube song, Youtube playlist, Spotify song, Spotify playlist, Youtube song dl while playing, Youtube playlist dl while playing, Spotify song dl while playing, Spotify playlist dl while playing, ALSO WANT STREAMING MUSIC!
