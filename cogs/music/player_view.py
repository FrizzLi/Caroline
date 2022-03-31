import discord
from discord.ui import View


class PlayerView(View):
    def __init__(self, player, source):
        super().__init__()
        self.player = player
        self.np = source
        self.old_msg = True
        self.msg = self.generate_message()

    def generate_message(self):
        """Display information about player and queue of songs."""

        tracks, remains, volume, loop_q, loop_t = self._get_page_info()
        if self.old_msg:
            remains = f"{remains} remaining track(s)"
            vol = f"Volume: {volume}"
            loop_q = f"Loop Queue: {loop_q}"
            loop_t = f"Loop Track: {loop_t}"
            req = f"Requester: '{self.np.requester}'"
            dur = f"Duration: {self.np.duration}"
            views = f'Views: {self.np.view_count:,}'

            msg = (
                f"```ml\n{tracks}\n"
                f"{remains}     currently playing track:\n"
                f"{loop_q}           {req}\n"
                f"{loop_t}           {dur}\n"
                f"{vol}                {views}```"
            )
        else:
            msg = discord.Embed(description=tracks, color=discord.Color.green())
            msg.add_field(name='Remaining track(s)', value=remains)
            msg.add_field(name="Volume", value=volume)
            msg.add_field(name="Queue/Track Loop", value=f"{loop_q} / {loop_t}")
            msg.add_field(name='Requested by', value=self.np.requester)
            msg.add_field(name='Duration', value=self.np.duration, inline=True)
            msg.add_field(name='Views', value=f'{self.np.view_count:,}', inline=True)

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
        if self.old_msg:
            for row_index, track in enumerate(queue[s-1:s+9], start=s):
                row = f"{f'{row_index}. '[:4]}{track['title']}"
                row = f"---> {row} <---" if pointer + 1 == row_index else f"     {row}"
                track_list.append(row)
        else:
            for row_index, track in enumerate(queue[s-1:s+9], start=s):
                row = f"`{f'{row_index}. '[:3]}`"
                if pointer + 1 > row_index:
                    row += f"**{track['title']}**"
                elif pointer + 1 == row_index:
                    row += f"**[{self.np.title}]({self.np.web_url})**"
                else:
                    row += track['title']
                track_list.append(row)

        return track_list

    @discord.ui.button(emoji="⏸️")
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

    @discord.ui.button(emoji="⏭️")
    async def skip_callback(self, interaction, button):  # TODO: try without button
        await self.player.music.skip_(interaction)
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔁")
    async def loop_q_callback(self, interaction, button):
        await self.player.music.loop_queue_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🔂")
    async def loop_t_callback(self, interaction, button):
        await self.player.music.loop_track_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

    @discord.ui.button(emoji="🎲")
    async def shuffle_callback(self, interaction, button):
        await self.player.music.shuffle_(interaction)
        msg = self.generate_message()
        await interaction.response.edit_message(content=msg, view=self)

# HELPFUL FOR MAKING BUTTONS/VIEW
# class MyButton(Button):
#     def __init__(self):
#         super().__init__(label="Play me!", style=discord.ButtonStyle.green, emoji="▶️")

#     async def button_callback(self, interaction):  # MUST BE callback only
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")
#             await interaction.followup.send("Hiiiii")

#     @commands.command()
#     async def hell(self, ctx):
#         button1 = MyButton()
#         button2 = Button(emoji="⏸️")
#         button3 = Button(label="Go to Google", url="https://google.com")

#         async def button_callback(interaction):
#             # await interaction.response.send_message("Hi!!", view=None) (gets removed)
#             await interaction.response.edit_message("Hi!!")
#             await interaction.response.edit_message(content="Hi!!")
#             await interaction.followup.send("Hiiiii")
#         button1.callback = button_callback
#         # IF NEED TO RESPOND FAST - 13:55

#         view = View(timeout=10)  # select menus, text input
#         view.add_item(button1)
#         view.add_item(button2)
#         view.add_item(button3)
#         # view.remove_item()
#         embed = discord.Embed(title="sss", description="I'm not connected to a voice channel", color=discord.Color.green())
#         await ctx.send(embed=embed, view=view)
#         # await ctx.send("Hello!", view=view)

#     @commands.command()
#     async def hello(self, ctx):
#         button1 = MyButton()

# class MyView2(View):
# label="Click heere!", style=discord.ButtonStyle.green,
# @discord.ui.button(emoji="⏮️")
# async def prev_callback(self, button, interaction):
#     # button.label = "WOW!"
#     # button.disabled = True
#     await interaction.response.edit_message(view=self)

# async def on_timeout(self):
#     await self.ctx.send("Timeout!")

# # async def on_error(self, error, item, interaction):
# #     await interaction.response.send_message(str(error))

# # async def interaction_check(self, interaction) -> bool:
# if interaction.user != self.ctx.author:
#     await interaction.response.send_message("Hey! You cant use that!", ephemeral=True)
#     return False
# else:
#     return True
