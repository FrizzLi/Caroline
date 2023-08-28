import discord

VOCAB_CHOICES = [
    discord.app_commands.Choice(name="👉 Learn new words", value=1),
    discord.app_commands.Choice(name="👉 Review words from Level 1", value=100),
    discord.app_commands.Choice(name="👉 Review words from Level 2", value=200),
    discord.app_commands.Choice(name="👉 Review words from Level 3", value=300),
    discord.app_commands.Choice(name="👉 Review words from Level 4", value=400),
]
LISTEN_CHOICES = [
    discord.app_commands.Choice(name="👉 Listen next lesson", value=0),
    discord.app_commands.Choice(name="👉 Listen previously fully listened lesson", value=-1)
]

READ_CHOICES = [
    discord.app_commands.Choice(name="👉 Read next lesson", value=0),
    discord.app_commands.Choice(name="👉 Read previously read lesson", value=-1)
]

VOCAB_DESCR = (
    "Gets next lesson with words that you haven't encountered yet.",
    "Reviews all the words you encountered in Level 1",
    "Reviews all the words you encountered in Level 2",
    "Reviews all the words you encountered in Level 3",
    "Reviews all the words you encountered in Level 4",
)
LISTEN_DESCR = (
    "Gets next lesson with tracks that you haven't encountered yet.",
    "Gets lesson with tracks that you've lastly encountered.",
)
READ_DESCR = (
    "Gets next lesson with reading text that you haven't encountered yet.",
    "Gets lesson with reading text that you've lastly encountered.",
)

CHOICES = (VOCAB_CHOICES, LISTEN_CHOICES, READ_CHOICES)
CHOICES_DESCR = (VOCAB_DESCR, LISTEN_DESCR, READ_DESCR)
