"""This module serves to help studying korean vocabulary and listening.

Function hierarchy:
vocab_listening
    _get_vocab_table
    _get_labelled_file_paths
    async get_voice
    get_unknown_lesson_number
    get_session_number
    get_lesson_vocab
    get_review_vocab
        create_users_level_score_ws
            get_score_distribution
            get_time_penalty_data
        get_random_words
    async run_vocab_session_loop
        prepare_word_output
            create_gtts_audio
        create_ending_session_stats

listening
    async get_voice
    get_listening_files
        get_unknown_lesson_number
    async run_listening_session_loop
    ?async pause
    ?async resume
    async on_ready

reading

"""

import json
import os
import random
from datetime import datetime
from glob import glob
from pathlib import Path
from statistics import fmean

import discord
import numpy as np
import pandas as pd
import pytz
from discord import app_commands
from discord.ext import commands
from gspread.exceptions import WorksheetNotFound
from gtts import gTTS

import utils
from cogs.korean.session_views import SessionListenView, SessionVocabView


class Language(commands.Cog):
    def __init__(self, bot):
        self.vocab_audio_paths = self._get_labelled_file_paths(("data/*/*/vocabulary_audio/*", "data/vocabulary_global_gtts_audio/*"))
        self.vocab_image_paths = self._get_labelled_file_paths(("data/*/*/vocabulary_images/*"))
        self.vocab_df = self._get_vocab_table()
        self.bot = bot
        self.ffmpeg_path = (
            "C:/ffmpeg/ffmpeg.exe" if os.name == "nt" else "/usr/bin/ffmpeg"
        )
        self.timezone = ""

    def _get_vocab_table(self):
        """Gets the whole vocabulary table dataframed from google spreadsheet.

        Returns:
            pandas.core.frame.DataFrame: worksheet dataframe table
        """

        _, vocab_dfs = utils.get_worksheets("Korea - Vocabulary", ("Level 1-2 (modified)",))

        # ignore rows with empty Lesson cells (duplicates)
        vocab_df = vocab_dfs[0]
        vocab_df["Lesson"].replace("", np.nan, inplace=True)
        vocab_df.dropna(subset=["Lesson"], inplace=True)

        return vocab_df

    def _get_labelled_file_paths(self, glob_paths):
        """Gets file names and their paths. Used for loading audio/image files.

        Not all words have audio file, it will load only the ones that are
        present in vocabulary_audio directory that is in each of the lessons.
        Audio files are located in data/level_x/lesson_x/vocabulary_audio dir
        and are downloaded from naver dictionary.
        Audio files that are missing are replaced by audio files created by
        GTTS. Those files are located in data/vocabulary_global_gtts_audio dir.

        [REMOVED] (pickle might be added once all image/audio data is ready)
        Just so we dont have to read through all the lessons every time this
        module is loaded, the audio paths are stored in pickle file. (cached)

        Args:
            glob_paths (Tuple[str]): string for glob pathing (with stars)

        Returns:
            Dict[str, str]: words and their audio paths (word being the key)
        """

        src_dir = Path(__file__).parents[0]

        paths = []
        for path in glob_paths:
            paths += glob(f"{src_dir}/{path}")

        paths_labelled = {}
        for path in paths:
            file_name = Path(path).stem
            # file_name = file_name[:-1]  # TODO: 1 AFTER IMAGES PICKED word = word[:-1] - script to remove the last letter
            paths_labelled[file_name] = path

        return paths_labelled

    async def get_voice(self, interaction):
        """Gets or connects to the voice channel.
        
        Gets the voice channel in which the bot is currently in. If it is not
        connected, it connects to channel in which the user is currently in.

        Returns:
            discord.voice_client.VoiceClient: voice channel
        """

        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)
        user_voice = interaction.user.voice
        if not voice and not user_voice:
            await interaction.followup.send("No bot nor you is connected.")
        elif not voice:
            await user_voice.channel.connect()
        voice = discord.utils.get(self.bot.voice_clients, guild=interaction.guild)

        return voice

    def get_unknown_lesson_number(self, user_name):
        """Gets the next unknown level_lesson_number for an user.

        Args:
            user_name (str): user name (used for worksheet name)

        Returns:
            int: level_lesson_number
        """

        df = self.vocab_df
        ws_names = (
            f"{user_name}-score-1", 
            f"{user_name}-score-2",
            f"{user_name}-score-3",
            f"{user_name}-score-4"
        )
        try:
            _, scores_dfs = utils.get_worksheets("Korea - Users stats", ws_names)
        except WorksheetNotFound:
            # going for first level
            level_lesson_number = 101
            scores_dfs = []

        # going for next unknown levels' lessons
        for i, level_scores_df in enumerate(scores_dfs, 1):
            known_words = set(level_scores_df[level_scores_df.columns[0]])
            level_words = set(df.loc[df["Lesson"] // 100 == i, "Korean"])
            unknown_words = level_words - known_words
            ws_missing_words = known_words - level_words
            if ws_missing_words:
                print(f"Level {i} has no words that are in user's score: {ws_missing_words}")
            if unknown_words:
                df = df.loc[df["Korean"].isin(unknown_words), ["Lesson", "Korean"]]
                level_lesson_number = int(df.Lesson.min())
                rows = df[df.Lesson == level_lesson_number].values
                unknown_words = ", ".join([row[1] for row in rows])
                print(f"Unknown words in lesson {level_lesson_number}: {unknown_words}")
                break

        # going for next unknown level
        if level_lesson_number == 1:
            level_lesson_number += 100 + len(scores_dfs) * 100
        
        return level_lesson_number

    def get_session_number(self, ws_log):
        """Gets ordinal number of lesson or review of session. Begins with 1.

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs

        Returns:
            int: ordinal session number
        """

        session_numbers = ws_log.col_values(4)
        if len(session_numbers) > 1:
            session_number = int(session_numbers[-1]) + 1
        else:
            session_number = 1

        return session_number

    def get_lesson_vocab(self, level_lesson_number):
        """Gets vocabulary for a given lesson.

        Args:
            level_lesson_number (int): lesson number

        Returns:
            List[pandas.core.frame.Row]: word data (row in ws table)
        """

        filtered_df = self.vocab_df.loc[self.vocab_df['Lesson'] == level_lesson_number]
        vocab = list(filtered_df.itertuples(name='Row', index=False))
        random.shuffle(vocab)

        return vocab

    def get_review_vocab(self, level_number, user_name):
        """Gets vocabulary review of all guessed words for a given level.

        Args:
            level_number (int): level number
            user_name (str): user name (used for worksheet name)

        Returns:
            List[pandas.core.frame.Row]: word data (row in ws table)
        """

        _, scores_dfs = utils.get_worksheets(
            "Korea - Users stats",
            (f"{user_name}-score-{level_number}",),
        )
        scores_df = scores_dfs[0]
        guessed_words = tuple(scores_df[scores_df.columns[0]])

        picked_words = self.get_random_words(guessed_words)
        picked_words_df = self.vocab_df[self.vocab_df["Korean"].isin(picked_words)]
        vocab = list(picked_words_df.itertuples(name='Row', index=False))

        return vocab

    def create_users_level_score_ws(self, ws_log, user_name, level_number):
        """Creates scoring for level in the user's worksheet.

        Scoring system takes into account: 
         - first guesses in a session, 
         - by each latter session, the importance of score is being reduced 
           by distribution values
         - time of the last guess of a certain word

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            user_name (str): user name (used for worksheet name)
            level_number (int): level number
        """

        score_table = {"✅": 1, "⏭️": 2, "🤔": 2, "🧩": 3, "❌": 4}
        distr_vals = self.get_score_distribution()
        considering_amount = len(distr_vals)
        table_rows = []

        df = pd.DataFrame(ws_log.get_all_records())
        df = df.sort_values(["Word", "Date"])

        # accessing first word individually because we need "previous_row"
        previous_row = df.iloc[0]
        knowledge_marks = [previous_row.Knowledge]
        knowledge_scores = [score_table[previous_row.Knowledge]]
        df.drop(0)

        # need to encounter non-existent word for saving the last word's info
        df = pd.concat([df, pd.DataFrame({"Word": ["X"], "Knowledge": ["❌"]})])

        for row in df.itertuples():
            if previous_row.Word != row.Word:
                knowledge_scores.reverse()
                knowledge_scores = knowledge_scores[:considering_amount]
                knowledge_scores_mean = fmean(knowledge_scores)
                extension_amount = abs(len(knowledge_scores) - len(distr_vals))
                knowledge_scores += [knowledge_scores_mean] * extension_amount
                distr_score = np.array(knowledge_scores) * np.array(distr_vals)

                time_score_penalty, time_marks = self.get_time_penalty_data(
                    previous_row.Date,
                    datetime.now()
                )

                knowledge_marks.reverse()
                knowledge_marks = knowledge_marks[:considering_amount]

                final_score = sum(distr_score) + time_score_penalty

                table_rows.append(
                    [
                        previous_row.Word,
                        final_score,
                        "".join(knowledge_marks),
                        "".join(time_marks)
                    ]
                )

                knowledge_marks = [row.Knowledge]
                knowledge_scores = [score_table[row.Knowledge]]

            # take into account only the first guesses in one session
            elif previous_row.Session_number != row.Session_number:
                knowledge_marks.append(row.Knowledge)
                knowledge_scores.append(score_table[row.Knowledge])

            previous_row = row

        table_rows = sorted(table_rows, key=lambda x:x[1], reverse=True)

        # create worksheet of scores
        ws_scores_list, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{user_name}-score-{level_number}",),
            create=True,
            size=(10_000, 4)
        )
        ws_scores = ws_scores_list[0]
        ws_scores.clear()
        table_rows.insert(0, ["Word", "Score", "Knowledge", "Last_time"])
        ws_scores.append_rows(table_rows)

    def get_score_distribution(self, amount=5, reducer=0.8):
        """Gets score distribution for vocabulary picking.

        Args:
            amount (int, optional): amount of values. Defaults to 10.
            reducer (float, optional): reducing coefficient. Defaults to 0.8.

        Returns:
            List[float]: distribution values
        """

        score = 1
        distribution_vals = []
        for _ in range(amount):
            distribution_vals.append(score)
            score = round(score * reducer, 3)

        return distribution_vals

    def get_time_penalty_data(self, row_date, now_date, coefficient = 0.01):
        """Gets time score penalty and emoji visualization for worksheet.

        Args:
            row_date (str): row's (word's) guess date
            now_date (datetime.datetime): current date
            coefficient (float, optional): Penalty coefficient.
                Defaults to 0.005.

        Returns:
            Tuple[int, List[str]]: score penalty, time marks
        """

        # score penalty
        row_date = datetime.strptime(row_date, "%Y-%m-%d %H:%M:%S")
        days_diff = (now_date - row_date).days
        score_penalty = days_diff * coefficient

        # emoji visualizations
        months, days = divmod(days_diff, 30)
        weeks, days = divmod(days, 7)
        time_marks = ["🌙"] * months + ["📅"] * weeks + ["🌞"] * days

        return score_penalty, time_marks

    def get_random_words(self, words, consider_amount=150, pick_amount=50):
        """Gets randomly chosen words for session.

        Creates linear probability distribution and uses it to pick words
        randomly from the most unknown ones to known ones.

        Args:
            words (List[str]): words that were guessed in a level
            consider_amount (int, optional): Amount of words to consider into
                random picking. Defaults to 150.
            pick_amount (int, optional): Amount of words to pick.
                Defaults to 50.

        Returns:
            numpy.ndarray: (list of) picked words
        """

        consider_amount = len(words) if len(words) < consider_amount else consider_amount
        pick_amount = consider_amount if consider_amount < pick_amount else pick_amount

        mean = 0
        std = 0.5
        half_norm_distribution = np.abs(np.random.normal(loc=mean, scale=std, size=consider_amount))
        half_norm_distribution.sort()
        half_norm_distribution = half_norm_distribution[::-1]
        weights = half_norm_distribution / half_norm_distribution.sum()

        picked_words = np.random.choice(words[:consider_amount], p=weights, size=pick_amount, replace=False)

        return picked_words

    def prepare_word_output(self, row, guide, i=[0]):
        """Prepares variables needed for outputting word data.

        Args:
            List[pandas.core.frame.Row]: word data (row in ws table)
            guide (bool): determines whether we want additional word info
            i (list, optional): using for discord bug with spoiled words.
                Defaults to [0].

        Returns:
            Tuple[discord.embeds.Embed, discord.file.File, str]: word data
        """

        max_spaces = 30
        i[0] += 1
        i[0] %= max_spaces
        spoil_spacing = " " * (i[0])
        file = None

        kor_no_num = row.Korean[:-1] if row.Korean[-1].isdigit() else row.Korean
        if kor_no_num not in self.vocab_audio_paths:
            self.create_gtts_audio(kor_no_num)

        url = "https://korean.dict.naver.com/koendict/#/search?range=all&query="
        url_kor = url + kor_no_num.replace(" ", "%20")

        eng_add = f"; ({row.English_Add})" if row.English_Add else ""
        content = f"**{row.Korean} - {row.Book_English}{eng_add}**"
        if not guide:
            content = f"||{content}{spoil_spacing}||"

        embed = discord.Embed(title=content, url=url_kor)

        if guide:
            ex = f"- {row.Example_KR} ({row.Example_EN})\n" if row.Example_KR else ""
            # NOTE: nn conditions when data is fully filled
            ex += f"- {row.Example_KR2} ({row.Example_EN2})\n" if row.Example_KR2 else ""
            ex = "\n" + ex if ex else ""
            if row.Explanation:
                embed.add_field(name="", value=f"**{row.Explanation}**{ex}", inline=False)
            # kk = "C:/Users/pmark/Desktop/Caroline-bot/cogs/korean/data/level_1/lesson_1/vocabulary_images/a2.png"
            # file = discord.File(kk, filename="image.png")
            if kor_no_num in self.vocab_image_paths:
                file = discord.File(self.vocab_image_paths[kor_no_num], filename="image.png")
            embed.set_image(url="attachment://image.png")

        return embed, file, self.vocab_audio_paths[kor_no_num]

        ######
        # korean_words = re.findall("[가-힣]+", syl)
        # for word in korean_words:
        #     syl = syl.replace(word, f"\n**{word}**")
        # syl = syl[1:]
        # {examples}\n\n{syl}
        # color = discord.Color.green(),
        # embed.set_footer(text=f"Rank {rank}")
        # embed.set_thumbnail(url="attachment://image.png")
        # embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://pbs.twimg.com/profile_images/1327036716226646017/ZuaMDdtm_400x400.jpg")
        # embed.set_image(url="attachment://image.png")
        # > {text} >

    def create_gtts_audio(self, korean_word):
        """Creates an audio using google's TTS for a given korean word.

        This is being used for all the words that have no audio from naver's
        dictionary. 
        Audio files are saved in data/vocabulary_global_gtts_audio dir, a new
        audio path is added for the given korean word.

        Args:
            korean_word (str): korean word
        """

        src_dir = Path(__file__).parents[0]
        vocab_path = f"{src_dir}/data/vocabulary_global_gtts_audio/"
        path = f'{vocab_path}/{korean_word}.mp3'
        tts = gTTS(korean_word, lang='ko')
        tts.save(path)

        self.vocab_audio_paths[korean_word] = path

    async def run_vocab_session_loop(self, interaction, voice, ws_log, session_number, lesson, vocab):
        """Runs session loop for vocabulary words.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            voice (discord.voice_client.VoiceClient): voice client channel
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_number (int): session number
            lesson (bool): indicates whether session is informational lesson or review
            List[pandas.core.frame.Row]: word data (row in ws table)
        """

        stat_labels = {"easy": "✅", "effort": "🤔", "partial": "🧩", "forgot": "❌"}
        view = SessionVocabView()
        guide = lesson

        unchecked_words = {row.Korean for row in vocab}
        stats = []
        msg = None
        
        while True:
            embed, file, audio_path = self.prepare_word_output(vocab[-1], guide)
            try:
                voice.play(
                    discord.FFmpegPCMAudio(
                        audio_path,
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            embed.set_footer(text=f"{len(unchecked_words)} words remaining")
            if not msg:
                msg = await interaction.channel.send(embed=embed, view=view)
            else:
                await msg.edit(embed=embed, view=view)
            if file:
                await msg.add_files(file)

            # wait for interaction
            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )

            # button interactions
            button_id = interaction.data["custom_id"]
            if button_id == "repeat":
                continue
            elif button_id == "info":
                guide = True
                continue

            guide = lesson
            row_to_move = vocab.pop()

            if button_id == "easy":
                vocab.insert(0, row_to_move)
                if row_to_move in unchecked_words:
                    unchecked_words.remove(row_to_move)
            elif button_id == "effort":
                vocab.insert(len(vocab) // 2, row_to_move)
            elif button_id == "partial":
                vocab.insert(len(vocab) // 3, row_to_move)
            elif button_id == "forgot":
                vocab.insert(- len(vocab) // 5, row_to_move)
            elif button_id == "end":
                stats_str = self.create_ending_session_stats(stats)
                content = f"{len(unchecked_words)} words remaining.\n{stats_str}"
                await msg.edit(content=content, view=view, embed=None)
                break

            time = datetime.now(pytz.timezone(self.timezone))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            stat = [
                time_str,
                row_to_move.Korean,
                stat_labels[button_id],
                session_number
            ]
            stats.append(stat)
            ws_log.append_row(stat)

    def create_ending_session_stats(self, stats):
        """Gets stats that will be displayed when the session ends.

        Contains top 5 wrongly guessed words and overall percentages for each
        mark.

        Args:
            stats (List[str, str, str, int]): time, word, mark, session number

        Returns:
            str: stats
        """

        if not stats:
            return "There weren't any words guessed."

        # get marks count and scoring per word
        marks_count = {"✅": 0, "🤔": 0, "🧩": 0, "❌": 0}
        score_table = {"✅": 0, "🤔": 1, "🧩": 2, "❌": 3}
        word_scores = {}
        for _, word, mark, _ in stats:
            if word not in word_scores:
                word_scores[word] = score_table[mark]
                marks_count[mark] += 1
            else:
                word_scores[word] += score_table[mark]

        # get hardest words
        word_scores_sorted = sorted(word_scores.items(), key=lambda x:x[1], reverse=True)
        hardest_words = []
        for word, score in word_scores_sorted[:5]:
            if score:
                hardest_words.append(word)
        hardest_words_string = ", ".join(hardest_words)

        # get mark percentages
        total = sum(marks_count.values())
        for mark in marks_count:
            marks_count[mark] = round(marks_count[mark] * 100 / total)

        percentages_summary = (
            f"{marks_count['✅']}%,"
            f"   {marks_count['🤔']}%,"
            f"   {marks_count['🧩']}%,"
            f"   {marks_count['❌']}%"
        )

        stats = f"Total guesses: {len(stats)}\nHardest words: {hardest_words_string}\n{percentages_summary}"

        return stats

    def get_listening_files(self, interaction, level_lesson_number):
        """Gets listening contents text and path to audio files.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            level_lesson_number (int): lesson number

        Returns:
            Tuple[List[str], List[str]]: (audio text, audio paths)
        """

        src_dir = Path(__file__).parents[0]
        level_number, lesson_number = self.get_level_lesson(interaction, level_lesson_number)
        lesson_path = f"{src_dir}/data/level_{level_number}/lesson_{lesson_number}"
        audio_path = Path(f"{lesson_path}/listening_audio")
        text_path = Path(f"{lesson_path}/listening_text.txt")

        try:
            with open(text_path, encoding="utf-8") as f:
                text = f.read()
            audio_texts = text.split("\n\n")
            audio_paths = sorted(glob(f"{audio_path}/listening_audio/*"))
            # sorted it because linux system reverses it
        except Exception:
            return [], []

        return audio_texts, audio_paths

    async def run_listening_session_loop(self, interaction, voice, audio_texts, audio_paths):

        i = 0
        count_n = len(audio_paths)
        view = SessionListenView()
        msg_str = f"{i+1}. track out of {count_n}."

        msg = await interaction.channel.send(msg_str)
        while True:
            if i >= count_n:
                i = 0
            try:
                voice.play(
                    discord.FFmpegPCMAudio(
                        audio_paths[i],
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            msg_str = f"{i+1}. lesson out of {count_n}"
            content = f"```{msg_str}\n{audio_texts[i]}```"
            await msg.edit(content=content, view=view)

            # wait for interaction
            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )

            # button interactions
            button_id = interaction.data["custom_id"]
            # TODO LISTEN ChatGPT Tokens first use!
            # TODO LISTEN polish whole module + apply pylint
            # TODO LISTEN ADD backward button (10s)
            if button_id == "pauseplay":
                # TODO LISTEN FIX: pauseplay button
                # need to add player, pause NN crucially atm
                button_id2 = None
                while button_id2 != "pauseplay":
                    interaction = await self.bot.wait_for(
                        "interaction",
                        check=lambda inter: "custom_id" in inter.data.keys()
                        and inter.user.name == interaction.user.name,
                    )
                    button_id2 = interaction.data["custom_id"]
            elif button_id == "next":
                i += 1
            elif button_id == "repeat":
                continue
            elif button_id == "end":
                content = f"```{msg_str}\nEnding listening session.```"
                await msg.edit(content=content, view=view)
                break

    # Button commands
    async def pause(self, interaction):
        """Pause the currently playing song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_playing():
            return
        elif vc.is_paused():
            return

        vc.pause()

    async def resume(self, interaction):
        """Resume the currently paused song."""

        vc = interaction.guild.voice_client
        if not vc or not vc.is_connected():
            return
        elif not vc.is_paused():
            return

        vc.resume()

    @commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded, it initializes timezone.

        This could have been initialized in __init__ method, but to make it
        consistent with all cogs, on_ready is being used for config loading.
        Surveillance module needs to load it there."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]

    @app_commands.command(name="vl")
    async def vocab_listening(self, interaction, level_lesson_number: int):
        """Start listening vocabulary exercise.

        There are 3 types of level_lesson_number:
         - One ("1") finds the next user's unknown lesson
         - Pure hundreds ("100", ..., "400") review session of one levels words
           (Hundred decimals represent level)
         - Hundreds up to 30 ("101", ..., "130") specific lesson number
           (Ten decimals represent level's lesson)
        """

        await interaction.response.send_message(
            "...Setting up vocab session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Vocabulary")
        )

        if level_lesson_number == 1:
            level_lesson_number = self.get_unknown_lesson_number(interaction.user.name)

        # get level and lesson number with validation check
        level_number, lesson_number = divmod(level_lesson_number, 100)
        if not (0 < level_number < 5 and lesson_number < 31):
            msg = "Wrong level lesson number!"
            await interaction.followup.send(msg)
            assert False, msg

        # get users stats worksheet
        ws_logs, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{interaction.user.name}-{level_number}",),
            create=True,
            size=(10_000, 4)
        )
        ws_log = ws_logs[0]
        if not ws_log.get_values("A1"):  # create header if missing
            ws_log.append_row(["Date", "Word", "Knowledge", "Session_number"])

        session_number = self.get_session_number(ws_log)

        if lesson_number:
            vocab = self.get_lesson_vocab(level_lesson_number)
            msg = f"Lesson {level_lesson_number}, session: {session_number}"
        else:
            vocab = self.get_review_vocab(level_number, interaction.user.name)
            msg = f"Review level {level_number}, session: {session_number}"
        await interaction.followup.send(msg)

        await self.run_vocab_session_loop(interaction, voice, ws_log, session_number, bool(lesson_number), vocab)

        self.create_users_level_score_ws(ws_log, interaction.user.name, level_number)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

    @app_commands.command(name="l")
    async def listening(self, interaction, level_lesson_number: int):
        """Start listening exercise."""

        await interaction.response.send_message(
            "...Setting up listening session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Listening")
        )

        audio_texts, audio_paths = self.get_listening_files(interaction, level_lesson_number)
        if not audio_texts and not audio_paths:
            msg = f"{level_lesson_number} lesson's audio files were not found!"
            await interaction.followup.send(msg)
            assert False, msg

        await interaction.followup.send(f"Lesson {level_lesson_number}")

        await self.run_listening_session_loop(interaction, voice, audio_texts, audio_paths)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="/play",
            ),
            status=discord.Status.online,
        )

    @app_commands.command(name="r")
    async def reading(self, interaction, level_lesson_number: int):
        """Start reading exercise."""

        await interaction.response.send_message(
            "...Setting up listening session..."
        )

        level_number, lesson_number = self.get_level_lesson(interaction, level_lesson_number)

        # load text file
        src_dir = Path(__file__).parents[0]
        lesson_path = f"{src_dir}/data/level_{level_number}/lesson_{lesson_number}"
        text_path = Path(f"{lesson_path}/reading_text.txt")
        try:
            with open(text_path, encoding="utf-8") as f:
                reading_text = f.read()
        except Exception as exc:
            msg = f"{level_lesson_number} lesson's text files were not found!"
            await interaction.followup.send(msg)
            raise commands.CommandError(msg) from exc

        await interaction.followup.send(f"Lesson {level_lesson_number}")
        await interaction.channel.send(f"```{reading_text}```")


async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Language(bot), guilds=[discord.Object(id=os.environ["SERVER_ID"])]
    )

# TODO: 3 Pylint, alt+shift
