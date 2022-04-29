import pandas as pd
import gspread

import youtube_dl
ytdlopts = {
    'format': 'bestaudio/best',
    'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # ipv6 addresses cause issues sometimes
}
ytdl = youtube_dl.YoutubeDL(ytdlopts)

# #########################
'''
gc = gspread.service_account('credentials.json')
sh = gc.open("Discord Music Log")
cmd_wks = sh.worksheet("Commands Log2")
track_wks = sh.worksheet("Track Log (Lifetime)")
cmd_df = pd.DataFrame(cmd_wks.get_all_records())
track_df = pd.DataFrame(track_wks.get_all_records())

# #########################

cmd_df['Date'] = pd.to_datetime(cmd_df['Date'])
cmd_grouped = cmd_df.groupby(["Title", "URL"])["Date"]
function_list = [("First time requested", "min"), ("Last time requested", "max"), ("Requests", "count")]
cmd_table = cmd_grouped.agg(function_list).reset_index()  # .sort_values("count", ascending=False).head(20)

cols_to_use = track_df.columns.difference(cmd_table.columns)
merged_df = pd.merge(cmd_table, track_df[cols_to_use], left_index=True, right_index=True, how='outer')
merged_df = merged_df[['First time requested', 'Last time requested', 'Requests', 'Title', 'URL', 'Duration', 'Views', 'Categories']]
merged_df = merged_df.fillna(0)
# cmd_table
# track_df
'''
# ##########################

def get_readable_duration(duration):
    """Get duration in hours, minutes and seconds."""

    m, s = divmod(int(duration), 60)
    h, m = divmod(m, 60)

    # if h and m:
    #     m = f':{m:02d}'
    # if m or s:
    #     s = f':{s:02d}'
    # duration = f"{h}{m}{s}"

    duration = ''
    if h:
        duration = f"{h}:{m:02d}:{s:02d}"
    else:
        duration = f"{m}:{s:02d}"
    # if h and m:
    #     m = f':{m:02d}'
    # elif m:
    #     h = ''

    # if h or m:
    #     s = f':{s:02d}'
    # else:
    #     m = ''


    return duration

def get_ytb_data(row):
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

"""Saves history of songs into Google Sheets."""

# get pandas format
print("get pandas format")
gc = gspread.service_account(filename='credentials.json')
sh = gc.open("Discord Music Log")
cmd_wks = sh.worksheet("Commands Log2")
cmd_df = pd.DataFrame(cmd_wks.get_all_records())
cmd_df['Date'] = pd.to_datetime(cmd_df['Date'])
now = pd.Timestamp.now()

# preparation
print("preparation")
name_offset_dict = {
    "Track Log (Lifetime)": False,
    "Track Log (year)": pd.DateOffset(years=1),
    "Track Log (3 months)": pd.DateOffset(months=3),
    "Track Log (month)": pd.DateOffset(months=1),
    "Track Log (week)": pd.DateOffset(weeks=1)
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
    print("filter months")
    if offset:
        timestamp = now - offset
        filter_ = cmd_df['Date'] >= timestamp
        filtered_cmd_df = cmd_df[filter_]
    else:
        filtered_cmd_df = cmd_df

    # groupby titles
    print("groupby titles")
    grouped_cmd_df = filtered_cmd_df.groupby(["Title", "URL"])["Date"]
    function_list = [("First time requested", "min"), ("Last time requested", "max"), ("Requests", "count")]
    grouped_cmd_df = grouped_cmd_df.agg(function_list).reset_index()

    # merge with track_df, rearrange, clean data
    cols_to_use = track_df.columns.difference(grouped_cmd_df.columns)
    merged_df = pd.merge(grouped_cmd_df, track_df[cols_to_use], left_index=True, right_index=True, how='outer')
    merged_df = merged_df[[
        'First time requested', 'Last time requested',
        'Requests', 'Title', 'URL',
        'Duration', 'Views', 'Categories'
    ]]
    merged_df['First time requested'] = merged_df['First time requested'].astype(str)
    merged_df['Last time requested'] = merged_df['Last time requested'].astype(str)
    merged_df = merged_df.fillna(0)

    # fill missing cells
    print("fill missing cells")
    for i, row in enumerate(merged_df.head(20).itertuples()):
        ytb_stats = row.Duration, row.Views, row.Categories
        if not all(ytb_stats):
            try:
                duration, views, categories = get_ytb_data(row)
            except KeyError:
                print(f"{i}. Playlist! (row: {row})")
                continue
            except Exception as e:
                print(f"{i}. error: {e}. Playlist or ")
                continue

            merged_df.at[row.Index, 'Duration'] = duration.replace(":", "︰")
            merged_df.at[row.Index, 'Views'] = views
            merged_df.at[row.Index, 'Categories'] = categories
            print(f"Updated {i} row.")

    # save to google spreadsheet
    listed_table_result = [merged_df.columns.values.tolist()] + merged_df.values.tolist()  # first part is for header
    track_wks.update(listed_table_result, value_input_option='USER_ENTERED')  # value_input_option='USER_ENTERED' / 'RAW'
