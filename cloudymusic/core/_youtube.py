# Copyright (c) 2025 strad-dev131
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the cloudymusic project. All rights reserved where applicable.

import asyncio
import os
import random
import re
from pathlib import Path
from typing import Any, Optional, Dict, Union

from py_yt import Playlist, VideosSearch
from pytdbot import types

from cloudymusic.logger import LOGGER

from ._config import config
from ._dataclass import MusicTrack, PlatformTracks, TrackInfo
from ._downloader import MusicService
from ._httpx import HttpxClient


class YouTubeUtils:
    """Utility class for YouTube-related operations using ShrutiAPI."""

    YOUTUBE_VIDEO_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com|youtu\.be)/"
        r"(?:watch\?v=|embed/|v/|shorts/)?([\w-]{11})(?:\?|&|$)",
        re.IGNORECASE,
    )
    YOUTUBE_PLAYLIST_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com)/"
        r"(?:playlist|watch)\?.*\blist=([\w-]+)",
        re.IGNORECASE,
    )
    YOUTUBE_SHORTS_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]+)",
        re.IGNORECASE,
    )

    @staticmethod
    def clean_query(query: str) -> str:
        """Clean the query by removing unnecessary parameters."""
        return query.split("&")[0].split("#")[0].strip()

    @staticmethod
    def is_valid_url(url: Optional[str]) -> bool:
        if not url:
            return False
        return any(
            pattern.match(url)
            for pattern in (
                YouTubeUtils.YOUTUBE_VIDEO_PATTERN,
                YouTubeUtils.YOUTUBE_PLAYLIST_PATTERN,
                YouTubeUtils.YOUTUBE_SHORTS_PATTERN,
            )
        )

    @staticmethod
    async def normalize_youtube_url(url: str) -> Optional[str]:
        """Normalize different YouTube URL formats to standard watch URL."""
        if not url:
            return None

        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].partition("?")[0].partition("#")[0]
            return f"https://www.youtube.com/watch?v={video_id}"

        if "youtube.com/shorts/" in url:
            video_id = url.split("youtube.com/shorts/")[1].split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"

        return url

    @staticmethod
    def create_platform_tracks(data: Dict[str, Any]) -> PlatformTracks:
        """Create PlatformTracks object from data."""
        if not data or not data.get("results"):
            return PlatformTracks(tracks=[])

        valid_tracks = [
            MusicTrack(**track)
            for track in data["results"]
            if track and (track.get("id") or track.get("tc"))
        ]
        return PlatformTracks(tracks=valid_tracks)

    @staticmethod
    def format_track(track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format track data into a consistent structure."""
        duration = track_data.get("duration", 0)
        if isinstance(duration, str):
            duration = YouTubeUtils.duration_to_seconds(duration)

        cover_url = track_data.get("cover", "")
        if not cover_url and (thumbnails := track_data.get("thumbnails")):
            for thumb in reversed(thumbnails):
                if url := thumb.get("url"):
                    cover_url = url
                    break

        video_id = track_data.get("id") or track_data.get("tc", "")
        return {
            "id": video_id,
            "name": track_data.get("name") or track_data.get("title", "Unknown Title"),
            "duration": duration,
            "cover": cover_url,
            "year": 0,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "platform": "youtube",
        }

    @staticmethod
    async def create_track_info(track_data: dict[str, Any]) -> TrackInfo:
        """Create TrackInfo from formatted track data."""
        video_id = track_data.get("id") or track_data.get("tc", "")
        return TrackInfo(
            cdnurl=track_data.get("cdnurl", "None"),
            key=track_data.get("key", "None"),
            name=track_data.get("name", "Unknown Title"),
            tc=video_id,
            cover=track_data.get("cover", ""),
            duration=track_data.get("duration", 0),
            platform="youtube",
            url=f"https://youtube.com/watch?v={video_id}",
        )

    @staticmethod
    def duration_to_seconds(duration: str) -> int:
        """Convert duration string (HH:MM:SS or MM:SS) to seconds."""
        if not duration:
            return 0
        try:
            parts = list(map(int, duration.split(":")))
            if len(parts) == 3:
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            return parts[0] * 60 + parts[1] if len(parts) == 2 else parts[0]
        except (ValueError, AttributeError):
            return 0

    @staticmethod
    async def get_cookie_file() -> Optional[str]:
        """Get a random cookie file from the 'cookies' directory."""
        cookie_dir = "cloudymusic/cookies"
        try:
            if not os.path.exists(cookie_dir):
                return None
            files = await asyncio.to_thread(os.listdir, cookie_dir)
            cookies_files = [f for f in files if f.endswith(".txt")]
            if not cookies_files:
                return None
            random_file = random.choice(cookies_files)
            return os.path.join(cookie_dir, random_file)
        except Exception:
            return None

    @staticmethod
    async def download_with_shrutibots_api(
        video_id: str, is_video: bool = False
    ) -> Union[None, Path]:
        """Download audio/video using ShrutiAPI (/download endpoint)."""
        from cloudymusic import client

        api_key = config.API_KEY
        if not api_key:
            LOGGER.warning("ShrutiAPI key is missing in configuration.")
            return None

        httpx = HttpxClient()
        media_type = "video" if is_video else "audio"
        target_url = f"https://api.shrutibots.in/download?url={video_id}&type={media_type}&api_key={api_key}"
        
        LOGGER.info(f"Requesting download from ShrutiAPI for video_id: {video_id}")

        try:
            response_data = await httpx.make_request(target_url)
            if response_data:
                dl_url = None
                if isinstance(response_data, dict):
                    dl_url = (
                        response_data.get("cdnurl")
                        or response_data.get("url")
                        or response_data.get("link")
                        or response_data.get("data", {}).get("url")
                    )
                elif isinstance(response_data, str):
                    dl_url = response_data

                if not dl_url or not isinstance(dl_url, str):
                    # အကယ်၍ API က ဖိုင်တိုက်ရိုက်ပေးလိုက်ပါက သို့မဟုတ် download ရလဒ်ဖြစ်ပါက
                    pass

                # အကယ်၍ ShrutiAPI က direct file download link ပေးလျှင်
                if dl_url and not re.fullmatch(r"https:\/\/t\.me\/([a-zA-Z0-9_]{5,})\/(\d+)", dl_url):
                    dl = await httpx.download_file(dl_url)
                    return dl.file_path if dl.success else None

                # Telegram message link ဖြစ်ပါက
                if dl_url:
                    info = await client.getMessageLinkInfo(dl_url)
                    if not isinstance(info, types.Error) and info.message is not None:
                        msg = await client.getMessage(info.chat_id, info.message.id)
                        if not isinstance(msg, types.Error):
                            file = await msg.download()
                            if not isinstance(file, types.Error):
                                return Path(file.path)
        except Exception as e:
            LOGGER.error(f"ShrutiAPI download failed: {e}")

        return None

    @staticmethod
    def _build_ytdlp_params(
        video_id: str, video: bool, cookie_file: Optional[str]
    ) -> list[str]:
        output_template = str(config.DOWNLOADS_DIR / "%(id)s.%(ext)s")
        format_selector = (
            "bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]"
            if video
            else "bestaudio[ext=m4a]/bestaudio[ext=mp4]/bestaudio[ext=webm]/bestaudio/best"
        )

        ytdlp_params = [
            "yt-dlp",
            "--no-warnings",
            "--quiet",
            "--geo-bypass",
            "--retries",
            "2",
            "--continue",
            "--no-part",
            "--concurrent-fragments",
            "3",
            "--socket-timeout",
            "10",
            "--throttled-rate",
            "100K",
            "--retry-sleep",
            "1",
            "--no-write-thumbnail",
            "--no-write-info-json",
            "--no-embed-metadata",
            "--no-embed-chapters",
            "--no-embed-subs",
            "-o",
            output_template,
            "-f",
            format_selector,
        ]

        if video:
            ytdlp_params += ["--merge-output-format", "mp4"]

        if config.PROXY:
            ytdlp_params += ["--proxy", config.PROXY]
        elif cookie_file:
            ytdlp_params += ["--cookies", cookie_file]

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        ytdlp_params += [video_url, "--print", "after_move:filepath"]

        return ytdlp_params

    @staticmethod
    async def download_with_yt_dlp(video_id: str, video: bool) -> Optional[Path]:
        cookie_file = await YouTubeUtils.get_cookie_file()
        ytdlp_params = YouTubeUtils._build_ytdlp_params(video_id, video, cookie_file)

        try:
            proc = await asyncio.create_subprocess_exec(
                *ytdlp_params,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)

            if proc.returncode != 0:
                return None

            downloaded_path_str = stdout.decode().strip()
            if not downloaded_path_str:
                return None

            downloaded_path = Path(downloaded_path_str)
            if not downloaded_path.exists():
                return None

            return downloaded_path
        except Exception:
            return None


class YouTubeData(MusicService):
    """Handles YouTube music data operations using ShrutiAPI as primary source."""

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = YouTubeUtils.clean_query(query) if query else None

    def is_valid(self) -> bool:
        return YouTubeUtils.is_valid_url(self.query)

    async def get_info(self) -> Union[PlatformTracks, types.Error]:
        if not self.query or not self.is_valid():
            return types.Error(code=400, message="Invalid YouTube URL provided")

        data = await self._fetch_data(self.query)
        if not data:
            return types.Error(code=404, message="Could not retrieve track information")

        return YouTubeUtils.create_platform_tracks(data)

    async def search(self) -> Union[PlatformTracks, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No search query provided")

        if self.is_valid():
            return await self.get_info()

        # VideosSearch ကို အသုံးပြု၍ သီချင်းရှာဖွေခြင်း (ShrutiAPI တွင် search endpoint မပါရှိသောကြောင့် pytube/py-yt ကိုသုံးသည်)
        try:
            search = VideosSearch(self.query, limit=5)
            results = await search.next()
            if not results or not results.get("result"):
                return types.Error(code=404, message=f"No results found for: {self.query}")

            tracks = [
                MusicTrack(**YouTubeUtils.format_track(video))
                for video in results["result"]
            ]
            return PlatformTracks(tracks=tracks)
        except Exception as error:
            return types.Error(code=500, message=f"Search failed: {str(error)}")

    async def get_track(self) -> Union[TrackInfo, types.Error]:
        if not self.query:
            return types.Error(code=400, message="No track identifier provided")

        url = (
            self.query
            if re.match("^https?://", self.query)
            else f"https://youtube.com/watch?v={self.query}"
        )

        data = await self._fetch_data(url)
        if not data or not data.get("results"):
            return types.Error(code=404, message="Could not retrieve track details")

        return await YouTubeUtils.create_track_info(data["results"][0])

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Union[Path, types.Error]:
        if not track:
            return types.Error(code=400, message="Invalid track information provided")

        # 1. ShrutiAPI ကို ဦးစားပေး၍ ဒေါင်းလုပ်ဆွဲခြင်း
        if api_result := await YouTubeUtils.download_with_shrutibots_api(track.tc, video):
            return api_result

        # 2. ShrutiAPI မအောင်မြင်မှသာ yt-dlp သို့ fallback သွားခြင်း
        dl_path = await YouTubeUtils.download_with_yt_dlp(track.tc, video)
        if not dl_path:
            return types.Error(code=500, message="Failed to download track from YouTube")

        return dl_path

    async def _fetch_data(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            if YouTubeUtils.YOUTUBE_PLAYLIST_PATTERN.match(url):
                return await self._get_playlist_data(url)
            return await self._get_video_data(url)
        except Exception:
            return None

    @staticmethod
    async def _get_video_data(url: str) -> Optional[Dict[str, Any]]:
        normalized_url = await YouTubeUtils.normalize_youtube_url(url)
        if not normalized_url:
            return None

        try:
            search = VideosSearch(normalized_url, limit=1)
            results = await search.next()
            if results and results.get("result"):
                return {"results": [YouTubeUtils.format_track(results["result"][0])]}
        except Exception:
            pass
        return None

    @staticmethod
    async def _get_playlist_data(url: str) -> Optional[Dict[str, Any]]:
        try:
            playlist = await Playlist.getVideos(url)
            if not playlist or not playlist.get("videos"):
                return None
            return {
                "results": [
                    YouTubeUtils.format_track(track)
                    for track in playlist["videos"]
                    if track.get("id")
                ]
            }
        except Exception:
            return None
