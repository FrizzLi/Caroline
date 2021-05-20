import os
import random
import glob
import discord
import youtube_dl

from discord.ext import commands
from discord.utils import get, find
from mutagen.mp3 import MP3
from typing import Any


class Voice(commands.Cog):
    def __init__(self, client):
        self.client = client

    queuer = []  # type: Any
    pointer = -1
    loop_queue = False
    loop_track = False
    jump_index = 0
    voluming = 0.1

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    ffmpeg_options = {"options": "-vn"}

    def replaceChars(self, track):
        track = track.replace('"', "'")
        for char in "\\/:*?<>|":
            track = track.replace(char, "_")

        return track

    def downloadAudio(self, query):
        try:  # youtube source
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:

                # get query title info (song/playlist name)
                if not query[0].startswith("https"):
                    ydl.params["noplaylist"] = True
                    extract_query = "ytsearch1:" + " ".join(query)
                    info = ydl.extract_info(extract_query, download=False)
                    title = info["entries"][0]["title"]
                else:
                    ydl.params["noplaylist"] = False
                    info = ydl.extract_info(query[0], download=False)
                    title = info["title"]

                title = self.replaceChars(
                    title
                )  # for special characters that cannot be saved

                # get local existing titles
                playlist = info["webpage_url_basename"] == "playlist"
                voice_dir = os.path.dirname(os.path.abspath(__file__))
                if playlist:
                    dest = title
                    audio_paths = voice_dir + "\\audio\\*"
                else:
                    dest = "singles"
                    audio_paths = voice_dir + "\\audio\\singles\\*.mp3"
                paths = glob.glob(audio_paths)
                titles = [os.path.basename(full_path) for full_path in paths]

                # download title if it doesnt exist
                if not (title + ".mp3") in titles:
                    dl_path = f"{voice_dir}\\audio\\{dest}\\%(title)s.%(ext)s"
                    ydl.params["outtmpl"] = dl_path
                    ydl.extract_info(info["webpage_url"], download=True)

        except Exception:  # TODO: spotify source
            pass
            """
            url_str = " ".join(query)
            list_type = 'album' if 'album' in url_str else ''
            list_type = 'playlist' if 'playlist' in url_str else list_type
            playlist = True if list_type else False
            if list_type:
                # download list into text file and get its title
                os.system(f"spotdl --{list_type} {url_str}")
                paths = glob.glob("*")
                latest = max(paths, key=os.path.getctime)
                title = latest[:-4]

                # download if title doesnt exist
                paths = glob.glob("audio/*")
                dirs = [os.path.basename(path) for path in paths]
                if not title in dirs:
                    path = f"audio\\{title}"
                    q = f"spotdl --list={latest} -f {path} --overwrite skip"
                    os.system(q)
                os.remove(latest)

            else:
                # download the track
                name_format = '"' + "{artist} - {track_name}" + '"'
                path = f"audio\\DOWNLOAD"
                os.system(f"spotdl -ff {name_format} -f {path} -s \
                    {url_str} --overwrite skip")

                # get name of the downloaded track
                paths = glob.glob(f"{path}/*.mp3")
                latest = max(paths, key=os.path.getctime)
                title = os.path.basename(latest)[:-4]
            """

        return title, playlist

    def setQueue(self, query):
        voice_dir = os.path.dirname(os.path.abspath(__file__))

        # get audio path from local
        if query[0][0] == "-":
            title = query[0][1:]
            audio_paths = glob.glob(f"{voice_dir}\\audio\\{title}\\*.mp3")
            audio_paths.sort(key=lambda x: os.path.getctime(x))
            try:
                index = int(query[1])
                audio_paths = [audio_paths[index - 1]]
                title = os.path.basename(audio_paths[0])[:-4]
            except IndexError:
                pass

        # download audio and get its path
        elif query[0][0] == "+":
            title, playlist = self.downloadAudio(query)
            if playlist:
                audio_paths = f"{voice_dir}\\audio\\{title}\\*.mp3"
            else:
                audio_paths = f"{voice_dir}\\audio\\*\\{title}.mp3"
            audio_paths = glob.glob(audio_paths)
            audio_paths.sort(key=lambda x: os.path.getctime(x))

        # TODO: stream audio and get its URL
        else:
            with youtube_dl.YoutubeDL(self.ydl_opts) as ydl:
                # get query title info (song/playlist name)
                if not query[0].startswith("https"):
                    ydl.params["noplaylist"] = True
                    extract_query = "ytsearch1:" + " ".join(query)
                    info = ydl.extract_info(extract_query, download=False)
                    title = info["entries"][0]["title"]
                else:
                    ydl.params["noplaylist"] = False
                    info = ydl.extract_info(query[0], download=False)
                    title = info["title"]
                if "entries" in info:
                    audio_paths = [en["webpage_url"] for en in info["entries"]]
                else:
                    audio_paths = [info["webpage_url"]]

        # set queuer
        for full_path in audio_paths:
            self.queuer.append(full_path)

        return title

    @commands.command(aliases=["p"], brief="Adds track to queue from ytb/spt.")
    async def play(self, ctx, *query: str):

        # queue playing loop
        def check_queue():
            if not self.loop_track:
                self.pointer += 1  # next
            if self.jump_index:
                self.pointer = self.jump_index - 1  # jump
            if self.loop_queue and len(self.queuer) < self.pointer + 1:
                self.pointer = 0  # repeat queue
            if len(self.queuer) > self.pointer:
                track_path = self.queuer[self.pointer]  # play
                voice.play(
                    discord.FFmpegPCMAudio(
                        track_path, executable="C:/ffmpeg/ffmpeg.exe"
                    ),
                    after=lambda e: check_queue(),
                )
                voice.source = discord.PCMVolumeTransformer(voice.source)
                voice.source.volume = self.voluming
            else:  # end
                self.pointer = -1
                self.queuer.clear()
            self.jump_index = 0

        # get audio and set the queue
        async with ctx.typing():
            title = self.setQueue(query)
        await ctx.send(f"{title} has been added to the queue.")

        # go to playing loop if there isnt song being played/paused
        voice = get(self.client.voice_clients, guild=ctx.guild)

        # need the streaming tho!
        if not voice.is_playing() and not voice.is_paused():
            check_queue()

    @commands.command(aliases=["q"], brief="Displays queue list of tracks.")
    async def queue(self, ctx):
        track_list = []
        start = 1
        if self.pointer > 2 and len(self.queuer) > 10:
            start = len(self.queuer[self.pointer - 2 : self.pointer + 8])
            start += self.pointer - 11

        for index, track_path in enumerate(
            self.queuer[start - 1 : start + 9], start=start
        ):
            pointer = "---> " if self.pointer + 1 == index else "     "
            audio_name = os.path.basename(track_path)[:-4]
            audio_length = MP3(track_path).info.length
            minutes = f"{str(int(audio_length // 60))}m"
            seconds = f"{str(int(audio_length % 60))}s"
            audio_length = f"({minutes}m {seconds}s)"
            row = f"{str(pointer)}{str(index)}. {audio_length} {audio_name}"
            track_list.append(row)

        queue_view = "\n".join(track_list)
        remains = len(self.queuer[start + 9 :])
        remains = f"{remains} remaining track(s)    " if remains else ""
        vol = f"volume: {str(int(self.voluming * 100))}%"
        loop_q = f"loopqueue: {str(self.loop_queue)}"
        loop_t = f"looptrack: {str(self.loop_track)}"
        msg = f"ml\n{queue_view}\n\n{remains}{vol}    {loop_q}    {loop_t}\n"
        await ctx.send(f"```{msg}```")

    @commands.command(brief="Connects/moves the bot to voice channel.")
    async def join(self, ctx, *, name=None):
        author_channel = ctx.message.author.voice.channel
        channel = (
            find(lambda r: r.name == name, ctx.guild.channels)
            if name
            else author_channel
        )
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if not voice:
            await channel.connect()
            await ctx.send(f"Joined {channel}.")
        elif voice.channel == channel:
            await ctx.send("I'm already there.")
        else:
            await voice.move_to(channel)
            await ctx.send(f"Moved from {voice.channel} to {channel}.")

    @commands.command(brief="Disconnects the bot from voice channel.")
    async def leave(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if not voice:
            return await ctx.send("Not connected to voice channel.")
        self.queuer.clear()
        self.loop_queue = False
        voice.stop()
        await voice.disconnect()
        await ctx.send(f"Left {voice.channel}.")

    @commands.command(brief="Pauses currently playing track.")
    async def pause(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_playing():
            voice.pause()
            return await ctx.send("Track is paused.")
        await ctx.send("There is no track being played.")

    @commands.command(brief="Resumes paused track.")
    async def resume(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if voice.is_paused():
            voice.resume()
            return await ctx.send("Track is resumed.")
        await ctx.send("There is no track paused.")

    @commands.command(brief="Stops current playing track and clears queue.")
    async def stop(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        self.queuer.clear()
        self.loop_queue = False
        voice.stop()
        return await ctx.send("Track is stopped and queue is cleared.")

    @commands.command(aliases=["next"], brief="Jump to next/specific track.")
    async def jump(self, ctx, index=None):
        if index:
            self.jump_index = int(index)
            track = os.path.basename(self.queuer[self.jump_index - 1])
            msg = f"Jumping into {self.jump_index}. track ({track[:-4]})."
        else:
            msg = "Skipping current track."
        await ctx.send(msg)
        get(self.client.voice_clients, guild=ctx.guild).stop()

    @commands.command(brief="Check or change the current volume. [%]")
    async def volume(self, ctx, vol=None):
        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")
        if vol:
            self.voluming = int(vol) / 100
            ctx.voice_client.source.volume = self.voluming
            msg = f"Volume changed to {int(self.voluming * 100)}%."
        else:
            msg = f"Volume: {int(self.voluming * 100)}%"
        await ctx.send(msg)

    @commands.command(brief="Randomizes the position of tracks in queue.")
    async def shuffle(self, ctx):
        shuffled_remains = self.queuer[self.pointer + 1 :]
        random.shuffle(shuffled_remains)
        self.queuer = self.queuer[: self.pointer + 1] + shuffled_remains
        return await ctx.send(
            "Position of remaning audio tracks in queue have been shuffled."
        )

    @commands.command(brief="Loops the whole queue of tracks.")
    async def loopqueue(self, ctx):
        if self.loop_queue:
            self.loop_queue = False
            await ctx.send("queue looping is stopped.")
        else:
            self.loop_queue = True
            await ctx.send("Looping queue.")

    @commands.command(brief="Loops the currently playing track.")
    async def looptrack(self, ctx):
        if self.loop_track:
            self.loop_track = False
            await ctx.send("Track looping is stopped.")
        else:
            self.loop_track = True
            await ctx.send("Looping current track.")

    @commands.command(
        aliases=["dl"], brief="DLs a track/playlist from ytb/spt URL. {URL}"
    )
    async def download(self, ctx, url):
        if not url.startswith("https"):
            return await ctx.send("Use web URL to download a song/playlist.")
        async with ctx.typing():
            title, playlist = self.downloadAudio((url,))
            dir_name = title if playlist else "DOWNLOAD"
        await ctx.send(
            f'{title} has been downloaded to "{dir_name}" directory.'
        )

    @commands.command(
        brief="Displays page of 10 tracks in directory. [dir_name] [page_num]"
    )
    async def view(self, ctx, dir_name="DOWNLOAD", page_num=1):
        if not os.path.exists(f"audio/{dir_name}"):
            return await ctx.send(f"{dir_name} directory does not exist.")

        dirs = ""
        if dir_name == "DOWNLOAD":
            dirs = (
                "Available Directories: "
                + ", ".join(os.listdir("audio"))
                + "\n\n"
            )
        page_num = (page_num - 1) * 10
        page_track = []
        tracks = glob.glob(f"audio/{dir_name}/*.mp3")
        tracks.sort(key=lambda x: os.path.getctime(x))
        for index, track_path in enumerate(
            tracks[page_num : page_num + 10], start=page_num + 1
        ):
            # TODO: This should be in function, its used elsewhere too!
            audio_name = os.path.basename(track_path)[:-4]
            audio_length = MP3(track_path).info.length
            minutes = f"{str(int(audio_length // 60))}m"
            seconds = f"{str(int(audio_length % 60))}s"
            audio_length = f"({minutes}m {seconds}s)"
            row = f"{str(index)}. {audio_length} {audio_name}"
            page_track.append(row)

        page_view = "\n".join(page_track)
        remains = len(tracks[page_num + 10 :])
        remains = f"{remains} remaining audio track(s)    " if remains else ""
        msg = f"ml\n{dirs}Directory: {dir_name}\n{page_view}\n\n{remains}\n"
        await ctx.send(f"```{msg}```")

    """
    @commands.command(aliases=['del'], brief="Deletes directory. {dir_name}")
    async def zdelete(self, ctx, dir_name): # same user who created it
        if not os.path.exists(f'audio/{dir_name}'):
            return await ctx.send(f"{dir_name} directory does not exist.")

        dir_tracks = os.listdir(f'audio/{dir_name}')
        for track_path in self.queuer:
            audio_name = os.path.basename(os.path.normpath(track_path))
            if audio_name in dir_tracks:
                return await ctx.send(f"Track from {dir_name} is in queue!
                Clear the queue first.") # bug when two folders have same name

        shutil.rmtree(f"audio/{dir_name}", ignore_errors=True)
        await ctx.send(f"{dir_name} directory has been deleted.")
    """

    @queue.before_invoke
    @pause.before_invoke
    @resume.before_invoke
    @stop.before_invoke
    @jump.before_invoke
    @volume.before_invoke
    @shuffle.before_invoke
    @loopqueue.before_invoke
    @looptrack.before_invoke
    async def ensure_voice(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if not voice:
            await ctx.send("Not connected to voice channel.")
            raise commands.CommandError("Not connected to voice channel.")
        elif not self.queuer:
            await ctx.send("There are no queued songs.")
            raise commands.CommandError("Queue is empty.")

    @play.before_invoke
    async def ensure_voice_play(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        user_voice = ctx.message.author.voice
        if not voice and not user_voice:
            await ctx.send("No bot nor you is connected.")
            raise commands.CommandError("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()

    # @zdelete.before_invoke
    @view.before_invoke
    @download.before_invoke
    async def ensure_dldir(self, ctx):
        if not os.path.exists("audio"):
            os.mkdir("audio")
            os.mkdir("audio/DOWNLOAD")
        elif not os.path.exists("audio/DOWNLOAD"):
            os.mkdir("audio/DOWNLOAD")

    @commands.command(
        brief="Brackets represent inputs. {} is mandatory, [] is optional.++"
    )
    async def HELP(self, ctx):
        await ctx.send(
            """```More facts about "play" command:
Instead of URL you can put search query as well.
The next two example commands have the same outcome:
    play https://www.youtube.com/watch?v=89kTb73csYg
    play forever young blackpink practice

Can be also used to play local files.
Example to play 2. track from directory named "DOWNLOAD":
    play -DOWNLOAD 2
```"""
        )


def setup(client):
    client.add_cog(Voice(client))


# ctx.voice_client vs get(self.client.voice_clients, guild=ctx.guild)
