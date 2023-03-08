import discord
import asyncio


class SessionVocabView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="✅", custom_id="easy")
    async def easy_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="⏭️", custom_id="medium")
    async def medium_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="❌", custom_id="hard")
    async def hard_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="🔁", custom_id="repeat")
    async def repeat_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="🔚", custom_id="end")
    async def end_callback(self, interaction, button):
        await interaction.response.defer()


class Session_Listen_View(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="⏸️", custom_id="pauseplay")
    async def play_callback(self, interaction, button):
        if button.emoji.name == "⏸️":
            error = await self.player.music.pause(interaction)
            if not error:
                button.emoji.name = "▶️"
        elif button.emoji.name == "▶️":
            error = await self.player.music.resume(interaction)
            if not error:
                button.emoji.name = "⏸️"

        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", custom_id="next")
    async def medium_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="🔁", custom_id="repeat")
    async def repeat_callback(self, interaction, button):
        await interaction.response.defer()

    @discord.ui.button(emoji="🔚", custom_id="end")
    async def end_callback(self, interaction, button):
        await interaction.response.defer()
