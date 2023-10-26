"""This module serves to help studying korean vocabulary and listening.

Function hierarchy:
vocab_listening
    _get_vocab_table
    _get_labelled_paths
    async get_voice
    async get_level_lesson_nums
        get_unknown_lesson_num
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
    async get_voice~~~
    async get_listening_files
        get_unknown_lesson_num~~~
    async run_listening_session_loop
        move_timestamp
    async on_ready

reading
    get_level_lesson_nums~~~
    get_lr_level_lesson_nums~~~
    set_lr_level_lesson_nums~~~

"""

import asyncio
import json
import os
import random
import time
from datetime import datetime
from glob import glob
from pathlib import Path
from statistics import fmean

import discord
import numpy as np
import pandas as pd
import pytz
from gspread.exceptions import WorksheetNotFound
from gtts import gTTS

import utils
from cogs.korean.constants import LISTEN_CHOICES, READ_CHOICES, VOCAB_CHOICES
from cogs.korean.session_views import (MenuSessionsView, SessionListenView,
                                       SessionVocabView)

V_IMAGE_PATHS = ("data/*/*/vocabulary_images/*",)
V_AUDIO_PATHS = (
    "data/*/*/vocabulary_audio/*",
    "data/vocabulary_global_gtts_audio/*",
)
V_SPREADSHEET = "Korea - Vocabulary"
V_WORKSHEETS = ("Level 1-2 (modified)",)
S_SPREADSHEET = "Korea - Users stats"


