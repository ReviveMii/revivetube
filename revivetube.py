"""
(c) 2025  ReviveMii Project. All rights reserved. If you want to use this Code, give Credits to ReviveMii Project. https://revivemii.errexe.xyz/

ReviveMii Project and TheErrorExe is the Developer of this Code. Modification, Network Use and Distribution is allowed if you leave this Comment in the beginning of the Code, and if a website exist, Credits on the Website.

This Code uses the Invidious API, Google API and yt-dlp. This Code is designed to run on Ubuntu 24.04.

Don’t claim that this code is your code. Don't use it without Credits to the ReviveMii Project. Don't use it without this Comment. Don't modify this Comment. You need to make your modified Code Open Source with this exact License.

ReviveMii's Server Code is provided "as-is" and "as available." We do not guarantee uninterrupted access, error-free performance, or compatibility with all Wii systems. ReviveMii project is not liable for any damage, loss of data, or other issues arising from the use of this service and code.

If you use this Code, you agree to https://revivemii.errexe.xyz/revivetube/t-and-p.html, also available as http only Version: http://revivemii.errexe.xyz/revivetube/t-and-p.html

ReviveMii Project: https://revivemii.errexe.xyz/
"""

import os
import shutil
import subprocess
import tempfile
import threading
import time
from threading import Thread

from bs4 import BeautifulSoup

import requests
import yt_dlp
from flask import Flask, request, render_template_string, send_file, Response, abort, jsonify
import json
import helper

app = Flask(__name__)


def check_and_create_folder():
    while True:
        folder_path = './sigma/videos'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder {folder_path} got created.")
        time.sleep(10)


def start_folder_check():
    thread = Thread(target=check_and_create_folder)
    thread.daemon = True
    thread.start()


VIDEO_FOLDER = "sigma/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
video_status = {}

FILE_SEPARATOR = os.sep

LOADING_TEMPLATE = helper.read_file(f"site_storage{FILE_SEPARATOR}loading_template.html")
CHANNEL_TEMPLATE = helper.read_file(f"site_storage{FILE_SEPARATOR}channel_template.html")
SEARCH_TEMPLATE = helper.read_file(f"site_storage{FILE_SEPARATOR}search_template.html")


os.makedirs(VIDEO_FOLDER, exist_ok=True)

MAX_VIDEO_SIZE = 1 * 1024 * 1024 * 1024
MAX_FOLDER_SIZE = 5 * 1024 * 1024 * 1024


def get_folder_size(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            file_path = os.path.join(dirpath, f)
            total_size += os.path.getsize(file_path)
    return total_size



INDEX_TEMPLATE = helper.read_file(f"site_storage{FILE_SEPARATOR}index_template.html")

WATCH_WII_TEMPLATE = helper.read_file(f"site_storage{FILE_SEPARATOR}watch_wii_template.html")


@app.route("/thumbnail/<video_id>")
def get_thumbnail(video_id):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"

    try:

        response = requests.get(thumbnail_url, stream=True, timeout=1)
        if response.status_code == 200:

            return send_file(
                response.raw,
                mimetype=response.headers.get("Content-Type", "image/jpeg"),
                as_attachment=False,
            )
        else:
            return f"Failed to fetch thumbnail. Status: {response.status_code}", 500
    except requests.exceptions.RequestException as e:
        return f"Error fetching thumbnail: {str(e)}", 500


def get_video_comments(video_id, max_results=20):
    api_key = helper.get_api_key()

    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": max_results,
        "order": "relevance"
    }

    try:
        response = requests.get("https://www.googleapis.com/youtube/v3/commentThreads", params=params, timeout=3)
        response.raise_for_status()

        data = response.json()

        comments = []
        if "items" in data:
            for item in data["items"]:
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet["authorDisplayName"],
                    "text": snippet["textDisplay"],
                    "likeCount": snippet.get("likeCount", 0),
                    "publishedAt": snippet["publishedAt"]
                })

        return comments

    except requests.exceptions.RequestException as e:
        print(f"Can't fetch Comments: {str(e)}")
        return []


