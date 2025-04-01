"""
(c) 2025  ReviveMii Project. All rights reserved. If you want to use this Code, give Credits to ReviveMii Project. https://revivemii.errexe.xyz/

ReviveMii Project and TheErrorExe is the Developer of this Code. Modification, Network Use and Distribution is allowed if you leave this Comment in the beginning of the Code, and if a website exist, Credits on the Website.

This Code uses the Invidious API, Google API and yt-dlp. This Code is designed to run on Ubuntu 24.04.

Don't claim that this code is your code. Don't use it without Credits to the ReviveMii Project. Don't use it without this Comment. Don't modify this Comment. You need to make your modified Code Open Source with this exact License.

ReviveMii's Server Code is provided "as-is" and "as available." We do not guarantee uninterrupted access, error-free performance, or compatibility with all Wii systems. ReviveMii project is not liable for any damage, loss of data, or other issues arising from the use of this service and code.

If you use this Code, you agree to https://revivemii.errexe.xyz/revivetube/t-and-p.html, also available as http only Version: http://revivemii.errexe.xyz/revivetube/t-and-p.html

ReviveMii Project: https://revivemii.errexe.xyz/
"""

import os
import shutil
import subprocess
import tempfile
import aiofiles
import aiohttp
import asyncio
import yt_dlp
from bs4 import BeautifulSoup
from quart import Quart, request, render_template_string, send_file, Response, abort, jsonify
from helper import *

app = Quart(__name__)

VIDEO_FOLDER = "sigma/videos"
YOUTUBE_API_URL = "https://www.googleapis.com/youtube/v3/videos"
video_status = {}

FILE_SEPARATOR = os.sep

async def read_file(file_path):
    async with aiofiles.open(file_path, mode='r') as f:
        return await f.read()

async def check_and_create_folder():
    while True:
        folder_path = './sigma/videos'
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"Folder {folder_path} got created.")
        await asyncio.sleep(10)

@app.before_serving
async def startup():
    asyncio.create_task(check_and_create_folder())

LOADING_TEMPLATE = None
CHANNEL_TEMPLATE = None
SEARCH_TEMPLATE = None
INDEX_TEMPLATE = None
WATCH_WII_TEMPLATE = None

async def load_templates():
    global LOADING_TEMPLATE, CHANNEL_TEMPLATE, SEARCH_TEMPLATE, INDEX_TEMPLATE, WATCH_WII_TEMPLATE
    LOADING_TEMPLATE = await read_file(f"site_storage{FILE_SEPARATOR}loading_template.html")
    CHANNEL_TEMPLATE = await read_file(f"site_storage{FILE_SEPARATOR}channel_template.html")
    SEARCH_TEMPLATE = await read_file(f"site_storage{FILE_SEPARATOR}search_template.html")
    INDEX_TEMPLATE = await read_file(f"site_storage{FILE_SEPARATOR}index_template.html")
    WATCH_WII_TEMPLATE = await read_file(f"site_storage{FILE_SEPARATOR}watch_wii_template.html")

app.before_serving(load_templates)

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

@app.route("/thumbnail/<video_id>")
async def get_thumbnail(video_id):
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as response:
                if response.status == 200:
                    return await send_file(
                        response.content,
                        mimetype=response.headers.get("Content-Type", "image/jpeg"),
                        as_attachment=False,
                    )
                return f"Failed to fetch thumbnail. Status: {response.status}", 500
    except aiohttp.ClientError as e:
        return f"Error fetching thumbnail: {str(e)}", 500

async def get_video_comments(video_id, max_results=20):
    api_key = await get_api_key()
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": max_results,
        "order": "relevance"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://www.googleapis.com/youtube/v3/commentThreads", params=params, timeout=3) as response:
                response.raise_for_status()
                data = await response.json()
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
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        print(f"Can't fetch Comments: {str(e)}")
        return []

@app.route("/cookies.txt", methods=["GET"])
async def cookies():
    return "403 Forbidden", 403

