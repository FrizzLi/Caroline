from timeit import default_timer as timer

import discord
from discord.ui import View, Button, Select


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
        await self.player.music._play(interaction, self.values[0])


class SearchView(View):
    def __init__(self, player, tracks):
        super().__init__(timeout=None)
        self.msg = "Choose a track!"
        self.add_item(self.addSelection(tracks, player))

    def addSelection(self, tracks, player):
        selection = SearchSelect(player)

        # above 25: raises maximum number of options already provided 
        for track in tracks[-25:]:
            selection.add_option(
                label=track['title'],
                description=get_readable_duration(track['duration']),
                value=track['webpage_url'],
            )
        return selection


class PlayerView(View):
    def __init__(self, player, source):
        super().__init__(timeout=None)
        self.add_item(Button(label="Current playing track link", url=source.web_url, row=1))
        self.player = player
        self.np = source
        self.start_timestamp = timer()
        self.msg = self.generate_message()

    def generate_message(self):
        """Display information about player and queue of songs."""

        tracks, remains, volume, loop_q, loop_t = self._get_page_info()
        end_timestamp = timer()
        duration_left = self.np.duration - (end_timestamp - self.start_timestamp)
        duration = get_readable_duration(duration_left)

        remains = f"{remains} remaining track(s)"
        vol = f"Volume: {volume}"
        loop_q = f"(🔁) Loop Queue: {loop_q}"
        loop_t = f"(🔂) Loop Track: {loop_t}"
        req = f"Requester: '{self.np.requester}'"
        dur = f"Duration: {duration} (refreshable)"
        views = f'Views: {self.np.view_count:,}'

        msg = (
            f"```ml\n{tracks}\n"
            f"{remains}     currently playing track:\n"
            f"{loop_q}      {req}\n"
            f"{loop_t}      {dur}\n"
            f"{vol}                {views}```"
        )

        return msg

    def _get_page_info(self):
        player = self.player
        first_row_index = self._get_first_row_index()
        track_list = self._get_track_list(first_row_index)

        tracks = "\n".join(track_list) + "\n"
        remains = len(player.queue[first_row_index+9:])
        volume = f"{int(player.volume * 100)}%"
        loop_q = "✅" if player.loop_queue else "❌"
        loop_t = "✅" if player.loop_track else "❌"

        return tracks, remains, volume, loop_q, loop_t

    def _get_first_row_index(self):
        queue = self.player.queue
        pointer = self.player.current_pointer

        s = 1
        if pointer > 2 and len(queue) > 10:
            remaining = len(queue[pointer: pointer + 8])
            s = remaining + pointer - 9

        return s

    def _get_track_list(self, s):
        queue = self.player.queue
        pointer = self.player.current_pointer

        track_list = []
        for row_index, track in enumerate(queue[s-1:s+9], start=s):
                row = f"{f'{row_index}. '[:4]}{track['title']}"
                row = f"---> {row} <---" if pointer + 1 == row_index else f"     {row}"
                track_list.append(row)

        return track_list

    async def on_error(self, error, item, interaction):
        msg = f"Item '{item}' has failed the dispatch. Error: {error}."
        await interaction.response.send_message(msg)

    @discord.ui.button(emoji="⏸️", row=0)
    async def play_callback(self, interaction, button):
        if button.emoji.name == "⏸️":
            error = await self.player.music.pause_(interaction)
            if not error:
                button.emoji.name = "▶️"
        elif button.emoji.name == "▶️":
            error = await self.player.music.resume_(interaction)
            if not error:
                button.emoji.name = "⏸️"

        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", row=0)
    async def skip_callback(self, interaction, button):
        await self.player.music.skip_(interaction)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔁", row=0)
    async def loop_q_callback(self, interaction, button):
        await self.player.music.loop_queue_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔂", row=0)
    async def loop_t_callback(self, interaction, button):
        await self.player.music.loop_track_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔀", row=0)
    async def shuffle_callback(self, interaction, button):
        await self.player.music.shuffle_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(label="Refresh", row=1)
    async def refresh_callback(self, interaction, button):
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)
