import asyncio
import json
from pathlib import Path

import requests
import replicate

from .config import (
    REPLICATE_API_TOKEN,
    ELEVENLABS_API_KEY,
    VIDEO_MODEL,
    MUSIC_MODEL,
)


def _run_replicate(prompt, output_path):
    if not REPLICATE_API_TOKEN:
        raise RuntimeError("REPLICATE_API_TOKEN غير موجود.")

    output = replicate.run(
        VIDEO_MODEL,
        input={
            "prompt": prompt,
        },
    )

    if isinstance(output, (list, tuple)):
        output = output[0]

    if hasattr(output, "read"):
        data = output.read()
        Path(output_path).write_bytes(data)
        return

    url = str(output)
    r = requests.get(url, timeout=600)
    r.raise_for_status()
    Path(output_path).write_bytes(r.content)


async def generate_video(prompt, aspect, seconds, output_path):
    await asyncio.to_thread(
        _run_replicate,
        prompt,
        output_path,
    )


def _generate_music(lyrics, style, reference, seconds, output_path):
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("ELEVENLABS_API_KEY غير موجود.")

    url = "https://api.elevenlabs.io/v1/music"

    duration_minutes = max(0.5, min(seconds / 60, 2))

    music_prompt = f"""
Create an original song.

Lyrics:
{lyrics}

Musical style:
{style}

General vocal/musical direction:
{reference}

Duration:
approximately {duration_minutes:.1f} minutes.

Requirements:
- Original melody.
- Original performance.
- Clear Arabic pronunciation when Arabic lyrics are provided.
- Do not imitate or clone any real person's voice.
- Do not reproduce an existing copyrighted song.
- Make the arrangement coherent and complete.
"""

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "prompt": music_prompt,
        "music_length_ms": int(seconds * 1000),
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=900,
    )

    if not response.ok:
        raise RuntimeError(
            f"ElevenLabs Music API error {response.status_code}: "
            f"{response.text[:1000]}"
        )

    Path(output_path).write_bytes(response.content)


async def generate_song(
    lyrics,
    style,
    reference,
    seconds,
    output_path,
):
    await asyncio.to_thread(
        _generate_music,
        lyrics,
        style,
        reference,
        seconds,
        output_path,
    )


async def mux(video_path, audio_path, output_path):
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-i",
        audio_path,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg mux failed:\n{stderr.decode(errors='ignore')[-2000:]}"
        )


async def compress_video(input_path, output_path):
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        output_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    _, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"FFmpeg compression failed:\n"
            f"{stderr.decode(errors='ignore')[-2000:]}"
  )
