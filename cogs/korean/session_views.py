from discord.ui import Select, View, button

from cogs.korean.constants import CHOICES, CHOICES_DESCR


class SessionVocabView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(emoji="✅", row=0, custom_id="easy")
    async def easy_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="🤔", row=0, custom_id="effort")
    async def effort_callback(self, interaction, button):
        await interaction.response.defer()
    
    @button(emoji="🧩", row=0, custom_id="partial")
    async def partial_callback(self, interaction, button):
        await interaction.response.defer()
    
    @button(emoji="❌", row=0, custom_id="forgot")
    async def forgot_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="🔁", row=1, custom_id="repeat")
    async def repeat_callback(self, interaction, button):
        await interaction.response.defer()
    
    @button(emoji="📄", row=1, custom_id="info")
    async def info_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="🔚", row=1, custom_id="end")
    async def end_callback(self, interaction, button):
        await interaction.response.defer()


class SessionListenView(View):
    def __init__(self, korean):
        super().__init__(timeout=None)
        self.korean = korean

    @button(emoji="⏪", custom_id="backward")
    async def backplay_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="⏸️", custom_id="pauseplay")
    async def pauseplay_callback(self, interaction, button):

        # pause
        if button.emoji.name == "⏸️":
            vc = interaction.guild.voice_client
            if not vc or not vc.is_playing():
                return
            elif vc.is_paused():
                return

            vc.pause()
            button.emoji.name = "▶️"

            # disable other buttons
            for children in self.children:
                if children.custom_id != "pauseplay":
                    children.disabled = True

        # resume
        elif button.emoji.name == "▶️":
            vc = interaction.guild.voice_client
            if not vc or not vc.is_connected():
                return
            elif not vc.is_paused():
                return

            vc.resume()
            button.emoji.name = "⏸️"

            # reenable other buttons
            for children in self.children:
                children.disabled = False

        await interaction.response.edit_message(view=self)

    @button(emoji="⏭️", custom_id="next")
    async def medium_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="🔁", custom_id="repeat")
    async def repeat_callback(self, interaction, button):
        await interaction.response.defer()

    @button(emoji="🔚", custom_id="end")
    async def end_callback(self, interaction, button):
        await interaction.response.defer()

class MenuSessionSelect(Select):
    def __init__(self, korean):
        super().__init__()
        self.korean = korean
        self.custom_id = 'sessionSelect'
        self.placeholder = "Select YOUR sessions here"

    async def callback(self, interaction):
        command_selection = int(self.values[0][0])
        level_lesson = int(self.values[0][1:])
        if command_selection == 0:
            await self.korean.vocab_listening(interaction, level_lesson)
        elif command_selection == 1:
            await self.korean.listening(interaction, level_lesson)
        elif command_selection == 2:
            await self.korean.reading(interaction, level_lesson)

class MenuSessionsView(View):
    def __init__(self, korean):
        super().__init__(timeout=None)
        self.msg = "Choose a session!"
        self.add_item(self.add_selection(korean))

    def add_selection(self, korean):
        selection = MenuSessionSelect(korean)

        for i, cmd_selections, cmd_descrs in zip(range(len(CHOICES)), CHOICES, CHOICES_DESCR):
            for cmd_selection, cmd_descr in zip(cmd_selections, cmd_descrs):
                selection.add_option(
                    label=cmd_selection.name,
                    value=str(i) + str(cmd_selection.value),
                    description=cmd_descr
                )

        return selection
