import asyncio

from discord.errors import ClientException

from cogs.music.player_view import PlayerView
from cogs.music.source import YTDLSource


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds
    to listen to different playlists simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    def __init__(self, interaction, music):
        self.interaction = interaction
        self.music = music

        self.queue = []
        self.next = asyncio.Event()

        self.np_msg = None
        self.volume = 0.2
        self.current_pointer = 0
        self.next_pointer = -1
        self.loop_queue = False
        self.loop_track = False

        self.timestamp = 0

        interaction.client.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""

        await self.interaction.client.wait_until_ready()

        while not self.interaction.client.is_closed():
            self.next.clear()

            try:
                if not self.loop_track:
                    self.next_pointer += 1  # next song
                if self.next_pointer >= len(self.queue):
                    if self.loop_queue:
                        self.next_pointer = 0  # queue loop
                    else:
                        await self.next.wait()
                        self.next.clear()

                self.current_pointer = self.next_pointer
                source = self.queue[self.current_pointer]

            except asyncio.TimeoutError:
                return self.destroy(self.interaction.guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration
                try:
                    source = await YTDLSource.regather_stream(
                        source,
                        loop=self.interaction.client.loop,
                        timestamp=self.timestamp,
                    )
                except Exception as err:
                    await self.interaction.channel.send(
                        f"Error:\n```css\n[{err}]\n```"
                    )
                    continue
                self.timestamp = 0

            source.volume = self.volume
            try:
                call_next = self.interaction.client.loop.call_soon_threadsafe
                self.interaction.guild.voice_client.play(
                    source,
                    after=lambda _: call_next(self.next.set),
                )
            except (ClientException, AttributeError) as err:
                print(err)
                return

            view = PlayerView(self, source)
            if not self.np_msg:
                self.np_msg = await self.interaction.channel.send(
                    view.msg, view=view
                )
            elif self.np_msg.channel.last_message_id == self.np_msg.id:
                self.np_msg = await self.np_msg.edit(view.msg, view=view)
            else:
                await self.np_msg.delete()
                self.np_msg = await self.interaction.channel.send(
                    view.msg, view=view
                )

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            try:  # host in replit cannot process cleanup...
                source.cleanup()
            except ValueError as err:
                print(err)

    def destroy(self, guild):
        """Disconnect and cleanup the player."""

        return self.interaction.client.loop.create_task(
            self.music.cleanup(guild)
        )
