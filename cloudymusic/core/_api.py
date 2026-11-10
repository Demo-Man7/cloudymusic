# Copyright (c) 2025 strad-dev131
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the cloudymusic project. All rights reserved where applicable.

import re
from pathlib import Path
from typing import Optional, Union

from pytdbot import types
from cloudymusic.logger import LOGGER

from ._config import config
from ._downloader import MusicService
from ._httpx import HttpxClient
from ._spotify_dl_helper import SpotifyDownload
from ._dataclass import PlatformTracks, MusicTrack, TrackInfo


class ApiData(MusicService):
    """API integration handler for multiple music streaming platforms using OneGrab API."""

    URL_PATTERNS = {
        "apple_music": re.compile(
            r"^(https?://)?([a-z0-9-]+\.)*music\.apple\.com/"
            r"([a-z]{2}/)?"
            r"(album|playlist|song)/[a-zA-Z0-9\-._]+/(pl\.[a-zA-Z0-9]+|\d+)(\?.*)?$",
            re.IGNORECASE,
        ),
        "spotify": re.compile(
            r"^(https?://)?([a-z0-9-]+\.)*spotify\.com/"
            r"(track|playlist|album|artist)/[a-zA-Z0-9]+(\?.*)?$",
            re.IGNORECASE,
        ),
        "soundcloud": re.compile(
            r"^(https?://)?([a-z0-9-]+\.)*soundcloud\.com/"
            r"[a-zA-Z0-9_-]+(/(sets)?/[a-zA-Z0-9_-]+)?(\?.*)?$",
            re.IGNORECASE,
        ),
    }

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = self._sanitize_query(query) if query else None
        self.api_url = config.API_URL.rstrip("/") if config.API_URL else "https://api.onegrab.fun"
        self.api_key = config.API_KEY
        self.client = HttpxClient()

    @staticmethod
    def _sanitize_query(query: str) -> str:
        return query.strip().split("?")[0].split("#")[0]

    def is_valid(self) -> bool:
        if not all([self.query, self.api_key, self.api_url]):
            return False
        return any(pattern.match(self.query) for pattern in self.URL_PATTERNS.values())

    def _get_headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    async def _make_api_request(
        self, endpoint: str, params: Optional[dict] = None
    ) -> Optional[dict]:
        # OneGrab API endpoint များအတွက် /api ကို ပေါင်းစပ်ပေးခြင်း
        request_url = f"{self.api_url}/api/{endpoint.lstrip('/')}"
        return await self.client.make_request(request_url, params=params, headers=self._get_headers())

    async def get_info(self) -> Union[PlatformTracks, types.Error]:
        """Retrieve track information from a valid URL using OneGrab /api/track or /api/get_url."""
        if not self.query or not self.is_valid():
            return types.Error(400, "Invalid or unsupported URL provided")

        response = await self._make_api_request("track", {"url": self.query})
        if response and isinstance(response, dict):
            # PlatformTracks format သို့ ပြောင်းလဲခြင်း
            tracks = [MusicTrack(**response)] if "id" in response or "tc" in response else []
            if tracks:
                return PlatformTracks(tracks=tracks)
        
        # Fallback to get_url if track fails
        response = await self._make_api_request("get_url", {"url": self.query, "video": "false"})
        return self._parse_tracks_response(response) or types.Error(
            404, "No track information found"
        )

    async def search(self) -> Union[PlatformTracks, types.Error]:
        """Search for tracks across supported platforms using OneGrab /api/search."""
        if not self.query:
            return types.Error(400, "No search query provided")

        if self.is_valid():
            return await self.get_info()

        # OneGrab API ၏ search endpoint (`/api/search?query=...`) ကို သုံးခြင်း
        response = await self._make_api_request("search", {"query": self.query, "limit": 5})
        return self._parse_tracks_response(response) or types.Error(
            404, "No results found for search query"
        )

    async def get_track(self) -> Union[TrackInfo, types.Error]:
        """Get detailed track information using OneGrab /api/track."""
        if not self.query:
            return types.Error(400, "No track identifier provided")

        target_url = self.query if re.match("^https?://", self.query) else f"https://open.spotify.com/track/{self.query}"
        response = await self._make_api_request("track", {"url": target_url})
        return (
            TrackInfo(**response) if response and isinstance(response, dict) else types.Error(404, "Track not found")
        )

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Union[Path, types.Error]:
        if not track:
            return types.Error(400, "Invalid track information provided")

        if track.platform.lower() == "spotify":
            spotify_result = await SpotifyDownload(track).process()
            if isinstance(spotify_result, types.Error):
                LOGGER.error(f"Spotify download failed: {spotify_result.message}")
            return spotify_result

        # OneGrab API မှ cdnurl မပါလာပါက /api/get_url မှ တဆင့် cdnurl အသစ် တောင်းခံခြင်း
        cdn_url = track.cdnurl
        if not cdn_url or cdn_url == "None":
            try:
                get_url_resp = await self._make_api_request("get_url", {"url": track.url, "video": str(video).lower()})
                if get_url_resp and isinstance(get_url_resp, dict):
                    cdn_url = get_url_resp.get("cdnurl") or get_url_resp.get("results")
            except Exception as e:
                LOGGER.error(f"Failed to fetch cdnurl from OneGrab: {e}")

        if not cdn_url or cdn_url == "None":
            error_msg = f"No download URL available for track: {track.tc}"
            LOGGER.error(error_msg)
            return types.Error(400, error_msg)

        download_path = config.DOWNLOADS_DIR / f"{track.tc}.mp3"
        download_result = await self.client.download_file(cdn_url, download_path)

        if not download_result.success:
            LOGGER.warning(
                f"Download failed for track {track.tc}: {download_result.error}"
            )
            return types.Error(
                500, f"Download failed: {download_result.error or track.tc}"
            )

        return download_result.file_path

    @staticmethod
    def _parse_tracks_response(
        response_data: Optional[dict],
    ) -> Union[PlatformTracks, types.Error]:
        if not response_data:
            return types.Error(404, "Invalid API response format")

        results = response_data.get("results") or response_data.get("data")
        if not results:
            if isinstance(response_data, dict) and ("id" in response_data or "tc" in response_data):
                results = [response_data]
            else:
                return types.Error(404, "No valid tracks found")

        if isinstance(results, dict):
            results = [results]

        try:
            tracks = [
                MusicTrack(**track_data)
                for track_data in results
                if isinstance(track_data, dict)
            ]
            return (
                PlatformTracks(tracks=tracks)
                if tracks
                else types.Error(404, "No valid tracks found")
            )
        except Exception as parse_error:
            LOGGER.error(f"Failed to parse tracks: {parse_error}")
            return types.Error(500, "Failed to process track data")