@app.route("/cookies.txt", methods=["GET"])
def cookies():
    return "403 Forbidden", 403

@app.route("/token.txt", methods=["GET"])
def token():
    return "403 Forbidden", 403

@app.route("/nohup.out", methods=["GET"])
def nohup():
    return "403 Forbidden", 403


@app.route("/", methods=["GET"])
def index():
    query = request.args.get("query")
    results = None

    if query:
        response = requests.get(f"https://invidious.materialio.us/api/v1/search?q={query}", timeout=3)
    else:
        response = requests.get("https://invidious.materialio.us/api/v1/trending", timeout=3)

    try:
        data = response.json()
    except ValueError:
        return "Can't parse Data. If this Issue persists, report it in the Discord Server.", 500

    if response.status_code == 200 and isinstance(data, list):
        if query:
            results = []
            for entry in data:
                if entry.get("type") == "video":
                    results.append({
                        "type": "video",
                        "id": entry.get("videoId"),
                        "title": entry.get("title"),
                        "uploader": entry.get("author", "Unknown"),
                        "thumbnail": f"/thumbnail/{entry['videoId']}",
                        "viewCount": entry.get("viewCountText", "Unknown"),
                        "published": entry.get("publishedText", "Unknown"),
                        "duration": helper.format_duration(entry.get("lengthSeconds", 0))
                    })
                elif entry.get("type") == "channel":
                    results.append({
                        "type": "channel",
                        "id": entry.get("authorId"),
                        "title": entry.get("author"),
                        "thumbnail": entry.get("authorThumbnails")[-1]["url"] if entry.get("authorThumbnails") else "/static/default_channel_thumbnail.jpg",
                        "subCount": entry.get("subCount", "Unknown"),
                        "videoCount": entry.get("videoCount", "Unknown")
                    })
            return render_template_string(SEARCH_TEMPLATE, results=results)
        else:
            results = [
                {
                    "id": entry.get("videoId"),
                    "title": entry.get("title"),
                    "uploader": entry.get("author", "Unknown"),
                    "thumbnail": f"/thumbnail/{entry['videoId']}",
                    "viewCount": entry.get("viewCountText", "Unknown"),
                    "published": entry.get("publishedText", "Unknown"),
                    "duration": helper.format_duration(entry.get("lengthSeconds", 0))
                }
                for entry in data
                if entry.get("videoId")
            ]
            return render_template_string(INDEX_TEMPLATE, results=results)
    else:
        return "No Results or Error in the API.", 404



