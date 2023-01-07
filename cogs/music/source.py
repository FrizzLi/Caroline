import asyncio
import functools

import discord
import youtube_dl

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ""

ytdlopts = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",  # ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdlopts)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get("title")
        self.web_url = data.get("webpage_url")
        self.duration = data.get("duration")
        self.view_count = data.get("view_count")

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    @classmethod
    async def create_source(
        cls, interaction, search: str, *, loop, playlist=False
    ):
        loop = loop or asyncio.get_event_loop()

        to_run = functools.partial(
            ytdl.extract_info, url=search, download=False
        )
        data = await loop.run_in_executor(None, to_run)

        if "entries" in data:
            if len(data["entries"]) == 1:  # for search single song
                data["title"] = data["entries"][0]["title"]
                data["webpage_url"] = data["entries"][0]["webpage_url"]
        else:  # for URL single song
            data["entries"] = [data]

        # hackis, need to resolve DL
        if not playlist:
            titled_url = f"[{data['title']}]({data['webpage_url']})"
            description = f"Queued {titled_url} [{interaction.user.mention}]"
            embed = discord.Embed(
                title="", description=description, color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)

        return data["entries"]

    @classmethod
    async def search_source(cls, search: str, *, loop):
        loop = loop or asyncio.get_event_loop()

        to_run = functools.partial(
            ytdl.extract_info, url="ytsearch10: " + search, download=False
        )
        data = await loop.run_in_executor(None, to_run)

        return data["entries"]

    @classmethod
    async def regather_stream(cls, data, *, loop, timestamp=0):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""

        loop = loop or asyncio.get_event_loop()
        requester = data["requester"]

        to_run = functools.partial(
            ytdl.extract_info, url=data["webpage_url"], download=False
        )
        data = await loop.run_in_executor(None, to_run)

        # set timestamp for last 5 seconds if set too high
        if data["duration"] < timestamp + 5:
            timestamp = data["duration"] - 5
        reconnect_streamed = "-reconnect 1 -reconnect_streamed 1"
        reconnect_delay = "-reconnect_delay_max 5"
        ffmpeg_opts = {
            "options": f"-vn -ss {timestamp}",
            "before_options": f"{reconnect_streamed} {reconnect_delay}",
        }

        return cls(
            discord.FFmpegPCMAudio(
                data["url"],
                **ffmpeg_opts,
                executable="C:/ffmpeg/ffmpeg.exe",
            ),
            data=data,
            requester=requester,
        )