class Language(discord.ext.commands.Cog):
    def __init__(self, bot):
        self.vocab_audio_paths = self._get_labelled_paths(V_AUDIO_PATHS)
        self.vocab_image_paths = self._get_labelled_paths(V_IMAGE_PATHS, True)
        self.lr_tracking_table = self._get_lr_tracking_table()
        self.vocab_df = self._get_vocab_table()
        self.bot = bot
        self.ffmpeg_path = (
            "C:/ffmpeg/ffmpeg.exe" if os.name == "nt" else "/usr/bin/ffmpeg"
        )
        self.timezone = ""
        self.busy_str = ""

    def _get_vocab_table(self):
        """Gets the whole vocabulary table dataframed from google spreadsheet.

        Returns:
            pandas.core.frame.DataFrame: worksheet dataframe table
        """

        _, vocab_dfs = utils.get_worksheets(V_SPREADSHEET, V_WORKSHEETS)

        # ignore rows with empty Lesson cells (duplicates)
        vocab_df = vocab_dfs[0]
        vocab_df["Lesson"].replace("", np.nan, inplace=True)
        vocab_df.dropna(subset=["Lesson"], inplace=True)

        return vocab_df

    def _get_lr_tracking_table(self):
        """Gets listening/reading tracking worksheet for user.

        Returns:
            List[List[gspread.worksheet.Worksheet, pandas.core.frame.DataFrame]]: (
                list of listening/reading worksheets (only one),
                list of listening/reading dataframes (only one)
            )
        """

        tracking_ws, tracking_df = utils.get_worksheets(
            S_SPREADSHEET,
            ("listen_read-tracking",),
            create=True,
            size=(1_000, 9),
        )
        tracking_ws = tracking_ws[0]
        tracking_df = tracking_df[0]

        # create header if missing
        listen = ["Listening 1", "Listening 2", "Listening 3", "Listening 4"]
        read = ["Reading 1", "Reading 2", "Reading 3", "Reading 4"]
        row = ["Username"] + listen + read
        if not tracking_ws.get_values("A1"):
            tracking_ws.append_row(row)
        if tracking_df.empty:
            tracking_df = pd.DataFrame(columns=row)

        return [tracking_ws, tracking_df]

    def _get_labelled_paths(self, glob_paths, ignore_last_letter=False):
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
            ignore_last_letter (bool, optional): ignore last letter in the
                filename (for image pickings). Defaults to False.

        Returns:
            Dict[str, str]: words and their audio paths (word being the key)
        """

        src_dir = Path(__file__).parents[0]

        paths = []
        for path in glob_paths:
            paths += glob(f"{src_dir}/{path}")

        paths_labelled = {}
        if ignore_last_letter:
            for path in paths:
                if path[-5].islower():
                    file_name = Path(path).stem
                    file_name = file_name[:-1]
                    paths_labelled[file_name] = path[:-5] + path[-4:]
        else:
            for path in paths:
                file_name = Path(path).stem
                paths_labelled[file_name] = path

        return paths_labelled

    async def get_voice(self, interaction):
        """Gets or connects to the voice channel.

        Gets the voice channel in which the bot is currently in. If it is not
        connected, it connects to channel in which the user is currently in.

        Returns:
            discord.voice_client.VoiceClient: voice channel
        """

        guild = interaction.guild
        user_voice = interaction.user.voice
        if not user_voice:
            msg = await interaction.followup.send("You are not in a voice channel.")
            await asyncio.sleep(10.0)
            await msg.delete()
            return

        voice = discord.utils.get(self.bot.voice_clients, guild=guild)
        if not voice:
            await user_voice.channel.connect()
        elif voice.channel != user_voice.channel:
            await voice.move_to(user_voice.channel)
        voice = discord.utils.get(self.bot.voice_clients, guild=guild)

        return voice

    async def get_level_lesson_nums(
        self, interaction, level_lesson_num
    ):
        """Gets level lesson numbers for vocabulary sessions.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            level_lesson_num (int): level lesson number

        Returns:
            Tuple[int, int, int]: level lesson numbers
        """

        user_name = interaction.user.name

        if level_lesson_num == 1:
            level_lesson_num = self.get_unknown_lesson_num(user_name)

        level_num, lesson_num = divmod(level_lesson_num, 100)
        if not (0 < level_num < 5 and lesson_num < 31):
            # we cannot choose certain lesson now so this is redundant
            msg = "Wrong level lesson number!"
            msg = await interaction.followup.send(msg)
            await asyncio.sleep(10.0)
            await msg.delete()
            self.busy_str = ""
            assert False, msg

        return level_num, lesson_num, level_lesson_num

    def get_lr_level_lesson_nums(self, user_name, level_lesson_num, listening):
        """Gets level lesson numbers for listening and reading sessions.

        Args:
            user_name (str): user name
            level_lesson_num (int): level lesson number
            listening (bool): listening session if true, otherwise reading

        Returns:
            Tuple[int, int, int]: level lesson numbers
        """

        df = self.lr_tracking_table[1]
        if user_name not in df["Username"].values:
            new_row = pd.DataFrame([[user_name, 2, 1, 1, 1, 5, 1, 1, 1]], columns=df.columns)
            df = df.append(new_row, ignore_index=True)
            self.lr_tracking_table[1] = df

        if listening:
            selected_columns = df.columns[1:5]
        else:
            selected_columns = df.columns[5:]

        row = df.loc[df["Username"] == user_name]

        for level, column_name in enumerate(selected_columns, start=1):
            val = row[column_name]
            val = val.values[0]
            if val < 30:
                # go to previus level if first lesson and last was selected
                if not level_lesson_num + val:
                    level_num = level - 1
                    lesson_num = 30
                else:
                    level_num = level
                    lesson_num = level_lesson_num + val
                level_lesson_num = level_num * 100 + lesson_num
                break
        
        return level_num, lesson_num, level_lesson_num

    def get_unknown_lesson_num(self, user_name):
        """Gets the next unknown level_lesson_num for an user.

        Args:
            user_name (str): user name (used for worksheet name)

        Returns:
            int: level_lesson_num
        """

        df = self.vocab_df
        ws_names = (
            f"{user_name}-score-1",
            f"{user_name}-score-2",
            f"{user_name}-score-3",
            f"{user_name}-score-4",
        )
        try:
            _, scores_dfs = utils.get_worksheets(S_SPREADSHEET, ws_names)
            if scores_dfs[0].empty:
                raise WorksheetNotFound
                # TODO: this kinda needs optimization, unreadable f. and doc
        except WorksheetNotFound:
            # going for first level
            level_lesson_num = 101
            scores_dfs = []

        # going for next (2. level or more) unknown levels' lessons
        for i, level_scores_df in enumerate(scores_dfs, 1):
            known_words = set(level_scores_df[level_scores_df.columns[0]])
            level_words = set(df.loc[df["Lesson"] // 100 == i, "Korean"])
            unknown_words = level_words - known_words
            ws_missing_words = known_words - level_words
            if ws_missing_words:
                update_needed_msg = (
                    f"Vocabulary is missing words in Level {i} that user has "
                    f"encountered: {ws_missing_words}\n"
                    "Rename those words for user! They're outdated."
                )
                print(update_needed_msg)
            if unknown_words:
                df = df.loc[
                    df["Korean"].isin(unknown_words), ["Lesson", "Korean"]
                ]
                level_lesson_num = int(df.Lesson.min())
                rows = df[df.Lesson == level_lesson_num].values
                unknown_words = ", ".join([row[1] for row in rows])
                missing_words_msg = (
                    "User is missing these words in lesson"
                    f"{level_lesson_num}: {unknown_words}"
                )
                print(missing_words_msg)
                break

        # going for next unknown level
        if level_lesson_num == 1:
            level_lesson_num += 100 + len(scores_dfs) * 100

        return level_lesson_num

    def get_session_number(self, ws_log):
        """Gets the next number in a row for session. Begins with 1.

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs

        Returns:
            int: session number
        """

        session_numbers = ws_log.col_values(4)
        if len(session_numbers) > 1:
            session_number = int(session_numbers[-1]) + 1
        else:
            session_number = 1

        return session_number

    def get_lesson_vocab(self, level_lesson_num):
        """Gets vocabulary for a given lesson.

        Args:
            level_lesson_num (int): level lesson number

        Returns:
            List[pandas.core.frame.Row]: word data (row in ws table)
        """

        filtered_df = self.vocab_df.loc[
            self.vocab_df["Lesson"] == level_lesson_num
        ]
        vocab = list(filtered_df.itertuples(name="Row", index=False))
        random.shuffle(vocab)

        return vocab

    def get_review_vocab(self, guessed_words):
        """Gets vocabulary to review for a given level.

        Args:
            guessed_words (Tuple[str]): guessed words in a level

        Returns:
            List[pandas.core.frame.Row]: word data (row in ws table)
        """

        picked_words = self.get_random_words(guessed_words)
        picked_words_df = self.vocab_df[
            self.vocab_df["Korean"].isin(picked_words)
        ]
        vocab = list(picked_words_df.itertuples(name="Row", index=False))

        return vocab

    def create_users_level_score_ws(self, ws_log, user_name, level_num):
        """Creates scoring for level in the user's worksheet.

        Scoring system takes into account:
         - first guesses in a session
         - by each latter session, the importance of score is being reduced
           by distribution values
         - time of the last guess of a certain word

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            user_name (str): user name (used for worksheet name)
            level_num (int): level number
        """

        score_table = {"✅": 1, "⏭️": 2, "🤔": 2, "🧩": 3, "❌": 4}
        distr_vals = self.get_score_distribution()
        considering_amount = len(distr_vals)
        table_rows = []

        df = pd.DataFrame(ws_log.get_all_records())
        if df.empty:
            return
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
                    previous_row.Date, datetime.now()
                )

                knowledge_marks.reverse()
                knowledge_marks = knowledge_marks[:considering_amount]

                final_score = sum(distr_score) + time_score_penalty

                table_rows.append(
                    [
                        previous_row.Word,
                        final_score,
                        "".join(knowledge_marks),
                        "".join(time_marks),
                    ]
                )

                knowledge_marks = [row.Knowledge]
                knowledge_scores = [score_table[row.Knowledge]]

            # take into account only the first guesses in one session
            elif previous_row.Session_number != row.Session_number:
                knowledge_marks.append(row.Knowledge)
                knowledge_scores.append(score_table[row.Knowledge])

            previous_row = row

        table_rows = sorted(table_rows, key=lambda x: x[1], reverse=True)

        # create worksheet of scores
        ws_scores_list, _ = utils.get_worksheets(
            S_SPREADSHEET,
            (f"{user_name}-score-{level_num}",),
            create=True,
            size=(10_000, 4),
        )
        ws_scores = ws_scores_list[0]
        ws_scores.clear()
        table_rows.insert(0, ["Word", "Score", "Knowledge", "Last_time"])
        ws_scores.append_rows(table_rows)

    def get_score_distribution(self, amount=5, reducer=0.8):
        """Gets score distribution for vocabulary picking.

        The value starts at 1. By each iteration the value is reduced by the
        <reducer>, <amount> tells us how many values (iterations) to do.

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

    def get_time_penalty_data(self, row_date, now_date, coefficient=0.01):
        """Gets time score penalty and emoji visualization for worksheet.

        Args:
            row_date (str): row's (word's) guess date
            now_date (datetime.datetime): current date
            coefficient (float, optional): Penalty coefficient.
                Defaults to 0.01.

        Returns:
            Tuple[int, List[str]]: score penalty, time marks
        """

        # score penalty number
        row_date = datetime.strptime(row_date, "%Y-%m-%d %H:%M:%S")
        days_diff = (now_date - row_date).days
        score_penalty = days_diff * coefficient

        # emoji visualization list
        months, days = divmod(days_diff, 30)
        weeks, days = divmod(days, 7)
        time_marks = ["🌙"] * months + ["📅"] * weeks + ["🌞"] * days

        return score_penalty, time_marks

    def get_random_words(
        self, guessed_words, consider_amount=150, pick_amount=50
    ):
        """Gets randomly chosen words for session.

        Uses linear probability distribution to pick words randomly from
        the most unknown ones to known ones.

        Args:
            guessed_words (Tuple[str]): words that were guessed in a level
            consider_amount (int, optional): Amount of words to consider into
                random picking. Defaults to 150.
            pick_amount (int, optional): Amount of words to pick.
                Defaults to 50.

        Returns:
            numpy.ndarray: picked words
        """

        if len(guessed_words) < consider_amount:
            consider_amount = len(guessed_words)

        if consider_amount < pick_amount:
            pick_amount = consider_amount

        mean = 0
        std = 0.5
        half_norm_distribution = np.abs(
            np.random.normal(loc=mean, scale=std, size=consider_amount)
        )
        half_norm_distribution.sort()
        half_norm_distribution = half_norm_distribution[::-1]
        weights = half_norm_distribution / half_norm_distribution.sum()

        picked_words = np.random.choice(
            guessed_words[:consider_amount],
            p=weights,
            size=pick_amount,
            replace=False,
        )

        return picked_words

    async def run_vocab_session_loop(
        self, interaction, voice, ws_log, session_number, guessed_words, vocab
    ):
        """Runs session loop for vocabulary words.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            voice (discord.voice_client.VoiceClient): voice client channel
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_number (int): session number
            guessed_words (Tuple[str]): words that were previously guessed
            vocab (List[pandas.core.frame.Row]): word data (row in ws table)
        """

        stat_labels = {
            "easy": "✅",
            "effort": "🤔",
            "partial": "🧩",
            "forgot": "❌",
        }
        view = SessionVocabView()

        unchecked_words = {row.Korean for row in vocab}
        unvisited_words = unchecked_words - set(guessed_words)
        stats = []
        msg = None

        while True:

            # prepare output data
            row = vocab[-1]
            guide = row.Korean in unvisited_words
            embed, file, audio_path = self.prepare_word_output(row, guide)
            try:
                voice.play(
                    discord.FFmpegPCMAudio(
                        audio_path,
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            footer_text = f"{len(unchecked_words)} words unchecked remaining."
            embed.set_footer(text=footer_text)

            # sending message
            if not msg:
                msg = await interaction.channel.send(embed=embed, view=view)
            else:
                if guide:
                    await msg.edit(embed=embed, view=view)
                else:  # remove files from previous word
                    await msg.edit(embed=embed, view=view, attachments=[])
            if file:
                await msg.add_files(file)

            # button interactions
            inter = 3
            while inter != 2:  # cuz of selection
                interaction = await self.bot.wait_for(
                    "interaction",
                    check=lambda inter: "custom_id" in inter.data.keys()
                    and inter.user.name == interaction.user.name,
                )
                inter = interaction.data["component_type"]

            button_id = interaction.data["custom_id"]
            if button_id == "repeat":
                continue
            elif button_id == "info":
                unvisited_words.add(row.Korean)
                continue
            elif button_id == "end":
                unchecked_remain = f"{len(unchecked_words)} words unchecked remaining.\n"
                stats_str = self.create_ending_session_stats(stats)
                content = unchecked_remain + stats_str

                await msg.edit(content=content, view=view, embed=None, attachments=[])
                ws_log.append_rows(stats)
                break

            if guide:
                unvisited_words.remove(row.Korean)
            row_to_move = vocab.pop()

            if button_id == "easy":
                vocab.insert(0, row_to_move)
                if row.Korean in unchecked_words:
                    unchecked_words.remove(row.Korean)
            elif button_id == "effort":
                vocab.insert(len(vocab) // 2, row_to_move)
            elif button_id == "partial":
                vocab.insert(len(vocab) // 3, row_to_move)
            elif button_id == "forgot":
                vocab.insert(-len(vocab) // 5, row_to_move)

            # save stats
            stat_time = datetime.now(pytz.timezone(self.timezone))
            stat_time_str = stat_time.strftime("%Y-%m-%d %H:%M:%S")
            stats.append(
                [
                    stat_time_str,
                    row_to_move.Korean,
                    stat_labels[button_id],
                    session_number,
                ]
            )
        
        return msg

    def prepare_word_output(self, row, guide, i=[0]):
        """Prepares variables needed for outputting word data.

        Args:
            List[pandas.core.frame.Row]: word data (row in ws table)
            guide (bool): determines whether additional should be displayed
            i (list, optional): using for discord bug with spoiled words.
                Defaults to [0].

        Returns:
            Tuple[discord.embeds.Embed, discord.file.File, str]: word data
                (embed message, file, path to audio)
        """

        kor_no_num = (
            row.Korean[:-1] if row.Korean[-1].isdigit() else row.Korean
        )
        if kor_no_num not in self.vocab_audio_paths:
            self.create_gtts_audio(kor_no_num)

        max_spaces = 30
        i[0] += 1
        i[0] %= max_spaces
        spoil_spacing = " " * (i[0])
        eng_add = f"; ({row.English_Add})" if row.English_Add else ""
        content = f"**{row.Korean} - {row.Book_English}{eng_add}**"
        if not guide:
            content = f"||{content}{spoil_spacing}||"

        url = "https://korean.dict.naver.com/koendict/#/search?range=all&query"
        url_kor = f"{url}={kor_no_num.replace(' ', '%20')}"
        embed = discord.Embed(title=content, url=url_kor)

        file = None
        if guide:
            ex = f"- {row.Example_KR} ({row.Example_EN})\n" if row.Example_KR else ""
            ex += f"- {row.Example_KR2} ({row.Example_EN2})\n" if row.Example_KR2 else ""
            ex = "\n" + ex if ex else ""
            if row.Explanation:
                embed.add_field(name="", value=f"**{row.Explanation}**{ex}", inline=False)
            file_name_word = row.Korean.replace("?", "")
            if file_name_word in self.vocab_image_paths:
                file = discord.File(self.vocab_image_paths[file_name_word], filename="image.png")

            embed.set_image(url="attachment://image.png")

        return embed, file, self.vocab_audio_paths[kor_no_num]

        # syllables info
        # korean_words = re.findall("[가-힣]+", syl)
        # for word in korean_words:
        #     syl = syl.replace(word, f"\n**{word}**")
        # syl = syl[1:]
        # {examples}\n\n{syl}

        # embed options:
        # color = discord.Color.green(),
        # embed.set_footer(text=f"Rank {rank}")
        # embed.set_thumbnail(url="attachment://image.png")
        # embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://pbs.twimg.com/profile_images/1327036716226646017/ZuaMDdtm_400x400.jpg")
        # embed.set_image(url="attachment://image.png")
        # > {text} >

    def create_gtts_audio(self, word):
        """Creates an audio using google's TTS for a given korean word.

        This is being used for all the words that have no audio from naver's
        dictionary.
        Audio files are saved in data/vocabulary_global_gtts_audio dir, a new
        audio path is added for the given korean word.

        Args:
            word (str): korean word
        """

        src_dir = Path(__file__).parents[0]
        vocab_path = f"{src_dir}/data/vocabulary_global_gtts_audio/"
        stripped_word = word.replace("?", "")
        path = f"{vocab_path}/{stripped_word}.mp3"
        tts = gTTS(word, lang="ko")
        tts.save(path)

        self.vocab_audio_paths[word] = path

    def create_ending_session_stats(self, stats):
        """Gets stats that will be displayed when the session ends.

        Contains total number of guesses, top 5 wrongly guessed words,
        and overall percentages for each guessing mark (that takes only
        the first guess into account).

        Args:
            stats (List[str, str, str, int]): (
                time, word, guess mark, session number
            )

        Returns:
            str: stats
        """

        if not stats:
            return "There weren't any words guessed."

        # get guessing marks count and scoring per word
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
        word_scores_sorted = sorted(
            word_scores.items(), key=lambda x: x[1], reverse=True
        )
        hardest_words = []
        for word, score in word_scores_sorted[:5]:
            if score:
                hardest_words.append(word)
        hardest_words_string = ", ".join(hardest_words)

        # get guessing mark percentages
        total = sum(marks_count.values())
        for mark in marks_count:
            marks_count[mark] = round(marks_count[mark] * 100 / total)

        percentages_summary = (
            f"{marks_count['✅']}%,"
            f"   {marks_count['🤔']}%,"
            f"   {marks_count['🧩']}%,"
            f"   {marks_count['❌']}%"
        )

        total_guesses = f"Total guesses: {len(stats)}\n"
        hardest_words_string = f"Hardest words: {hardest_words_string}\n" if hardest_words_string else ""
        stats = total_guesses + hardest_words_string + percentages_summary
        return stats

    async def get_listening_files(
        self, interaction, level_num, lesson_num, level_lesson_num
    ):
        """Gets listening text and path to audio files.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            level_num (int): level number
            lesson_num (int): lesson number
            level_lesson_num (int): level lesson number

        Returns:
            Tuple[List[str], List[str]]: (audio text, audio paths)
        """

        src_dir = Path(__file__).parents[0]
        lesson_path = f"{src_dir}/data/level_{level_num}/lesson_{lesson_num}"
        audio_path = f"{lesson_path}/listening_audio/*"
        text_path = Path(f"{lesson_path}/listening_text.txt")

        try:
            with open(text_path, encoding="utf-8") as f:
                text = f.read()
            audio_texts = text.split("\n\n")
            audio_paths = sorted(glob(audio_path))
            # sorted it because linux system reverses it
        except Exception:
            msg = (
                f"There are no listening files for {level_lesson_num}. lesson."
            )
            msg = await interaction.followup.send(msg)
            await asyncio.sleep(10.0)
            await msg.delete()
            self.busy_str = ""
            assert False, msg

        return audio_texts, audio_paths

    async def run_listening_session_loop(
        self, interaction, voice, audio_texts, audio_paths
    ):
        """Runs session loop for audio files.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            voice (discord.voice_client.VoiceClient): voice client channel
            audio_texts (List[str]): audio text
            audio_paths (List[str]): audio paths

        Returns:
            bool: listened all tracks
        """

        i = 0
        count_n = len(audio_paths)
        view = SessionListenView(self)

        play_backwards = False
        listened_all = False
        msg = None
        audio_start = 0

        while True:
            if i >= count_n:
                i = 0
            try:
                audio_source = discord.FFmpegPCMAudio(
                    audio_paths[i],
                    executable=self.ffmpeg_path,
                )
                if play_backwards:
                    play_backwards = False
                    if voice.is_playing():
                        voice.stop()
                    audio_start, audio_source = self.move_timestamp(
                        audio_start, audio_source
                    )

                voice.play(audio_source)
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            msg_str = f"{i+1}. lesson out of {count_n}"
            content = f"```{msg_str}\n{audio_texts[i]}```"
            if not msg:
                msg = await interaction.channel.send(
                    content=content, view=view
                )
                audio_start = time.time()
            else:
                await msg.edit(content=content, view=view)

            if i+1 >= count_n:
                listened_all = True

            # button interactions
            interaction = await self.bot.wait_for(
                "interaction",
                check=lambda inter: "custom_id" in inter.data.keys()
                and inter.user.name == interaction.user.name,
            )

            button_id = interaction.data["custom_id"]
            if button_id == "backward":
                play_backwards = True
                continue

            elif button_id == "pauseplay":
                # stop, resume only.. if doesnt work
                pause_start = time.time()
                button_id2 = None
                while button_id2 != "pauseplay":
                    interaction = await self.bot.wait_for(
                        "interaction",
                        check=lambda inter: "custom_id" in inter.data.keys()
                        and inter.user.name == interaction.user.name,
                    )
                    button_id2 = interaction.data["custom_id"]
                pause_end = time.time()
                audio_start += pause_end - pause_start
                continue

            elif button_id == "next":
                if voice.is_playing():
                    voice.stop()
                i += 1

            elif button_id == "repeat":
                if voice.is_playing():
                    voice.stop()

            elif button_id == "end":
                if voice.is_playing():
                    voice.stop()
                content = f"```{msg_str}\nListening sessions has ended.```"
                await msg.edit(content=content, view=view)
                break

            audio_start = time.time()
        
        return listened_all, msg

    def move_timestamp(self, audio_start, audio_source):
        """Moves timestamp (audio frames) in audio source. Updates start time.

        Args:
            audio_start (float): starting timestamp
            audio_source (discord.player.FFmpegPCMAudio): audio source

        Returns:
            Tuple[float, discord.player.FFmpegPCMAudio]: (
                new start time, audio source
            )
        """

        time_now = time.time()
        time_difference = time_now - audio_start
        if time_difference > 10:
            start_timestamp = time_difference - 10
            reads_amount = int(start_timestamp * 50)

            # one second is 50 read() calls, 1 read = 20ms   24s
            for _ in range(reads_amount):
                audio_source.read()

        # update audio_start, because next timestamp move
        # would not be consistent with the original one
        audio_start += 10

        return audio_start, audio_source

    @discord.ext.commands.Cog.listener()
    async def on_ready(self):
        """Executes when the cog is loaded, it initializes timezone.

        This could have been initialized in __init__ method, but to make it
        consistent with all cogs, on_ready is being used for config loading.
        Surveillance module needs to load it there."""

        with open("config.json", encoding="utf-8") as file:
            self.timezone = json.load(file)["timezone"]
        self.bot.add_view(MenuSessionsView(self))

    @discord.app_commands.command(name="vocab")
    @discord.app_commands.describe(level_lesson_num="Select session type")
    @discord.app_commands.choices(level_lesson_num=VOCAB_CHOICES)
    async def _vocab_listening(self, interaction, level_lesson_num: discord.app_commands.Choice[int], custom_number: int=0):
        await self.vocab_listening(interaction, level_lesson_num.value, custom_number)

    async def vocab_listening(self, interaction, session_type: int, level_lesson_num: int=0):
        """Starts listening vocabulary exercise.

        There are 3 types of level_lesson_num in vocab_listening session:
         - One ("1") starts the next user's unknown lesson
         - Pure hundreds ("100", ..., "400") starts review session of level
           (Hundred decimals represent level)
         - Hundreds up to 30 ("101", ..., "130") starts lesson session
           (Ten decimals represent level's lesson)
        """

        msgs = []
        if self.busy_str:
            await interaction.response.send_message(
                f"The bot is busy with {self.busy_str}!", delete_after=5
            )
            return
        else:
            await interaction.response.send_message(
                "...Setting up vocab session...", delete_after=5
            )

        voice = await self.get_voice(interaction)
        if not voice:
            return
        
        self.busy_str = "vocab session"

        level_lesson_num = level_lesson_num if level_lesson_num else session_type
        (
            level_num,
            lesson_num,
            level_lesson_num,
        ) = await self.get_level_lesson_nums(interaction, level_lesson_num)

        # get users stats worksheet
        user_name = interaction.user.name
        ws_logs, scores_dfs = utils.get_worksheets(
            S_SPREADSHEET,
            (f"{user_name}-{level_num}", f"{user_name}-score-{level_num}"),
            create=True,
            size=(10_000, 4),
        )
        ws_log = ws_logs[0]
        if not ws_log.get_values("A1"):  # create header if missing
            ws_log.append_row(["Date", "Word", "Knowledge", "Session_number"])

        scores_df = scores_dfs[1]
        if scores_df.empty:
            guessed_words = ()
        else:
            guessed_words = tuple(scores_df[scores_df.columns[0]])

        session_number = self.get_session_number(ws_log)

        if lesson_num:
            vocab = self.get_lesson_vocab(level_lesson_num)
            msg = (
                f"Vocabulary Level {level_num} - Lesson {level_lesson_num}, "
                f"session: {session_number}"
            )
        else:
            if not guessed_words:
                msg = await interaction.channel.send(
                    "You haven't guessed any words in selected level!"
                )
                msgs.append(msg)
                await asyncio.sleep(60)
                for msg in msgs:
                    await msg.delete()
                self.busy_str = ""
                return
            vocab = self.get_review_vocab(guessed_words)
            msg = (
                f"Vocabulary Review Level {level_num}, "
                f"session: {session_number}"
            )
        msg = await interaction.channel.send(msg)
        msgs.append(msg)

        await self.bot.change_presence(
            activity=discord.Game(name="Vocabulary")
        )

        msg = await self.run_vocab_session_loop(
            interaction, voice, ws_log, session_number, guessed_words, vocab
        )
        msgs.append(msg)

        self.create_users_level_score_ws(ws_log, user_name, level_num)
        self.busy_str = ""

        await asyncio.sleep(60)

        for msg in msgs:
            await msg.delete()

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=self.bot.activity_str,
            ),
            status=discord.Status.online,
        )

    @discord.app_commands.command(name="listen")
    @discord.app_commands.describe(level_lesson="Select session type")
    @discord.app_commands.choices(level_lesson=LISTEN_CHOICES)
    async def _listening(self, interaction, level_lesson: discord.app_commands.Choice[int], custom_number: int=0):
        await self.listening(interaction, level_lesson.value, custom_number)

    async def listening(self, interaction, level_lesson: int, level_lesson_num: int=0):
        """Starts listening exercise.

        There are 2 types of level_lesson in listening sessions:
         - One ("1") starts the latest lesson which has all words visited
         - Hundreds up to 30 ("101", ..., "130") starts specific lesson
           (Hundred decimals represent level)
           (Ten decimals represent level's lesson)
        """

        if self.busy_str:
            await interaction.response.send_message(
                f"The bot is busy with {self.busy_str}!", delete_after=5
            )
            return
        else:
            await interaction.response.send_message(
                "...Setting up listening session...", delete_after=5
            )

        voice = await self.get_voice(interaction)
        if not voice:
            return
        
        self.busy_str = "listening session"

        level_lesson_num = level_lesson_num if level_lesson_num else level_lesson
        if level_lesson_num:
            level_num = level_lesson_num // 100
            lesson_num = level_lesson_num % 100
        else:
            (
                level_num,
                lesson_num,
                level_lesson_num,
            ) = self.get_lr_level_lesson_nums(interaction.user.name, level_lesson, True)

        audio_texts, audio_paths = await self.get_listening_files(
            interaction, level_num, lesson_num, level_lesson_num
        )

        msgs = []
        msg = await interaction.channel.send(f"Listening Lesson {level_lesson_num}")
        msgs.append(msg)

        await self.bot.change_presence(activity=discord.Game(name="Listen"))

        listened_all, msg = await self.run_listening_session_loop(
            interaction, voice, audio_texts, audio_paths
        )
        msgs.append(msg)
        
        if not level_lesson and listened_all:
            df = self.lr_tracking_table[1]
            row_index = df[df['Username'] == interaction.user.name].index[0]
            df.loc[row_index, f"Listening {level_num}"] = lesson_num + 1
            self.lr_tracking_table[1] = df
            utils.update_worksheet(self.lr_tracking_table[0], df)
        
        self.busy_str = ""
        await asyncio.sleep(60)

        for msg in msgs:
            await msg.delete()

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=self.bot.activity_str,
            ),
            status=discord.Status.online,
        )

    @discord.app_commands.command(name="read")
    @discord.app_commands.describe(level_lesson="Select session type")
    @discord.app_commands.choices(level_lesson=READ_CHOICES)
    async def _reading(self, interaction, level_lesson: discord.app_commands.Choice[int], custom_number: int=0):
        await self.reading(interaction, level_lesson.value, custom_number)

    async def reading(self, interaction, level_lesson: int, level_lesson_num: int=0):
        """Starts reading exercise.

        There are 2 types of level_lesson_num in reading sessions:
         - One ("1") starts the latest lesson which has all words visited
         - Hundreds up to 30 ("101", ..., "130") starts specific lesson
           (Hundred decimals represent level)
           (Ten decimals represent level's lesson)
        """

        await interaction.response.send_message(
            "...Setting up reading session...", delete_after=5
        )

        level_lesson_num = level_lesson_num if level_lesson_num else level_lesson
        if level_lesson_num:
            level_num = level_lesson_num // 100
            lesson_num = level_lesson_num % 100
        else:
            (
                level_num,
                lesson_num,
                level_lesson_num,
            ) = self.get_lr_level_lesson_nums(interaction.user.name, level_lesson, False)

        # load text file
        src_dir = Path(__file__).parents[0]
        lesson_path = f"{src_dir}/data/level_{level_num}/lesson_{lesson_num}"
        text_path = Path(f"{lesson_path}/reading_text.txt")
        try:
            with open(text_path, encoding="utf-8") as f:
                reading_text = f.read()
        except Exception as exc:
            msg = f"There are no reading files for {level_lesson_num}. lesson."
            msg = await interaction.followup.send(msg)
            await asyncio.sleep(10.0)
            await msg.delete()
            raise discord.ext.commands.CommandError(msg) from exc
        
        if not level_lesson:
            df = self.lr_tracking_table[1]
            user_row = df[df['Username'] == interaction.user.name].index[0]
            df.loc[user_row, f"Reading {level_num}"] = lesson_num + 1
            self.lr_tracking_table[1] = df
            utils.update_worksheet(self.lr_tracking_table[0], df)

        msg1 = await interaction.channel.send(f"Reading Lesson {level_lesson_num}")
        msg2 = await interaction.channel.send(f"```{reading_text}```")
        await asyncio.sleep(15 * 60)
        await msg1.delete()
        await msg2.delete()

    @discord.app_commands.command(name="help")
    async def help(self, interaction, private_visibility: bool=False):
        """Sends message with guide on how to use the bot."""

        embed = discord.Embed(title="❔ Guide on how to use the bot")

        text_vocab_interact = """
✅ - know without thinking
🤔 - know after thinking
🧩 - know only partially
❌ - not know
🔁 - repeat the audio
📄 - display additional info about the word
🔚 - end the session
        """
        text_listen_interact = """
⏪ - rewind by 10 seconds
⏸️ - pause
⏩ - next track
🔁 - repeat track
🔚 - end the session
        """
        text_notes = """
- If you encounter a word for the first time, it displays all the info about the word. If you have already encountered it, this info will be hidden, only the word with translation will be there, but spoiled. To unspoil it, click on the black text. If you want to see the additional info, use the 📄 button.
- If the word has number attached at the end, it means it can have multiple meanings. Each number represents one meaning.
- Listening sessions starts from 102 and reading sessions from 105 lessons.
- Listening/Reading sessions require you to understand lesson's corresponding grammar that is described inside the Google Doc's link below
- Vocab/Listening session messages will be deleted 1 minute after the session ends. Reading session ends in 15 minutes.
        """
        text_links = """
- [Level 1 Grammar](https://docs.google.com/document/d/1BTBgvSy7VGwoD1AD4lCqpy0_7Zn-U_6smeU0GKdFjoU/edit?usp=sharing) (Google Doc - grammar reference (for listening/reading))
- [User's stats](https://docs.google.com/spreadsheets/d/1wFbxnhwc2BQAEAL_KNCPfBYoLwhdcGR5FuVKxlwjSJg/edit?usp=sharing) (Google Sheet - user's logs and scores for every word)
- [Vocabulary](https://docs.google.com/spreadsheets/d/1mhYVWtqUWF-vVjwCz3cvlhZxH6GjfU6XyLVd2lNcWe0/edit?usp=sharing) (Google Sheet -  vocabulary list)

**Select YOUR sessions in the dropdown below**"""

        embed.add_field(name="Interactions for vocab session:", value=text_vocab_interact, inline=False)
        embed.add_field(name="Interactions for listening session:", value=text_listen_interact, inline=False)
        embed.add_field(name="Notes:", value=text_notes, inline=False)
        embed.add_field(name="Links:", value=text_links, inline=False)

        view = MenuSessionsView(self)
        # ephemeral=private_visibility
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    """Loads up this module (cog) into the bot that was initialized
    in the main function.

    Args:
        bot (__main__.MyBot): bot instance initialized in the main function
    """

    await bot.add_cog(
        Language(bot), guilds=[discord.Object(id=os.environ["GUILD_ID"])]
    )
