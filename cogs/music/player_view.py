from timeit import default_timer

import discord
from discord.ui import Button, Select, View


def get_readable_duration(duration):
    """Get duration in hours, minutes and seconds."""

    m, s = divmod(int(duration), 60)
    h, m = divmod(m, 60)

    if h:
        duration = f"{h}:{m:02d}:{s:02d}"
    else:
        duration = f"{m}:{s:02d}"

    return duration


class SearchSelect(Select):
    def __init__(self, player):
        super().__init__()
        self.player = player

    async def callback(self, interaction):
        await self.player.music.play(interaction, self.values[0])


class SearchView(View):
    def __init__(self, player, tracks):
        super().__init__(timeout=None)
        self.msg = "Choose a track!"
        self.add_item(self.add_selection(tracks, player))

    def add_selection(self, tracks, player):
        selection = SearchSelect(player)

        # above 25: raises maximum number of options already provided
        for track in tracks[-25:]:
            selection.add_option(
                label=track["title"],
                description=get_readable_duration(track["duration"]),
                value=track["webpage_url"],
            )
        return selection


class PlayerView(View):
    def __init__(self, player, source):
        super().__init__(timeout=None)
        self.add_item(
            Button(
                label="Current playing track link", url=source["webpage_url"], row=1
            )
        )
        self.player = player
        self.source = source
        self.start = default_timer()
        self.pause_ts = 0
        self.update_msg()

    def update_msg(self):
        self.msg = self.generate_message()

    def generate_message(self):
        """Display information about player and queue of songs."""

        tracks, remains, volume, loop_q, loop_t = self._get_page_info()
        paused = self.children[0].emoji.name == '▶️'
        end = self.pause_ts if paused else default_timer()
        dur_total = self.source.duration
        dur_total = get_readable_duration(dur_total)
        dur_total = "0:00:00" if dur_total.startswith("-") else dur_total
        dur_curr = end - self.start + self.player.seek_sec
        dur_curr = get_readable_duration(dur_curr)
        dur_curr = "0:00:00" if dur_curr.startswith("-") else dur_curr

        remains = f"{remains} remaining track(s)"
        vol = f"Volume: {volume}"
        loop_q = f"(🔁) Loop Queue: {loop_q}"
        loop_t = f"(🔂) Loop Track: {loop_t}"
        req = f"Requester: '{self.source.requester}'"
        dur = f"Duration: {dur_curr} (refreshable) / {dur_total}"
        views = f"Views: {self.source.view_count:,}"

        msg = (
            f"```ml\n{tracks}\n"
            f"{remains}     currently playing track:\n"
            f"{loop_q}      {req}\n"
            f"{loop_t}      {dur}\n"
            f"{vol}               {views}```"
        )

        return msg

    def _get_page_info(self):
        player = self.player
        first_row_index = self._get_first_row_index()
        track_list = self._get_track_list(first_row_index)

        tracks = "\n".join(track_list) + "\n"
        remains = len(player.queue[first_row_index + 9 :])
        volume = f"{int(player.volume * 100)}%"
        loop_q = "✅" if player.loop_queue else "❌"
        loop_t = "✅" if player.loop_track else "❌"

        return tracks, remains, volume, loop_q, loop_t

    def _get_first_row_index(self):
        queue = self.player.queue
        pointer = self.player.current_pointer

        start = 1
        if pointer > 2 and len(queue) > 10:
            remaining = len(queue[pointer : pointer + 8])
            start = remaining + pointer - 9

        return start

    def _get_track_list(self, start):
        queue = self.player.queue
        pointer = self.player.current_pointer

        track_list = []
        for row_index, track in enumerate(
            queue[start - 1 : start + 9], start=start
        ):
            row = f"{f'{row_index}. '[:4]}{track['title']}"
            row = (
                f"---> {row} <---"
                if pointer + 1 == row_index
                else f"     {row}"
            )
            track_list.append(row)

        return track_list

    async def on_error(self, interaction, error, item):
        msg = f"Item '{item}' has failed the dispatch. Error: {error}."
        await interaction.response.send_message(msg)

    @discord.ui.button(emoji="⏸️", row=0)
    async def play_callback(self, interaction, button):
        if button.emoji.name == "⏸️":
            error = await self.player.music.pause(interaction)
            if not error:
                button.emoji.name = "▶️"
                self.pause_ts = default_timer()
        elif button.emoji.name == "▶️":
            error = await self.player.music.resume(interaction)
            if not error:
                button.emoji.name = "⏸️"
                self.start += (default_timer() - self.pause_ts)

        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", row=0)
    async def skip_callback(self, interaction, button):
        await self.player.music.skip(interaction)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔁", row=0)
    async def loop_q_callback(self, interaction, button):
        await self.player.music.loop_queue(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔂", row=0)
    async def loop_t_callback(self, interaction, button):
        await self.player.music.loop_track(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔀", row=0)
    async def shuffle_callback(self, interaction, button):
        await self.player.music.shuffle(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(label="Refresh", row=1)
    async def refresh_callback(self, interaction, button):
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)
