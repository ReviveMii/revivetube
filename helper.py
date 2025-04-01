import json
import os
import subprocess
import aiofiles
import aiohttp
import asyncio

async def read_file(path):
    assert isinstance(path, str), "Path must be a string"

    try:
        async with aiofiles.open(path, 'r', encoding='utf-8') as file:
            content = await file.read()
        return content
    except FileNotFoundError:
        return "Error: File not found."
    except Exception as e:
        return f"Error: {str(e)}"

async def get_video_duration_from_file(video_path):
    try:
        result = await asyncio.create_subprocess_exec(
            'ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await result.communicate()

        if result.returncode != 0:
            raise Exception(stderr.decode())

        video_info = json.loads(stdout.decode())
        duration = float(video_info['format']['duration'])
        return duration
    except Exception as e:
        print(f"Can't fetch Video-Duration: {str(e)}")
        return 0

async def format_duration(seconds):
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{str(seconds).zfill(2)}"

async def get_file_size(file_path):
    try:
        stat = await aiofiles.os.stat(file_path)
        return stat.st_size
    except Exception as e:
        print(f"Error getting file size: {str(e)}")
        return 0

async def get_range(file_path, byte_range):
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(byte_range[0])
            data = await f.read(byte_range[1] - byte_range[0] + 1)
        return data
    except Exception as e:
        print(f"Error reading file range: {str(e)}")
        return b''

async def get_api_key():
    try:
        async with aiofiles.open("token.txt", "r") as f:
            return (await f.read()).strip()
    except FileNotFoundError:
        raise FileNotFoundError("Missing token.txt. Please go to README.md")
