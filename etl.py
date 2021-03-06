import os
import glob
import psycopg2
import pandas as pd
from sql_queries import *


def process_song_file(cur, filepath):
    """Reads JSON file and loads its song related data into DB

    Args:
        cur (psycopg2.cursor): DB cursor
        filepath (str): Filepath of the JSON file to load
    """

    # open song file
    df = pd.read_json(filepath, lines=True)

    for _, row in df.iterrows():

        # insert song record
        song_data = [row['song_id'], row['title'],
                     row['artist_id'], row['year'], row['duration']]
        try:
            cur.execute(song_table_insert, song_data)
        except psycopg2.Error as exc:
            print('Something went wrong when inserting song record')
            print(str(exc))

        # insert artist record
        artist_data = [row['artist_id'], row['artist_name'],
                       row['artist_location'], row['artist_latitude'],
                       row['artist_longitude']]
        try:
            cur.execute(artist_table_insert, artist_data)
        except psycopg2.Error as exc:
            print('Something went wrong when inserting artist record')
            print(str(exc))


def process_log_file(cur, filepath):
    """Reads JSON file and loads its log/activity related data into DB

    Args:
        cur (psycopg2.cursor): DB cursor
        filepath (str): Filepath of the JSON file to load
    """

    # open log file
    df = pd.read_json(filepath, lines=True)

    # filter by NextSong action
    df = df[df['page'] == 'NextSong']

    # convert timestamp column to datetime
    t = pd.to_datetime(df['ts'], unit='ms')

    # insert time data records
    time_data = ([[time, time.hour, time.day, time.weekofyear,
                   time.month, time.year, time.dayofweek] for time in t])
    column_labels = ('timestamp', 'hour', 'day',
                     'week of year', 'month', 'year', 'weekday')
    time_df = pd.DataFrame(time_data, columns=column_labels)

    for _, row in time_df.iterrows():
        try:
            cur.execute(time_table_insert, list(row))
        except psycopg2.Error as exc:
            print('Something went wrong when inserting time record')
            print(str(exc))

    # load user table
    user_df = df[['userId', 'firstName', 'lastName', 'gender', 'level']]

    # insert user records
    for _, row in user_df.iterrows():
        try:
            cur.execute(user_table_insert, row)
        except psycopg2.Error as exc:
            print('Something went wrong when inserting songplay record')
            print(str(exc))

    # insert songplay records
    for _, row in df.iterrows():

        # get songid and artistid from song and artist tables
        cur.execute(song_select, (row.song, row.artist, row.length))
        results = cur.fetchone()

        if results:
            songid, artistid = results
        else:
            songid, artistid = None, None

        # insert songplay record
        songplay_data = (row['ts'], row['userId'], row['level'], songid,
                         artistid, row['sessionId'], row['location'], row['userAgent'])
        try:
            cur.execute(songplay_table_insert, songplay_data)
        except psycopg2.Error as exc:
            print('Something went wrong when inserting songplay record')
            print(str(exc))


def process_data(cur, conn, filepath, func):
    """Reads JSON file and loads its song related data into DB

    Args:
        cur (psycopg2.cursor): DB cursor
        conn (psycopg2.connection): DB connection
        filepath (str): Filepath of the JSON file to load
        func (function): Function to call to process data from file
    """

    # get all files matching extension from directory
    all_files = []
    for root, dirs, files in os.walk(filepath):
        files = glob.glob(os.path.join(root, '*.json'))
        for f in files:
            all_files.append(os.path.abspath(f))

    # get total number of files found
    num_files = len(all_files)
    print('{} files found in {}'.format(num_files, filepath))

    # iterate over files and process
    for i, datafile in enumerate(all_files, 1):
        func(cur, datafile)
        conn.commit()
        print('{}/{} files processed.'.format(i, num_files))


def main():
    """Entry point of script. Processes two different files with song and log data
    to load them into Postgresql DB
    """
    conn = psycopg2.connect(
        "host=127.0.0.1 dbname=sparkifydb user=student password=student")
    cur = conn.cursor()

    process_data(cur, conn, filepath='data/song_data', func=process_song_file)
    process_data(cur, conn, filepath='data/log_data', func=process_log_file)

    conn.close()


if __name__ == "__main__":
    main()
