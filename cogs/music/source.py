import functools
import asyncio
import youtube_dl
import discord


# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''

ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdlopts)


class YTDLSource(discord.PCMVolumeTransformer):

    def __init__(self, source, *, data, requester):
        super().__init__(source)
        self.requester = requester

        self.title = data.get('title')
        self.web_url = data.get('webpage_url')
        self.duration = self._get_readable_duration(data.get('duration'))
        self.view_count = data.get('view_count')

    def __getitem__(self, item: str):
        """Allows us to access attributes similar to a dict.
        This is only useful when you are NOT downloading.
        """
        return self.__getattribute__(item)

    def _get_readable_duration(self, duration):
        """Get duration in hours, minutes and seconds."""

        m, s = divmod(duration, 60)
        h, m = divmod(m, 60)
        h = (f'{int(h)}h' if h else '')
        m = (' ' if h and m else '') + (f'{int(m)}m' if m else '')
        s = (' ' if h or m else '') + (f'{int(s)}s' if s else '')
        duration = h + m + s

        return duration

    @classmethod
    async def create_source(cls, interaction, search: str, *, loop, download=False):
        loop = loop or asyncio.get_event_loop()

        to_run = functools.partial(ytdl.extract_info, url=search, download=download)
        data = await loop.run_in_executor(None, to_run)

        if 'entries' in data:
            if len(data['entries']) == 1:  # for search single song
                data['title'] = data['entries'][0]['title']
                data['webpage_url'] = data['entries'][0]['webpage_url']
        else:  # for URL single song
            data['entries'] = [data]

        description = f"Queued [{data['title']}]({data['webpage_url']}) [{interaction.user.mention}]"
        embed = discord.Embed(title="", description=description, color=discord.Color.green())
        await interaction.followup.send(embed=embed)

        # TODO: resolve download
        if download:
            source = ytdl.prepare_filename(data['entries'])
        else:
            return data['entries']

        return cls(discord.FFmpegPCMAudio(source), data=data['entries'], requester=interaction.user)

    @classmethod
    async def regather_stream(cls, data, *, loop):
        """Used for preparing a stream, instead of downloading.
        Since Youtube Streaming links expire."""

        loop = loop or asyncio.get_event_loop()
        requester = data['requester']

        to_run = functools.partial(ytdl.extract_info, url=data['webpage_url'], download=False)
        data = await loop.run_in_executor(None, to_run)

        return cls(discord.FFmpegPCMAudio(data['url']), data=data, requester=requester)