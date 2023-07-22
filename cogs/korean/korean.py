"""This module serves to help studying korean vocabulary and listening.

Function hierarchy:
vocab_listening
    _get_vocab_table
    _get_vocab_audio_paths
    async get_voice
    get_level_lesson
    get_session_number
    get_lesson_vocab
    get_review_vocab
        create_users_level_score_ws
            get_score_distribution
            get_time_penalty_data
        get_random_words
    async run_vocab_session_loop
        create_ending_session_stats

listening
    async get_voice
    get_listening_files
        get_level_lesson
    async run_listening_session_loop
    ?async pause
    ?async resume
    async on_ready

reading

"""

import json
import os
import pickle
import random
import re
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

# class Word:
#     def __init__(self, row):

#     row.Book_English, row.Korean, (row.Example_EN, row.Example_KR)
#     Rank
#     English_Add
#     Explanation
#     Syllables
#     Example_EN2
#     Example_KR2
class Language(commands.Cog):
    def __init__(self, bot):
        self.vocab_audio_paths, self.vocab_image_paths = self._get_vocab_audio_paths()
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

        # ignore rows with no Lesson cell filled (duplicates)
        vocab_df = vocab_dfs[0]
        vocab_df["Lesson"].replace("", np.nan, inplace=True)
        vocab_df.dropna(subset=["Lesson"], inplace=True)

        return vocab_df

    def _get_vocab_audio_paths(self):
        """Gets vocab's local audio paths of all levels.

        Not all words have audio file, it will load only the ones that are
        present in vocabulary_audio directory that is in each of the lessons.
        Just so we dont have to read through all the lessons every time this
        module is loaded, the audio paths are stored in pickle file. (cached)
        Audio files are located in data/level_x/lesson_x/vocabulary_audio dir.

        ALSO IMAGES

        Returns:
            Dict[str, str]: words and their audio paths (word being the key)
        """

        src_dir = Path(__file__).parents[0]
        audio_pickle_path = f"{src_dir}/data/vocab_audio_path.pickle"
        if os.path.isfile(audio_pickle_path):
            with open(audio_pickle_path, "rb") as handle:
                audio_paths_labelled = pickle.loads(handle.read())
        else:
            audio_paths = glob(f"{src_dir}/data/*/*/vocabulary_audio/*")
            audio_paths_labelled = {}
            for audio_path in audio_paths:
                word = Path(audio_path).stem
                audio_paths_labelled[word] = audio_path

            with open(audio_pickle_path, "wb") as file:
                pickle.dump(audio_paths_labelled, file)

        image_pickle_path = f"{src_dir}/data/vocab_image_path.pickle"
        if os.path.isfile(image_pickle_path):
            with open(image_pickle_path, "rb") as handle:
                image_paths_labelled = pickle.loads(handle.read())    
        else:
            audio_paths = glob(f"{src_dir}/data/*/*/vocabulary_images/*")
            image_paths_labelled = {}
            for audio_path in audio_paths:
                word = Path(audio_path).stem
                word = word[:-1]
                image_paths_labelled[word] = audio_path

            with open(image_pickle_path, "wb") as file:
                pickle.dump(image_paths_labelled, file)

        return audio_paths_labelled, image_paths_labelled

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

    def get_level_lesson(self, interaction, level_lesson_number):
        """Gets level and lesson numbers with validation checks.

        If the given level_lesson_number is invalid, it returns zeros.
        There are 3 types of level_lesson_number:
         - One ("1") finds the next user's unknown lesson (also prints words)
         - Pure hundreds ("100", ..., "400") review session of one levels words
         - Hundreds up to 30 ("101", ..., "130") specific lesson number

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            level_lesson_number (int): level lesson number

        Returns:
            Tuple[int, int]: (level_number, lesson_number)
        """

        # get next not fully known level_lesson_number
        if level_lesson_number == 1:
            df = self.vocab_df
            user_name = interaction.user.name
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

            # going for next levels' lessons
            for i, scores_df in enumerate(scores_dfs, 1):
                known_words = set(scores_df[scores_df.columns[0]])
                level_words = set(df.loc[df["Lesson"] // 100 == i, "Korean"])
                unknown_words = level_words - known_words
                if unknown_words:
                    df = df.loc[df["Korean"].isin(unknown_words), ["Lesson", "Korean"]]
                    level_lesson_number = int(df.Lesson.min())
                    rows = df[df.Lesson == level_lesson_number].values
                    unknown_words = ", ".join([row[1] for row in rows])
                    print(f"Unknown words in lesson {level_lesson_number}: {unknown_words}")
                    break

            # going for next level
            if level_lesson_number == 1:
                level_lesson_number += 100 + len(scores_dfs) * 100

        # get level and lesson number with validation check
        level_number = level_lesson_number // 100
        lesson_number = level_lesson_number % 100
        if not (0 < level_number < 5 and lesson_number < 31):
            return 0, 0

        return level_number, lesson_number

    def get_session_number(self, ws_log, session_column):
        """Gets ordinal number of lesson or review of session. Begins with 1.

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_column (int): column index used to retrieve session number

        Returns:
            int: ordinal session number
        """

        session_numbers = ws_log.col_values(session_column)
        if len(session_numbers) > 1:
            session_number = int(session_numbers[-1]) + 1
        else:
            session_number = 1

        return session_number

    def get_lesson_vocab(self, level_lesson_number):
        """Gets vocabulary for a given lesson.

        Hundred decimals represent level of the vocabulary. 
        The other two numbers range from 1 to 30 that represent a lesson.

        Args:
            level_lesson_number (int): lesson number

        Returns:
            List[Tuple[str, str, Tuple[str, str]]]: [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
        """

        vocab = []
        for row in self.vocab_df.itertuples():
            if not row.Lesson:
                continue
            if row.Lesson > level_lesson_number:
                break
            if row.Lesson == level_lesson_number:
                vocab.append(
                    (
                        row.Book_English, 
                        row.Korean, 
                        (row.Example_EN, row.Example_KR), 
                        row.English_Add, 
                        row.Explanation, 
                        row.Syllables, 
                        row.Example_EN2, 
                        row.Example_KR2,
                        row.Rank
                    )
                )

        # korean, english, explanation, syllables, rank
        # English_Add	Explanation	Syllables	Example_EN2	Example_KR2
        random.shuffle(vocab)

        return vocab

    def get_review_vocab(self, level_number, user_name):
        """Gets vocabulary review of all guessed words for a given level.

        Args:
            level_number (int): level number
            user_name (str): user name (used for worksheet name)

        Returns:
            List[Tuple[str, str, Tuple[str, str]]]: [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
        """

        # get guessed words
        _, scores_dfs = utils.get_worksheets(
            "Korea - Users stats",
            (f"{user_name}-score-{level_number}",),
        )
        scores_df = scores_dfs[0]
        guessed_words = tuple(scores_df[scores_df.columns[0]])

        picked_words = self.get_random_words(guessed_words)

        # getting english data from worksheet
        korean_word_data = pd.Series(
            zip(
                self.vocab_df.Book_English,
                self.vocab_df.Example_EN,
                self.vocab_df.Example_KR,
                self.vocab_df.English_Add,
                self.vocab_df.Explanation,
                self.vocab_df.Syllables,
                self.vocab_df.Example_EN2,
                self.vocab_df.Example_KR2,
                self.vocab_df.Rank
            ),
            index=self.vocab_df.Korean
            ).to_dict()

        # korean, english, explanation, syllables, rank

        # creating vocab list with all of the content
        vocab = []
        for kor in picked_words:
            vocab.append(
                (
                    korean_word_data[kor][0],
                    korean_word_data[kor][1:3],
                    korean_word_data[kor][3],
                    korean_word_data[kor][4],
                    korean_word_data[kor][5],
                    korean_word_data[kor][6],
                    korean_word_data[kor][7],
                    korean_word_data[kor][8]
                )
            )

        return vocab

    def create_users_level_score_ws(self, ws_log, user_name, level_number):
        """Gets score of words and visualizing list of rows for worksheet.

        Scoring system takes into account: 
         - first guesses in a session, by each latter session, the importance
           of score is being reduced by distribution values
         - time of the last guess of a certain word

        Args:
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            user_name (str): user name (used for worksheet name)
            level_number (int): level number

        Returns:
            Tuple[List[str, int, str, str]]: (
                word, score, (knowledge_marks, time_marks)
            )
        """

        score_table = {"✅": 1, "⏭️": 2, "❌": 4}
        distr_vals = self.get_score_distribution()
        considering_amount = len(distr_vals)
        table_rows = []

        df = pd.DataFrame(ws_log.get_all_records())
        df = df.sort_values(["Word", "Date"])
        previous_row = df.iloc[0]
        knowledge_marks = [previous_row.Knowledge]
        knowledge_scores = [score_table[previous_row.Knowledge]]
        df.drop(0)
        df = pd.concat([df, pd.DataFrame({"Word": ["NAN"], "Knowledge": ["❌"]})])  # for the last word

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
        randomly from the most unknown ones to the more known ones.

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

    def create_embed(self, word_data):
        eng, kor, ex, eng_add, expl, syl, exs2en, exs2kr, rank = word_data

        url = "https://korean.dict.naver.com/koendict/#/search?range=all&query="
        title = f"{kor} - {eng}; ({eng_add})"
        embed = discord.Embed(
            title = title,
            url = url + kor,
        )
        examples = f"{ex[1]} = {ex[0]}\n{exs2kr} = {exs2en}"

        korean_words = re.findall("[가-힣]+", syl)
        for word in korean_words:
            syl = syl.replace(word, f"\n**{word}**")
        syl = syl[1:]

        text = f"**{expl}**\n\n{examples}"  # \n\n{syl}
        embed.add_field(name="", value=text, inline=False)
        
        kk = "C:/Users/pmark/Desktop/Caroline-bot/cogs/korean/data/level_1/lesson_1/vocabulary_images/a1.png"
        file = discord.File(kk, filename="image.png")
        # file = discord.File(f"{self.vocab_image_paths[f'{kor}']}", filename="image.png")

        embed.set_image(url="attachment://image.png")
        return embed, file

        # color = discord.Color.green(),
        # embed.set_footer(text=f"Rank {rank}")
        # embed.set_thumbnail(url="attachment://image.png")
        # embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://pbs.twimg.com/profile_images/1327036716226646017/ZuaMDdtm_400x400.jpg")
        # embed.set_image(url="attachment://image.png")
        # > {text} >
        # await interaction.response.send_message(file=file, embed=embed)
    

    async def run_vocab_session_loop(self, interaction, voice, ws_log, session_number, lesson_number, vocab):
        """Runs session loop for vocabulary words.

        Args:
            interaction (discord.interactions.Interaction): slash cmd context
            voice (discord.voice_client.VoiceClient): voice client channel
            ws_log (gspread.worksheet.Worksheet): worksheet table of logs
            session_number (int): session number
            lesson_number (int): indicates whether session is lesson or review
            vocab (List[Tuple[str, str, Tuple[str, str]]]): [
                english word,
                korean word,
                (english usage example, korean usage example)
            ]
            
        """

        i = 1
        max_spaces = 30  # using for discord bug with spoiled words
        unchecked = set(vocab)
        msg_str = f"{len(unchecked)} words remaining."
        stat_labels = {"easy": "✅", "medium": "⏭️", "hard": "❌"}
        view = SessionVocabView()
        stats = []

        src_dir = Path(__file__).parents[0]
        vocab_path = f"{src_dir}/data/vocab_sources/lessonlol/vocabulary_audio/"

        embed, file = self.create_embed(vocab[-1])

        await interaction.channel.send(file=file, embed=embed)

        msg = await interaction.channel.send(msg_str)
        while True:
            embed, file = self.create_embed(vocab[-1])
            eng, kor, ex, eng_add, expl, syl, exs2en, exs2kr, rank = vocab[-1]
            example = f"\n{ex[1]} = {ex[0]}" if ex[0] else ""
            kor_no_num = kor[:-1] if kor[-1].isdigit() else kor

            # handling word with audio
            spoil_spacing = " " * (i % max_spaces)
            eng_part = f"{eng:20}{spoil_spacing}{example}"
            if kor_no_num not in self.vocab_audio_paths:
                path = f'{vocab_path}/{kor_no_num}.mp3'
                tts = gTTS(kor_no_num, lang='ko')
                tts.save(path)
                self.vocab_audio_paths[kor_no_num] = path

            msg_display = f"||{kor} = {eng_part}||"
            try:
                voice.play(
                    discord.FFmpegPCMAudio(
                        self.vocab_audio_paths[kor_no_num],
                        executable=self.ffmpeg_path,
                    )
                )
            except Exception as err:
                print(f"Wait a bit, repeat the unplayed audio!!! [{err}]")

            msg_str = f"{len(unchecked)} words remaining"
            content = f"{msg_str}\n{msg_display}"
            await msg.edit(content=content, view=view)

            # wait for interaction
            i += 1
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
                continue

            # partial
            word_to_move = vocab.pop()
            if button_id == "easy":
                vocab.insert(0, word_to_move)
                if word_to_move in unchecked:
                    unchecked.remove(word_to_move)
            elif button_id == "effort":
                vocab.insert(len(vocab) // 2, word_to_move)
            elif button_id == "forgot":
                vocab.insert(- len(vocab) // 5, word_to_move)
            elif button_id == "end":
                stats_str = self.create_ending_session_stats(stats)
                content = f"{msg_str}\n{stats_str}"
                await msg.edit(content=content, view=view)
                ws_log.append_rows(stats)
                break

            time = datetime.now(pytz.timezone(self.timezone))
            time_str = time.strftime("%Y-%m-%d %H:%M:%S")
            stats.append(
                [
                    time_str,
                    word_to_move[1],
                    stat_labels[button_id],
                    session_number,
                ]
            )
    @app_commands.command(name="lel")
    async def embedmsg(self, interaction):

        await interaction.response.send_message(
            "...Setting up vocab session..."
        )
        # Example_EN	Example_KR
        # Example_EN2	Example_KR2
        # Explanation	Syllables
        # korean, english, explanation, syllables, rank
        url = "https://korean.dict.naver.com/koendict/#/search?range=all&query="
        korean = "편하다"
        title = f"{korean} - {english}"
        explanation = "**Explanation. Lorem ipsum.Explanation. Lorem ipsum.Explanation. Lorem ipsum**"
        syllables = {"qwe": 123, "asd": 234}
        rank = 234
        embed = discord.Embed(
            title = title,
            description = explanation,
            url = url + korean,
        )
        for syllable in syllables:
            embed.add_field(name="", value=f"**{syllable}** - {syllables[syllable]}")
        embed.set_footer(text="Rank 342")
        # color = discord.Color.green(),

        file = discord.File("감사하다e.png", filename="image.png")
        # embed.set_thumbnail(url="attachment://image.png")
        embed.set_image(url="attachment://image.png")
        # embed.set_footer(text="Rank 342")
        # embed.add_field(name="", value="강강 ||강강강강강|| 강강강강 강강강강 (inline ~~with~~ Field  with Field 1)", inline=False)
        # embed.add_field(name="", value="**강**It is `inline` with Field 1\n**한** (It _is_ inline __with__ Field) 2\nasdads")
        # embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://pbs.twimg.com/profile_images/1327036716226646017/ZuaMDdtm_400x400.jpg")
        # embed.set_image(url="attachment://image.png")
        # embed.set_footer(text="Nonee", icon_url="attachment://image.png")
        # > {text} >
        # await interaction.response.send_message(file=file, embed=embed)
        await interaction.channel.send(file=file, embed=embed)

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
        marks_count = {"✅": 0, "⏭️": 0, "❌": 0}
        scoring = {"✅": 0, "⏭️": 1, "❌": 2}
        word_scores = {}
        for _, word, mark, _ in stats:
            if word not in word_scores:
                word_scores[word] = scoring[mark]
                marks_count[mark] += 1
            else:
                word_scores[word] += scoring[mark]

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
            marks_count[mark] = round(marks_count[mark] * 100 / total, 1)

        percentages_summary = (
            f"{marks_count['✅']}%,"
            f"   {marks_count['⏭️']}%,"
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
            # TODO ChatGPT Tokens first use!
            # TODO polish whole module + apply pylint
            # TODO ADD backward button (10s)
            if button_id == "pauseplay":
                # TODO FIX: pauseplay button
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
        """Start listening vocabulary exercise."""

        await interaction.response.send_message(
            "...Setting up vocab session..."
        )
        voice = await self.get_voice(interaction)
        await self.bot.change_presence(
            activity=discord.Game(name="Vocabulary")
        )

        level_number, lesson_number = self.get_level_lesson(interaction, level_lesson_number)
        level_lesson_number = level_number * 100 + lesson_number
        if not level_number and not lesson_number:
            msg = "Wrong level lesson number!"
            await interaction.followup.send(msg)
            assert False, msg

        # get users stats worksheet
        columns = 4
        ws_logs, _ = utils.get_worksheets(
            "Korea - Users stats",
            (f"{interaction.user.name}-{level_number}",),
            create=True,
            size=(10_000, columns)
        )
        ws_log = ws_logs[0]
        if not ws_log.get_values("A1"):
            ws_log.append_row(["Date", "Word", "Knowledge", "Session_number"])

        session_number = self.get_session_number(ws_log, columns)

        if lesson_number:
            vocab = self.get_lesson_vocab(level_lesson_number)
            await interaction.followup.send(f"Lesson {level_lesson_number}")
        else:
            vocab = self.get_review_vocab(level_number, interaction.user.name)
            await interaction.followup.send(f"Level {level_number} Review session: {session_number}")

        await self.run_vocab_session_loop(interaction, voice, ws_log, session_number, lesson_number, vocab)

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