@app.route("/token.txt", methods=["GET"])
async def token():
    return "403 Forbidden", 403

@app.route("/nohup.out", methods=["GET"])
async def nohup():
    return "403 Forbidden", 403

@app.route("/", methods=["GET"])
async def index():
    query = request.args.get("query")
    results = None
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://invidious.materialio.us/api/v1/search?q={query}" if query else "https://invidious.materialio.us/api/v1/trending"
            async with session.get(url, timeout=3) as response:
                data = await response.json()
                if response.status == 200 and isinstance(data, list):
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
                                    "duration": await format_duration(entry.get("lengthSeconds", 0))
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
                        return await render_template_string(SEARCH_TEMPLATE, results=results)
                    else:
                        results = [
                            {
                                "id": entry.get("videoId"),
                                "title": entry.get("title"),
                                "uploader": entry.get("author", "Unknown"),
                                "thumbnail": f"/thumbnail/{entry['videoId']}",
                                "viewCount": entry.get("viewCountText", "Unknown"),
                                "published": entry.get("publishedText", "Unknown"),
                                "duration": await format_duration(entry.get("lengthSeconds", 0))
                            }
                            for entry in data
                            if entry.get("videoId")
                        ]
                        return await render_template_string(INDEX_TEMPLATE, results=results)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        return "Can't parse Data. If this Issue persists, report it in the Discord Server.", 500
    return "No Results or Error in the API.", 404

