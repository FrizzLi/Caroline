import os

import discord


class SharedUtils(discord.ext.commands.Cog):
    """Represents cog extension that tracks activity on all voice channels
    and also allows us to run Python code.

    Args:
        commands (discord.ext.commands.cog.CogMeta): class that is taken to
            create subclass - our own customized cog module
    """

    def __init__(self, bot):
        self.bot = bot


    @discord.ext.commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Leave the channel when all the other members leave.

        Args:
            member (discord.member.Member): the bot
            before (discord.member.VoiceState): state before certain
                (anyone's) action [unused]
            after (discord.member.VoiceState): state after certain
                (anyone's) action [unused]
        """

        voice_state = member.guild.voice_client
        if not voice_state:
            return
        members_amount = len(voice_state.channel.members)

        # Checks if the bot is connected in the voice channel and
        # whether theres only 1 member connected to it (the bot itself)
        if voice_state is not None and members_amount == 1:
            try:
                await member.guild.voice_client.disconnect()
            except AttributeError:
                pass

    @discord.app_commands.command()
    async def join(
        self, interaction, *, channel: discord.VoiceChannel = None
    ):
        """Connect to voice.
        This command also handles moving the bot to different channels.

        Args:
            channel: discord.VoiceChannel [Optional]
                The channel to connect to. If a channel is not specified,
                an attempt to join the voice channel you are in will be made.
        """

        if channel is None:
            try:
                channel = interaction.user.voice.channel
            except AttributeError:
                msg = "Specify voice channel or join one first."
                return await interaction.response.send_message(msg)

        vc = interaction.guild.voice_client
        if vc:
            if vc.channel.id == channel.id:
                msg = "I'm already in the channel."
                return await interaction.response.send_message(msg)
            try:
                await vc.move_to(channel)
                embed = discord.Embed(
                    description=f"Moved to channel: **{channel}**.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except TimeoutError:
                msg = f"Moving to channel: <{channel}> timed out."
                await interaction.response.send_message(msg)
        else:
            try:
                await channel.connect()
                embed = discord.Embed(
                    description=f"Connected to channel: **{channel}**.",
                    color=discord.Color.green(),
                )
                await interaction.response.send_message(embed=embed)
            except TimeoutError:
                msg = f"Connecting to channel: <{channel}> timed out."
                await interaction.response.send_message(msg)

    @discord.app_commands.command()
    async def leave(self, interaction):
        """Stop the currently playing song, clears queue and disconnects from
        voice.
        """

        voice = discord.utils.get(
            self.bot.voice_clients, guild=interaction.guild
        )
        # vc = interaction.guild.voice_client
        if not voice:
            msg = "I'm not connected to a voice channel."
            return await interaction.response.send_message(msg)

        try:
            await interaction.guild.voice_client.disconnect()
        except AttributeError:
            pass

        embed = discord.Embed(
            description=f"Left **{voice.channel.name}** channel.",
            color=discord.Color.green(),
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        SharedUtils(bot), guilds=[discord.Object(id=os.environ["GUILD_ID"])]
    )