@app.route("/watch", methods=["GET"])
def watch():
    video_id = request.args.get("video_id")
    if not video_id:
        return "Missing Video-ID.", 400

    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")

    if video_id not in video_status:
        video_status[video_id] = {"status": "processing"}

    user_agent = request.headers.get("User-Agent", "").lower()
    is_wii = "wii" in user_agent and "wiiu" not in user_agent

    try:
        # Metadaten des Videos abrufen
        response = requests.get(f"http://localhost:5000/video_metadata/{video_id}", timeout=20)
        if response.status_code == 200:
            metadata = response.json()
        else:
            return f"Metadata API Error for Video-ID {video_id}.", 500
    except requests.exceptions.RequestException as e:
        return f"Can't connect to Metadata-API: {str(e)}", 500

    # Kommentare des Videos abrufen
    comments = []
    try:
        comments = get_video_comments(video_id)
    except Exception as e:
        print(f"Video-Comments Error: {str(e)}")
        comments = []

    # Kanal-Logo und Abonnentenanzahl über die SuperPlayCounts API abrufen
    channel_logo_url = ""
    subscriber_count = "Unbekannt"
    try:
        channel_id = metadata['channelId']
        api_url = f"https://api-superplaycounts.onrender.com/api/youtube-channel-counter/user/{channel_id}"
        channel_response = requests.get(api_url, timeout=5)
        if channel_response.status_code == 200:
            channel_data = channel_response.json()

            for stat in channel_data.get("statistics", []):
                for count in stat.get("counts", []):
                    if count.get("value") == "subscribers":
                        subscriber_count = count.get("count", "Unbekannt")
                        break

            for stat in channel_data.get("statistics", []):
                for user_info in stat.get("user", []):
                    if user_info.get("value") == "pfp":
                        channel_logo_url = user_info.get("count", "").replace("https://", "http://")
                        break
    except Exception as e:
        print(f"SuperPlayCounts API Error: {str(e)}")

    comment_count = len(comments)

    if os.path.exists(video_mp4_path):
        video_duration = helper.get_video_duration_from_file(video_flv_path)
        alert_script = ""
        if video_duration > 420:
            alert_script = """
            <script type="text/javascript">
                alert("This Video is long. There is a chance that the Wii will not play the Video. Try a Video under 5 minutes.");
            </script>
            """

        if is_wii and os.path.exists(video_flv_path):
            return render_template_string(WATCH_WII_TEMPLATE + alert_script,
                                          title=metadata['title'],
                                          uploader=metadata['uploader'],
                                          channelId=metadata['channelId'],
                                          description=metadata['description'].replace("\n", "<br>"),
                                          viewCount=metadata['viewCount'],
                                          likeCount=metadata['likeCount'],
                                          publishedAt=metadata['publishedAt'],
                                          comments=comments,
                                          commentCount=comment_count,
                                          channel_logo_url=channel_logo_url,
                                          subscriberCount=subscriber_count,
                                          video_id=video_id,
                                          video_flv=f"/sigma/videos/{video_id}.flv",
                                          alert_message="")

        return render_template_string(WATCH_WII_TEMPLATE,
                                      title=metadata['title'],
                                      uploader=metadata['uploader'],
                                      channelId=metadata['channelId'],
                                      description=metadata['description'].replace("\n", "<br>"),
                                      viewCount=metadata['viewCount'],
                                      likeCount=metadata['likeCount'],
                                      publishedAt=metadata['publishedAt'],
                                      comments=comments,
                                      commentCount=comment_count,
                                      channel_logo_url=channel_logo_url,
                                      subscriberCount=subscriber_count,
                                      video_id=video_id,
                                      video_flv=f"/sigma/videos/{video_id}.flv",
                                      alert_message="")

    if not os.path.exists(video_mp4_path):
        if video_status[video_id]["status"] == "processing":
            threading.Thread(target=process_video, args=(video_id,)).start()
        return render_template_string(LOADING_TEMPLATE, video_id=video_id)


def process_video(video_id):
    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")
    try:

        video_status[video_id] = {"status": "downloading"}




        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")
            command = [
                "yt-dlp",
                "-o", temp_video_path,
                "--cookies", "cookies.txt",
                "--proxy", "http://localhost:4000",                
                "-f", "worstvideo+worstaudio",
                f"https://youtube.com/watch?v={video_id}"
            ]
            subprocess.run(command, check=True)

            downloaded_files = [f for f in os.listdir(temp_dir) if video_id in f]
            if not downloaded_files:
                video_status[video_id] = {"status": "error", "message": "Error downloading."}
                return

            downloaded_file = os.path.join(temp_dir, downloaded_files[0])

            if not downloaded_file.endswith(".mp4"):
                video_status[video_id] = {"status": "converting"}
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i", downloaded_file,
                        "-c:v", "libx264",
                        "-crf", "51",
                        "-c:a", "aac",
                        "-strict", "experimental",
                        "-preset", "ultrafast",
                        "-b:a", "64k",
                        "-movflags", "+faststart",
                        "-vf", "scale=854:480",
                        video_mp4_path
                    ],
                    check=True
                )
            else:
                shutil.copy(downloaded_file, video_mp4_path)

        if not os.path.exists(video_flv_path):
            video_status[video_id] = {"status": "converting for Wii"}
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i", video_mp4_path,
                    "-ar", "22050",
                    "-f", "flv",
                    "-s", "320x240",
                    "-ab", "32k",
                    "-preset", "ultrafast",
                    "-crf", "51",
                    "-filter:v", "fps=fps=15",
                    video_flv_path
                ],
                check=True)

        video_status[video_id] = {"status": "complete", "url": f"/sigma/videos/{video_id}.mp4"}

    except Exception as e:
        video_status[video_id] = {"status": "error", "message": str(e)}