@app.route("/watch", methods=["GET"])
async def watch():
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
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://localhost:5000/video_metadata/{video_id}", timeout=20) as response:
                if response.status == 200:
                    metadata = await response.json()
                else:
                    return f"Metadata API Error for Video-ID {video_id}.", 500
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return f"Can't connect to Metadata-API: {str(e)}", 500

    comments = await get_video_comments(video_id)
    channel_logo_url = ""
    subscriber_count = "Unbekannt"
    
    try:
        channel_id = metadata['channelId']
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api-superplaycounts.onrender.com/api/youtube-channel-counter/user/{channel_id}", timeout=5) as channel_response:
                if channel_response.status == 200:
                    channel_data = await channel_response.json()
                    for stat in channel_data.get("statistics", []):
                        for count in stat.get("counts", []):
                            if count.get("value") == "subscribers":
                                subscriber_count = count.get("count", "Unbekannt")
                                break
                        for user_info in stat.get("user", []):
                            if user_info.get("value") == "pfp":
                                channel_logo_url = user_info.get("count", "").replace("https://", "http://")
                                break
    except Exception as e:
        print(f"SuperPlayCounts API Error: {str(e)}")

    comment_count = len(comments)

    if os.path.exists(video_mp4_path):
        video_duration = await get_video_duration_from_file(video_flv_path)
        alert_script = ""
        if video_duration > 420:
            alert_script = """<script type="text/javascript">alert("This Video is long. There is a chance that the Wii will not play the Video. Try a Video under 5 minutes.");</script>"""

        if is_wii and os.path.exists(video_flv_path):
            return await render_template_string(WATCH_WII_TEMPLATE + alert_script,
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

        return await render_template_string(WATCH_WII_TEMPLATE,
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
            asyncio.create_task(process_video(video_id))
        return await render_template_string(LOADING_TEMPLATE, video_id=video_id)

async def process_video(video_id):
    video_mp4_path = os.path.join(VIDEO_FOLDER, f"{video_id}.mp4")
    video_flv_path = os.path.join(VIDEO_FOLDER, f"{video_id}.flv")
    try:
        video_status[video_id] = {"status": "downloading"}
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video_path = os.path.join(temp_dir, f"{video_id}.%(ext)s")
            subprocess.run([
                "yt-dlp",
                "-o", temp_video_path,
                "--cookies", "cookies.txt",
                "--proxy", "http://localhost:4000",                
                "-f", "worstvideo+worstaudio",
                f"https://youtube.com/watch?v={video_id}"
            ], check=True)

            downloaded_files = [f for f in os.listdir(temp_dir) if video_id in f]
            if not downloaded_files:
                video_status[video_id] = {"status": "error", "message": "Error downloading."}
                return

            downloaded_file = os.path.join(temp_dir, downloaded_files[0])
            if not downloaded_file.endswith(".mp4"):
                video_status[video_id] = {"status": "converting"}
                subprocess.run([
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
                ], check=True)
            else:
                shutil.copy(downloaded_file, video_mp4_path)

        if not os.path.exists(video_flv_path):
            video_status[video_id] = {"status": "converting for Wii"}
            subprocess.run([
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
            ], check=True)

        video_status[video_id] = {"status": "complete", "url": f"/sigma/videos/{video_id}.mp4"}
    except Exception as e:
        video_status[video_id] = {"status": "error", "message": str(e)}

@app.route("/status/<video_id>")
async def check_status(video_id):
    return jsonify(video_status.get(video_id, {"status": "pending"}))

@app.route("/video_metadata/<video_id>")
async def video_metadata(video_id):
    api_key = await get_api_key()
    params = {
        "part": "snippet,statistics",
        "id": video_id,
        "key": api_key
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(YOUTUBE_API_URL, params=params, timeout=1) as response:
                response.raise_for_status()
                data = await response.json()
                if "items" not in data or len(data["items"]) == 0:
                    return f"The Video with ID {video_id} was not found.", 404
                video_data = data["items"][0]
                return {
                    "title": video_data["snippet"]["title"],
                    "uploader": video_data["snippet"]["channelTitle"],
                    "channelId": video_data["snippet"]["channelId"],
                    "description": video_data["snippet"]["description"],
                    "viewCount": video_data["statistics"].get("viewCount", "Unknown"),
                    "likeCount": video_data["statistics"].get("likeCount", "Unknown"),
                    "dislikeCount": video_data["statistics"].get("dislikeCount", "Unknown"),
                    "publishedAt": video_data["snippet"].get("publishedAt", "Unknown")
                }
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return f"API Error: {str(e)}", 500

@app.route("/<path:filename>")
async def serve_video(filename):
    file_path = os.path.join(filename)
    if not os.path.exists(file_path):
        return "File not found.", 404

    file_size = await get_file_size(file_path)
    range_header = request.headers.get('Range', None)
    if range_header:
        byte_range = range_header.strip().split('=')[1]
        start_byte, end_byte = byte_range.split('-')
        start_byte = int(start_byte)
        end_byte = int(end_byte) if end_byte else file_size - 1

        if start_byte >= file_size or end_byte >= file_size:
            abort(416)

        data = await get_range(file_path, (start_byte, end_byte))
        content_range = f"bytes {start_byte}-{end_byte}/{file_size}"

        response = Response(
            data,
            status=206,
            mimetype="video/mp4",
            content_type="video/mp4",
        )
        response.headers["Content-Range"] = content_range
        response.headers["Content-Length"] = str(len(data))
        return response

    return await send_file(file_path)

@app.route('/channel', methods=['GET'])
async def channel_m():
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
            info = ydl.extract_info(f"https://www.youtube.com/channel/{channel_id}/videos", download=False)
            if 'entries' not in info:
                return "No videos found.", 404
            channel_name = info.get('uploader', 'Unknown')

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://invidious.materialio.us/channel/{channel_id}", timeout=10) as response:
                if response.status != 200:
                    return "Failed to fetch channel page.", 500
                soup = BeautifulSoup(await response.text(), "html.parser")
                profile_div = soup.find(class_="channel-profile")
                channel_picture = ""
                if profile_div:
                    img_tag = profile_div.find("img")
                    if img_tag and "src" in img_tag.attrs:
                        channel_picture = f"http://api.allorigins.win/raw?url=http://invidious.materialio.us{img_tag['src']}"

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
                return await render_template_string(
                    CHANNEL_TEMPLATE,
                    results=results,
                    channel_name=channel_name,
                    channel_picture=channel_picture
                )
    except Exception as e:
        return f"An error occurred: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
