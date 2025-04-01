import json
import os
import subprocess
import aiofiles
import aiohttp
import asyncio

async def read_file(path):
    try:
        async with aiofiles.open(path, 'r', encoding='utf-8') as file:
            return await file.read()
    except Exception as e:
        print(f"Error reading file: {str(e)}")
        return None

async def get_video_duration_from_file(video_path):
    try:
        proc = await asyncio.create_subprocess_exec(
            'ffprobe', '-v', 'error', '-show_format',
            '-show_streams', '-of', 'json', video_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise Exception(stderr.decode())
        return float(json.loads(stdout.decode())['format']['duration'])
    except Exception as e:
        print(f"Error getting video duration: {str(e)}")
        return 0.0

async def format_duration(seconds):
    return f"{int(seconds//60)}:{int(seconds%60):02d}"

async def get_file_size(file_path):
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        print(f"Error getting file size: {str(e)}")
        return 0

async def get_range(file_path, byte_range):
    try:
        async with aiofiles.open(file_path, 'rb') as f:
            await f.seek(byte_range[0])
            return await f.read(byte_range[1] - byte_range[0] + 1)
    except Exception as e:
        print(f"Error reading file range: {str(e)}")
        return b''

async def get_api_key():
    try:
        async with aiofiles.open("token.txt", "r") as f:
            return (await f.read()).strip()
    except Exception as e:
        print(f"Error reading API key: {str(e)}")
        raise
