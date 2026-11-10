# Copyright (c) 2025 strad-dev131
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the cloudymusic project. All rights reserved where applicable.

import asyncio
import os
import re
from typing import Optional, Union
from pathlib import Path

import aiohttp
from py_yt import VideosSearch
from pytdbot import types

from cloudymusic.logger import LOGGER
from ._config import config
from ._dataclass import MusicTrack, PlatformTracks, TrackInfo
from ._downloader import MusicService


class YouTubeAPI:
    """ShrutiAPI based YouTube handler for cloudymusic."""

    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.listbase = "https://youtube.com/playlist?list="
        self.download_dir = "downloads"

    def _get_api_config(self):
        url = getattr(config, "API_URL", None) or os.environ.get("API_URL", "https://api.shrutibots.in")
        key = getattr(config, "API_KEY", None) or os.environ.get("API_KEY", "")
        return url.rstrip("/"), key

    @staticmethod
    def time_to_seconds(time_str) -> int:
        try:
            return sum(int(x) * 60 ** i for i, x in enumerate(reversed(str(time_str).split(":"))))
        except Exception:
            return 0

    async def _download_media(self, link: str, kind: str, timeout: int) -> Optional[str]:
        video_id = link.split("v=")[-1].split("&")[0] if "v=" in link else link
        if not video_id or len(video_id) < 3:
            return None

        api_url, api_key = self._get_api_config()
        if not api_key:
            LOGGER.error("ShrutiAPI key is missing in configuration!")
            return None

        os.makedirs(self.download_dir, exist_ok=True)
        file_path = os.path.join(self.download_dir, f"{video_id}.{'mp3' if kind == 'audio' else 'mp4'}")
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/download",
                    params={"url": video_id, "type": kind, "api_key": api_key},
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as resp:
                    if resp.status != 200:
                        LOGGER.warning(f"ShrutiAPI download failed with status {resp.status}")
                        return None
                    
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                return file_path
        except Exception as e:
            LOGGER.error(f"ShrutiAPI download error: {e}")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        return None

    async def download_song(self, link: str) -> Optional[str]:
        return await self._download_media(link, "audio", 300)

    async def download_video(self, link: str) -> Optional[str]:
        return await self._download_media(link, "video", 600)

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        
        results = VideosSearch(link, limit=1)
        res_dict = await results.next()
        if not res_dict or not res_dict.get("result"):
            return "Unknown", "03:00", 180, "", link

        result = res_dict["result"][0]
        title = result.get("title", "Unknown")
        duration_min = result.get("duration", "03:00")
        thumbnails = result.get("thumbnails", [])
        thumbnail = thumbnails[0]["url"].split("?")[0] if thumbnails else ""
        vidid = result.get("id", "")
        duration_sec = int(self.time_to_seconds(duration_min)) if duration_min else 180
        return title, duration_min, duration_sec, thumbnail, vidid


class YouTubeData(MusicService):
    """Bridge class for cloudymusic integration using ShrutiAPI."""

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = query.strip() if query else None
        self.yt = YouTubeAPI()

    def is_valid(self) -> bool:
        if not self.query:
            return False
        return bool(re.search(self.yt.regex, self.query))

    async def get_info(self) -> Union[PlatformTracks, types.Error]:
        """Required abstract method implementation for MusicService."""
        if not self.query or not self.is_valid():
            return types.Error(code=400, message="Invalid YouTube URL provided")

        title, duration_min, duration_sec, thumbnail, vidid = await self.yt.details(self.query)
        track = MusicTrack(
            id=vidid,
            name=title,
            duration=duration_sec,
            cover=thumbnail,
            year=0,
            url=f"https://www.youtube.com/watch?v={vidid}",
            platform="youtube"
        )
        return PlatformTracks(tracks=[track])

    async def search(self) -> Union[PlatformTracks, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No search query provided")

        if self.is_valid():
            return await self.get_info()

        try:
            search = VideosSearch(self.query, limit=5)
            results = await search.next()
            if not results or not results.get("result"):
                return types.Error(code=404, message=f"No results found for: {self.query}")

            tracks = []
            for video in results["result"]:
                vid = video.get("id")
                title = video.get("title", "Unknown Title")
                duration = video.get("duration", "03:00")
                duration_sec = self.yt.time_to_seconds(duration)
                thumbs = video.get("thumbnails", [])
                cover = thumbs[0]["url"].split("?")[0] if thumbs else ""

                tracks.append(
                    MusicTrack(
                        id=vid,
                        name=title,
                        duration=duration_sec,
                        cover=cover,
                        year=0,
                        url=f"https://www.youtube.com/watch?v={vid}",
                        platform="youtube"
                    )
                )
            return PlatformTracks(tracks=tracks)
        except Exception as error:
            return types.Error(code=500, message=f"Search failed: {str(error)}")

    async def get_track(self) -> Union[TrackInfo, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No track identifier provided")

        link = self.query if re.match("^https?://", self.query) else self.base + self.query
        title, duration_min, duration_sec, thumbnail, vidid = await self.yt.details(link)

        return TrackInfo(
            cdnurl="None",
            key="None",
            name=title,
            tc=vidid,
            cover=thumbnail,
            duration=duration_sec,
            platform="youtube",
            url=f"https://youtube.com/watch?v={vidid}",
        )

    async def download_track(self, track: TrackInfo, video: bool = False) -> Union[Path, types.Error]:
        if not track or not track.tc:
            return types.Error(code=400, message="Invalid track information provided")

        file_path = await self.yt.download_video(track.tc) if video else await self.yt.download_song(track.tc)
        if not file_path or not os.path.exists(file_path):
            return types.Error(code=500, message="Failed to download track from ShrutiAPI")

        return Path(file_path)
