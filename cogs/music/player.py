import asyncio
import random

from discord.errors import ClientException

from cogs.music.player_view import PlayerView
from cogs.music.source import YTDLSource


class MusicPlayer:
    """A class which is assigned to each guild using the bot for Music.
    This class implements a queue and loop, which allows for different guilds
    to listen to different playlists simultaneously.
    When the bot disconnects from the Voice it's instance will be destroyed.
    """

    __slots__ = (
        "interaction",
        "music",
        "queue",
        "next",
        "np_msg",
        "volume",
        "current_pointer",
        "next_pointer",
        "loop_queue",
        "loop_track",
        "timestamp",
        "view"
    )

    def __init__(self, interaction, music):
        self.interaction = interaction
        self.music = music

        self.queue = []
        self.next = asyncio.Event()

        self.np_msg = None
        self.volume = 0.05
        self.current_pointer = 0
        self.next_pointer = -1
        self.loop_queue = False
        self.loop_track = False

        self.timestamp = 0

        self.view = None

        interaction.client.loop.create_task(self.player_loop())

    async def player_loop(self):
        """Our main player loop."""

        await self.interaction.client.wait_until_ready()

        while not self.interaction.client.is_closed():
            self.next.clear()
            print("1 CLEAR")
            # Log info: Normal flow is going from 1 to 10
            #   (3 if qloop triggered, or no next song; 5 if closing
            # What is regather for? How is it different from create source
            # Cannot we use regather for all so it would be faster?

            try:
                if not self.loop_track:
                    self.next_pointer += 1  # next song
                    print("2 POINTER++")
                if self.next_pointer >= len(self.queue):
                    if self.loop_queue:
                        self.next_pointer = 0  # queue loop
                        print("3 POINTER 0")
                    else:
                        print("3 INTO WAIT")
                        await self.next.wait()
                        print("3 FROM WAIT")
                        self.next.clear()
                        print("3 CLEAR")

                print("4 INTO CURRENT_POINTER UPDATE")
                self.current_pointer = self.next_pointer
                source = self.queue[self.current_pointer]

            except asyncio.TimeoutError:
                print("5 DESTROY")
                return self.destroy(self.interaction.guild)

            if not isinstance(source, YTDLSource):
                # Source was probably a stream (not downloaded)
                # So we should regather to prevent stream expiration

                try:
                    print("6 GOING TO REGATHER")
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
                print("7 TIMESTAMP 0")

            source.volume = self.volume
            try:
                print("8 CALL LOOP THREADSAFE")
                call_next = self.interaction.client.loop.call_soon_threadsafe
                self.interaction.guild.voice_client.play(
                    source,
                    after=lambda _: call_next(self.next.set),
                )
            except (ClientException, AttributeError) as err:
                print(err)
                return

            self.view = PlayerView(self, source)
            print("9 INTO UPDATE MSG")
            await self.update_player_status_message()
            print("10 MSG UPDATED")

    async def update_player_status_message(self):
        if not self.np_msg:  # there is no np msg anywhere
            self.np_msg = await self.interaction.channel.send(
                content=self.view.msg, view=self.view
            )
        elif self.np_msg.channel.last_message_id == self.np_msg.id:  # if np msg is the last one, just update it
            self.np_msg = await self.np_msg.edit(
                content=self.view.msg, view=self.view
            )
        else:  # if there is np_msg but it is not the last one, remove the old one and create a new one
            await self.np_msg.delete()
            self.np_msg = await self.interaction.channel.send(
                content=self.view.msg, view=self.view
            )

        await self.next.wait()


    def shuffle(self):
        """Randomizes the position of tracks in queue."""

        if not self.queue:
            return

        shuffled_remains = self.queue[self.current_pointer + 1 :]
        random.shuffle(shuffled_remains)

        self.queue = (
            self.queue[: self.current_pointer + 1] + shuffled_remains
        )

    def toggle_loop_queue(self):
        """Loops the queue of tracks."""

        self.loop_queue = not self.loop_queue

    def toggle_loop_track(self):
        """Loops the currently playing track."""

        self.loop_track = not self.loop_track

    def destroy(self, guild):
        """Disconnect and cleanup the player."""

        return self.interaction.client.loop.create_task(
            self.music.cleanup(guild)
        )