@app.route("/status/<video_id>")
def check_status(video_id):
    return jsonify(video_status.get(video_id, {"status": "pending"}))


@app.route("/video_metadata/<video_id>")
def video_metadata(video_id):
    api_key = helper.get_api_key()

    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }

    try:
        response = requests.get(YOUTUBE_API_URL, params=params, timeout=1)
        response.raise_for_status()

        data = response.json()

        if "items" not in data or len(data["items"]) == 0:
            return f"The Video with ID {video_id} was not found.", 404

        video_data = data["items"][0]
        title = video_data["snippet"]["title"]
        description = video_data["snippet"]["description"]
        uploader = video_data["snippet"]["channelTitle"]
        channel_id = video_data["snippet"]["channelId"]
        view_count = video_data["statistics"].get("viewCount", "Unknown")
        like_count = video_data["statistics"].get("likeCount", "Unknown")
        dislike_count = video_data["statistics"].get("dislikeCount", "Unknown")
        published_at = video_data["snippet"].get("publishedAt", "Unknown")

        return {
            "title": title,
            "uploader": uploader,
            "channelId": channel_id,
            "description": description,
            "viewCount": view_count,
            "likeCount": like_count,
            "dislikeCount": dislike_count,
            "publishedAt": published_at
        }

    except requests.exceptions.RequestException as e:
        return f"API Error: {str(e)}", 500


@app.route("/<path:filename>")
def serve_video(filename):
    file_path = os.path.join(filename)

    if not os.path.exists(file_path):
        return "File not found.", 404

    file_size = helper.get_file_size(file_path)

    range_header = request.headers.get('Range', None)
    if range_header:
        byte_range = range_header.strip().split('=')[1]
        start_byte, end_byte = byte_range.split('-')
        start_byte = int(start_byte)
        end_byte = int(end_byte) if end_byte else file_size - 1

        if start_byte >= file_size or end_byte >= file_size:
            abort(416)

        data = helper.get_range(file_path, (start_byte, end_byte))
        content_range = f"bytes {start_byte}-{end_byte}/{file_size}"

        response = Response(
            data,
            status=206,
            mimetype="video/mp4",
            content_type="video/mp4",
            direct_passthrough=True
        )
        response.headers["Content-Range"] = content_range
        response.headers["Content-Length"] = str(len(data))
        return response

    return send_file(file_path)



@app.route('/channel', methods=['GET'])
def channel_m():
    channel_id = request.args.get('channel_id', None)

    if not channel_id:
        return "Channel ID is required.", 400

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 20,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            url = f"https://www.youtube.com/channel/{channel_id}/videos"
            info = ydl.extract_info(url, download=False)

            if 'entries' not in info:
                return "No videos found.", 404

            channel_name = info.get('uploader', 'Unknown')

        invidious_url = f"https://invidious.materialio.us/channel/{channel_id}"
        response = requests.get(invidious_url, timeout=10)

        if response.status_code != 200:
            return "Failed to fetch channel page.", 500

        soup = BeautifulSoup(response.text, "html.parser")
        profile_div = soup.find(class_="channel-profile")

        if profile_div:
            img_tag = profile_div.find("img")
            if img_tag and "src" in img_tag.attrs:
                channel_picture = "http://api.allorigins.win/raw?url=http://invidious.materialio.us" + img_tag["src"]
            else:
                channel_picture = ""
        else:
            channel_picture = ""

        results = [
            {
                'id': video['id'],
                'duration': 'Duration not available on Channel View',
                'title': video['title'],
                'uploader': channel_name,
                'thumbnail': f"http://yt.old.errexe.xyz/thumbnail/{video['id']}"
            }
            for video in info['entries']
        ]

        return render_template_string(
            CHANNEL_TEMPLATE,
            results=results,
            channel_name=channel_name,
            channel_picture=channel_picture
        )

    except Exception as e:
        return f"An error occurred: {str(e)}", 500



if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=5000)
