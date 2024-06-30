import os
import re
from datetime import timedelta
from googleapiclient.discovery import build
from flask import Flask, render_template, request

app = Flask(__name__)
api_key = 'API_KEY'  # Replace with your API key
youtube = build('youtube', 'v3', developerKey=api_key)

hours_pattern = re.compile(r'(\d+)H')
minutes_pattern = re.compile(r'(\d+)M')
seconds_pattern = re.compile(r'(\d+)S')

def extract_playlist_id(url):
    match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
    return match.group(1) if match else None

def get_playlist_info(playlist_id):
    total_seconds = 0
    video_count = 0
    nextPageToken = None

    pl_details_request = youtube.playlists().list(
        part='snippet',
        id=playlist_id
    )
    
    pl_details_response = pl_details_request.execute()
    playlist_title = pl_details_response['items'][0]['snippet']['title'] if pl_details_response['items'] else "Unknown"

    while True:
        pl_request = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=nextPageToken
        )
        pl_response = pl_request.execute()

        vid_ids = [item['contentDetails']['videoId'] for item in pl_response['items']]
        video_count += len(vid_ids)

        vid_request = youtube.videos().list(
            part="contentDetails",
            id=','.join(vid_ids)
        )
        vid_response = vid_request.execute()

        for item in vid_response['items']:
            duration = item['contentDetails']['duration']

            hours = hours_pattern.search(duration)
            minutes = minutes_pattern.search(duration)
            seconds = seconds_pattern.search(duration)

            hours = int(hours.group(1)) if hours else 0
            minutes = int(minutes.group(1)) if minutes else 0
            seconds = int(seconds.group(1)) if seconds else 0

            video_seconds = timedelta(
                hours=hours,
                minutes=minutes,
                seconds=seconds
            ).total_seconds()

            total_seconds += video_seconds

        nextPageToken = pl_response.get('nextPageToken')
        if not nextPageToken:
            break

    return {
        'title': playlist_title,
        'video_count': video_count,
        'total_seconds': total_seconds
    }

def format_duration(total_seconds):
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)} hours, {int(minutes)} minutes, {int(seconds)} seconds"

@app.context_processor
def utility_processor():
    def adjusted_duration(total_seconds, speed):
        adjusted_seconds = total_seconds / speed
        return format_duration(adjusted_seconds)
    return dict(adjusted_duration=adjusted_duration, format_duration=format_duration)

@app.route('/', methods=['GET', 'POST'])
def index():
    playlist_info = None
    error = None
    if request.method == 'POST':
        playlist_url = request.form.get('playlist_url')
        playlist_id = extract_playlist_id(playlist_url)
        if playlist_id:
            try:
                playlist_info = get_playlist_info(playlist_id)
            except Exception as e:
                error = f"Error: {str(e)}"
        else:
            error = "Invalid playlist URL."
    return render_template('index.html', playlist_info=playlist_info, error=error)

if __name__ == '__main__':
    app.run(debug=True)
