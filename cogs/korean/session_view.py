import discord


class SessionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="✅", custom_id="easy")
    async def easy_callback(self, interaction, button):
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="⏭️", custom_id="medium")
    async def medium_callback(self, interaction, button):
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="❌", custom_id="hard")
    async def hard_callback(self, interaction, button):
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔁", custom_id="repeat")
    async def repeat_callback(self, interaction, button):
        await interaction.response.edit_message(view=self)

    @discord.ui.button(emoji="🔚", custom_id="end")
    async def end_callback(self, interaction, button):
        await interaction.response.edit_message(view=self)
