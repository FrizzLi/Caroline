import random
import discord
from discord.ext import commands
import youtube_dl
import pandas as pd
import re
import gspread
import pytz
from cogs.music.player_view import get_readable_duration
from cogs.music.source import ytdl


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(brief="Rolls a number between 1 and 100. (roll 1000)")
    async def roll(self, ctx, max_=100):
        rolled_number = f"{str(random.randint(1, max_))} (1 - {str(max_)})"
        await ctx.send(f"{ctx.message.author.mention} rolls {rolled_number}")

    @commands.command(brief="Enables Python interactive shell.")
    async def python(self, ctx):
        await ctx.send(f'Python mode activated! Exit by "{ctx.prefix}"')
        await self.bot.change_presence(activity=discord.Game(name="Python"))

        def check(message):
            return message.channel == ctx.channel

        msg = await self.bot.wait_for("message", check=check)
        ans = 0

        while not msg.content.startswith(f"{ctx.prefix}"):
            try:  # evaluating input with value return
                ans = eval(msg.content)
                await ctx.send(ans)
            except Exception:  # executing input without return
                try:
                    exec(msg.content)
                except Exception as e2:  # invalid input
                    await ctx.send(e2)
            msg = await self.bot.wait_for("message", check=check)

        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening, name=f"{ctx.prefix}help"
            )
        )
        await ctx.send("Python mode deactivated!")

    @commands.command(brief="Deletes specified number of messages. (clearr 5)")
    async def clearr(self, ctx, amount=5):
        channel = ctx.message.channel
        async for message in channel.history(limit=int(amount) + 1):
            await message.delete()

    @commands.command(brief="?choose black pink white.")
    async def choose(self, ctx, *args):
        await ctx.send(random.choice(args))

    @commands.command(brief="Replies specified message.++")
    async def echo(self, ctx, *args):
        """ For voice put '-v' after echo. E.g. ?echo -v Hello world!"""
        # TODO: after voice is done, make TTS

        if args[0] == "-v":
            await ctx.send(" ".join(args[1:]), tts=True)
        else:
            await ctx.send(" ".join(args))

    @commands.command(brief="Logouts bot from the server.")
    async def close(self, ctx):
        await self.bot.close()

    def get_ytb_cmd_data(self, elem):
        search_expr = elem.content[6:]
        data = ytdl.extract_info(url=search_expr, download=False)
        if 'entries' in data:
            if len(data['entries']) == 1:  # for search single song
                data['title'] = data['entries'][0]['title']
                data['webpage_url'] = data['entries'][0]['webpage_url']

        tz_aware_date = elem.created_at.astimezone(pytz.timezone('Europe/Berlin'))
        data['title'] = data['title'].replace('"',"'")
        data['webpage_url'] = data['webpage_url'].replace('"',"'")

        datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")  # windows only #
        author = elem.author.name
        title = data['title']
        webpage_url = data['webpage_url']
        # f"""=HYPERLINK("{data['webpage_url']}","{data['title']}")""",

        return datetime, author, title, webpage_url

    def get_ytb_track_data(self, row):
        data = ytdl.extract_info(url=row.URL, download=False)
        if 'entries' in data:
            if len(data['entries']) == 1:  # for search single song
                data['duration'] = data['entries'][0]['duration']
                data['view_count'] = data['entries'][0]['view_count']
                data['categories'] = data['entries'][0]['categories']

        duration = get_readable_duration(data['duration']) if 'duration' in data else ""
        views = f"{data['view_count']:,}" if 'view_count' in data else ""
        categories = ', '.join(data['categories']) if 'categories' in data else ""

        return duration, views, categories

    @commands.command()
    async def history(self, ctx, limit: int):
        """Saves history of songs into Google Sheets."""

        table_data = []
        i = 0
        async for elem in ctx.channel.history(limit=limit):
            if elem.content.startswith("___") and (elem.author.name == 'GLaDOS' or elem.author.name == 'Caroline'):  # TODO: remove Caroline
                break
            i += 1

            # retrieve data from basic command - old bots (Groovy, Rhytm)
            if elem.content.lower()[1:].startswith("play"):
                try:
                    datetime, author, title, webpage_url = self.get_ytb_cmd_data(elem)
                except Exception as e:
                    print(f"{i}. Error: {e}. It is a playlist or there's other problem. search_expr: {search_expr}")
                    continue

                rec = datetime, author, title, webpage_url
                table_data.append(rec)
                print(f"{i}. (old) downloaded: {rec}")

            # retrieve data from slash command - new bot (GLaDOS)
            elif (elem.author.name == 'GLaDOS' or elem.author.name == 'Caroline') and elem.embeds and elem.embeds[0].description.startswith('Queued'):
                msg = elem.embeds[0].description
                matching_expr = r"Queued \[(.+?)\]\((.+?)\) \[<@!?(\d+)>]"

                result = re.match(matching_expr, msg)
                title = result[1].replace('"',"'")
                webpage_url = result[2].replace('"',"'")
                author_id = result[3]
                author = await ctx.guild.fetch_member(author_id).name
                tz_aware_date = elem.created_at.astimezone(pytz.timezone('Europe/Berlin'))
                datetime = tz_aware_date.strftime("%Y-%m-%d %#H:%M:%S")  # %Z%z

                rec = datetime, author, title, webpage_url
                table_data.append(rec)
                print(f"{i}. (new) downloaded: {rec}")

        # save to gsheets
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open("Discord Music Log")
        wks = sh.worksheet("Commands Log")  # for creation sh.add_worksheet("Commands Log", df.shape[0], df.shape[1])
        df = pd.DataFrame(table_data, index=None)
        wks_formatted_rows = [df.columns.values.tolist()] + df.values.tolist()
        wks.append_rows(wks_formatted_rows, value_input_option='USER_ENTERED')

        await ctx.send("___Messages saved up to this point.___")

    @commands.command()
    async def createStats(self, ctx):
        """Saves history of songs into Google Sheets."""

        # get pandas format
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open("Discord Music Log")
        cmd_wks = sh.worksheet("Commands Log")
        cmd_df = pd.DataFrame(cmd_wks.get_all_records())
        cmd_df['Date'] = pd.to_datetime(cmd_df['Date'])
        now = pd.Timestamp.now()

        # preparation
        name_offset_dict = {
            "Track Log (Lifetime)": False,
            "Track Log (Year)": pd.DateOffset(years=1),
            "Track Log (3 Months)": pd.DateOffset(months=3),
            "Track Log (Month)": pd.DateOffset(months=1),
            "Track Log (Week)": pd.DateOffset(weeks=1)
        }

        for sheet_name, offset in name_offset_dict.items():
            print(sheet_name, "begins")
            track_wks = sh.worksheet(sheet_name)
            track_df = pd.DataFrame(track_wks.get_all_records())
            if track_df.empty:
                track_df = pd.DataFrame(columns=[
                    'First time requested', 'Last time requested',
                    'Requests', 'Title', 'URL',
                    'Duration', 'Views', 'Categories'
                ])

            # filter months
            if offset:
                timestamp = now - offset
                filter_ = cmd_df['Date'] >= timestamp
                filtered_cmd_df = cmd_df[filter_]
            else:
                filtered_cmd_df = cmd_df

            # groupby titles
            grouped_cmd_df = filtered_cmd_df.groupby(["URL", "Title"])["Date"]
            function_list = [("First time requested", "min"), ("Last time requested", "max"), ("Requests", "count")]
            grouped_cmd_df = grouped_cmd_df.agg(function_list).reset_index()

            # merge with track_df, rearrange, clean data
            track_df = track_df.drop(labels=["First time requested", "Last time requested", "Requests", "Title"], axis=1)
            merged_df = pd.merge(grouped_cmd_df, track_df, on='URL', how='left')
            merged_df = merged_df[[
                'First time requested', 'Last time requested',
                'Requests', 'Title', 'URL',
                'Duration', 'Views', 'Categories'
            ]]
            merged_df['First time requested'] = merged_df['First time requested'].astype(str)
            merged_df['Last time requested'] = merged_df['Last time requested'].astype(str)
            merged_df = merged_df.fillna(0)
            merged_df = merged_df.sort_values(by='Requests', ascending=False)

            # fill missing cells
            for i, row in enumerate(merged_df.itertuples(), 1):
                ytb_stats = row.Duration, row.Views, row.Categories
                if not all(ytb_stats):
                    try:
                        duration, views, categories = self.get_ytb_track_data(row)
                    except Exception as e:
                        print(f"{i}. error: {e}. (row: {row})")
                        continue

                    merged_df.at[row.Index, 'Duration'] = duration.replace(":", "︰")
                    merged_df.at[row.Index, 'Views'] = views
                    merged_df.at[row.Index, 'Categories'] = categories
                    print(f"Updated {i} row. ({duration}, {views}, {categories}) -- {row.Title}")

            # save to gsheets
            listed_table_result = [merged_df.columns.values.tolist()] + merged_df.values.tolist()  # first part is for header
            track_wks.update(listed_table_result, value_input_option='USER_ENTERED')  # value_input_option='USER_ENTERED' / 'RAW'

        await ctx.send("___Stats updated up to this point.___")

async def setup(bot):
    await bot.add_cog(Commands(bot))
