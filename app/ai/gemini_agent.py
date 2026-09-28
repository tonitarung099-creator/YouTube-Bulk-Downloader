from __future__ import annotations

import os
import re
from typing import Iterable

from google import genai
from google.genai import types

from app.models.commands import AgentResult, DownloadIntent


SYSTEM_INSTRUCTION = """
Kamu adalah parser perintah untuk aplikasi YouTube Bulk Downloader.
Tugasmu HANYA mengubah bahasa manusia menjadi DownloadIntent yang terstruktur.

Aturan:
- Jangan pernah menghasilkan perintah shell, Python, PowerShell, CMD, atau kode.
- Jangan mengarang URL. Jika tidak ada URL, biarkan null.
- Jika pengguna menyebut playlist, source_type=playlist.
- Jika pengguna menyebut channel/kanal/semua video channel, source_type=channel.
- Jika pengguna menyebut satu video, source_type=video.
- "musik saja", "audio saja", "mp3" => mode=audio.
- "jangan shorts" => include_shorts=false.
- "jangan live" => include_live=false.
- "subtitle/sub" => include_subtitles=true.
- "thumbnail" => include_thumbnail=true.
- Jika pengguna meminta download, action=download.
- Jika hanya meminta cek/lihat/analisis isi URL, action=analyze.
- Gunakan Bahasa Indonesia singkat pada explanation.
- Jangan melakukan aksi di luar schema.
""".strip()


class GeminiLanguageAgent:
    """Gemini hanya memahami intent; yt-dlp tetap menjadi executor lokal."""

    def __init__(
        self,
        api_keys: Iterable[str] | None = None,
        model: str | None = None,
    ) -> None:
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.api_keys = self._load_keys(api_keys)
        self._cursor = 0

    @staticmethod
    def _load_keys(api_keys: Iterable[str] | None) -> list[str]:
        if api_keys is not None:
            keys = list(api_keys)
        else:
            multi = os.getenv("GEMINI_API_KEYS", "")
            single = os.getenv("GEMINI_API_KEY", "")
            keys = [*multi.split(","), single]

        clean: list[str] = []
        for key in keys:
            key = key.strip()
            if key and key not in clean:
                clean.append(key)
        return clean[:100]

    def interpret(self, text: str, current_url: str | None = None) -> AgentResult:
        text = text.strip()
        if not text:
            return AgentResult(
                intent=DownloadIntent(explanation="Perintah kosong."),
                provider="local_fallback",
            )

        if not self.api_keys:
            return AgentResult(
                intent=self._local_fallback(text, current_url),
                provider="local_fallback",
            )

        errors: list[Exception] = []
        for _ in range(len(self.api_keys)):
            key_index = self._cursor % len(self.api_keys)
            api_key = self.api_keys[key_index]
            self._cursor = (self._cursor + 1) % len(self.api_keys)

            try:
                client = genai.Client(api_key=api_key)
                prompt = text
                if current_url and current_url not in text:
                    prompt += f"\nURL aktif di aplikasi: {current_url}"

                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=DownloadIntent,
                        temperature=0.1,
                    ),
                )
                intent = DownloadIntent.model_validate_json(response.text)
                if not intent.url and current_url:
                    intent.url = current_url
                return AgentResult(
                    intent=intent,
                    provider="gemini",
                    key_index=key_index,
                )
            except Exception as exc:  # SDK exception types can vary by version.
                errors.append(exc)
                if not self._should_rotate(exc):
                    break

        intent = self._local_fallback(text, current_url)
        if errors:
            intent.explanation += " Gemini tidak tersedia, memakai parser lokal."
        return AgentResult(intent=intent, provider="local_fallback")

    @staticmethod
    def _should_rotate(exc: Exception) -> bool:
        message = str(exc).lower()
        rotate_markers = (
            "429",
            "quota",
            "rate limit",
            "resource_exhausted",
            "resource exhausted",
            "401",
            "403",
            "api key",
        )
        return any(marker in message for marker in rotate_markers)

    @staticmethod
    def _local_fallback(text: str, current_url: str | None) -> DownloadIntent:
        lower = text.lower()
        url_match = re.search(r"https?://\S+", text)
        url = url_match.group(0).rstrip(".,);]") if url_match else current_url

        if any(word in lower for word in ("playlist", "daftar putar")):
            source_type = "playlist"
        elif any(word in lower for word in ("channel", "kanal", "semua video")):
            source_type = "channel"
        elif url:
            source_type = "auto"
        else:
            source_type = "auto"

        action = "download"
        if any(word in lower for word in ("cek", "analisis", "lihat isi", "tampilkan")):
            action = "analyze"
        elif "pause" in lower or "jeda" in lower:
            action = "pause"
        elif "lanjut" in lower or "resume" in lower:
            action = "resume"
        elif "batal" in lower or "cancel" in lower:
            action = "cancel"

        quality = "best"
        for q in ("2160p", "1440p", "1080p", "720p", "480p", "360p"):
            if q in lower:
                quality = q
                break

        mode = "audio" if any(
            word in lower for word in ("audio saja", "musik saja", "mp3", "m4a", "opus")
        ) else "video"

        audio_format = "best"
        for fmt in ("mp3", "m4a", "opus"):
            if fmt in lower:
                audio_format = fmt
                break

        return DownloadIntent(
            action=action,
            source_type=source_type,
            url=url,
            mode=mode,
            quality=quality,
            audio_format=audio_format,
            include_shorts=not any(
                phrase in lower for phrase in ("jangan shorts", "tanpa shorts", "skip shorts")
            ),
            include_live=not any(
                phrase in lower for phrase in ("jangan live", "tanpa live", "skip live")
            ),
            include_subtitles=any(
                word in lower for word in ("subtitle", "subtitel", "srt", "sub ")
            ),
            include_thumbnail="thumbnail" in lower,
            use_archive=not any(
                phrase in lower for phrase in ("download ulang", "ulang semua")
            ),
            explanation="Perintah dipahami dengan parser lokal.",
        )
