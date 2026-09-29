from __future__ import annotations

import os
import re
from typing import Iterable

from google import genai
from google.genai import types

from app.models.commands import AgentResult, DownloadIntent, DownloadIntentPatch
from app.models.intent_patch import apply_intent_patch

ACTION_SYSTEM_INSTRUCTION = """Kamu adalah agent aksi untuk aplikasi Pengunduh YouTube Massal. Keluarkan HANYA patch field DownloadIntentPatch yang benar-benar diminta pengguna; jangan mengisi default untuk field yang tidak disebut. Jangan membuat shell/Python/PowerShell/CMD atau URL palsu. Perintah cek/analisis URL memakai action=analyze. Jeda/lanjut/batal memakai action masing-masing. Jika pengguna meminta cari/carikan/temukan sesuatu di YouTube tanpa URL, gunakan action=search, source_type=search, dan isi search_query dengan kata pencarian yang ringkas. Jika pengguna juga meminta hasil pencarian langsung diunduh, set download_after_search=true. Untuk kata 'semua' pada pencarian, gunakan search_limit=100 kecuali pengguna menyebut angka lain; batas maksimum 200. Gunakan Bahasa Indonesia singkat pada explanation. Pahami negasi: 'jangan unduh subtitle' berarti false, 'jangan download ulang' berarti use_archive=true (hindari unduh ulang), sedangkan 'download ulang' berarti use_archive=false. 'tambahkan subtitle Indonesia' hanya mengubah subtitle/language."""

CHAT_SYSTEM_INSTRUCTION = """Kamu adalah asisten Gemini di dalam aplikasi Pengunduh YouTube Massal. Jawab pertanyaan pengguna secara natural dalam Bahasa Indonesia. Kamu boleh menjawab pertanyaan umum, menjelaskan fitur aplikasi, memberi saran format/kualitas unduhan, dan membantu pengguna merumuskan perintah. Jangan mengaku sudah menjalankan aksi aplikasi dari mode chat. Aksi aplikasi yang benar-benar didukung adalah: analisis URL YouTube, mencari video di YouTube, mengunduh hasil/video/playlist/channel, memilih video atau audio, memilih MP4/MKV/WebM atau MP3/M4A/Opus, mengatur kualitas, subtitle, thumbnail, metadata, Shorts/Live, jumlah unduhan paralel, jeda, lanjut, dan batal. Jika ditanya 'kamu bisa melakukan apa saja?', jelaskan kemampuan chat + kemampuan aksi tersebut dengan ringkas dan jelas."""

GEMINI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
)


class GeminiLanguageAgent:
    def __init__(self, api_keys: Iterable[str] | None = None, model: str | None = None) -> None:
        requested = (model or os.getenv("GEMINI_MODEL", "")).strip()
        self.models: tuple[str, ...] = GEMINI_MODELS
        self.model = GEMINI_MODELS[0]
        self.set_model(requested)
        self.last_model: str | None = None
        self.last_error: str | None = None
        self.api_keys = self._load_keys(api_keys)
        self._cursor = 0
        self._chat_history: list[tuple[str, str]] = []

    @staticmethod
    def _normalize_keys(values: Iterable[str]) -> list[str]:
        clean: list[str] = []
        for value in values:
            key = str(value).strip()
            if key and key not in clean:
                clean.append(key)
        return clean[:100]

    @classmethod
    def _load_keys(cls, api_keys: Iterable[str] | None) -> list[str]:
        if api_keys is not None:
            return cls._normalize_keys(api_keys)
        values = [*os.getenv("GEMINI_API_KEYS", "").split(","), os.getenv("GEMINI_API_KEY", "")]
        return cls._normalize_keys(values)

    def set_api_keys(self, api_keys: Iterable[str]) -> None:
        self.api_keys = self._normalize_keys(api_keys)
        self._cursor = 0
        self.last_error = None

    def set_model(self, model: str | None) -> None:
        requested = str(model or "").strip()
        if requested in GEMINI_MODELS:
            self.models = (requested,) + tuple(item for item in GEMINI_MODELS if item != requested)
        else:
            self.models = GEMINI_MODELS
        self.model = self.models[0]

    def _client_call(self, key_index: int, model_name: str, text: str, config) -> object:
        client = genai.Client(api_key=self.api_keys[key_index])
        return client.models.generate_content(model=model_name, contents=text, config=config)

    def test_connection(self) -> tuple[str, int]:
        if not self.api_keys:
            raise RuntimeError("Belum ada API key Gemini. Masukkan API key di menu Pengaturan.")
        self.last_error = None
        config = types.GenerateContentConfig(temperature=0.0, max_output_tokens=8)
        for model_name in self.models:
            for _ in range(len(self.api_keys)):
                idx = self._cursor % len(self.api_keys)
                self._cursor = (self._cursor + 1) % len(self.api_keys)
                try:
                    self._client_call(idx, model_name, "Balas hanya: OK", config)
                    self.last_model = model_name
                    return model_name, idx
                except Exception as exc:
                    self.last_error = str(exc)
                    if not self._should_rotate(exc):
                        break
        raise RuntimeError(self._friendly_error())

    @staticmethod
    def _looks_like_action(text: str) -> bool:
        lower = " ".join(text.casefold().split())
        if re.search(r"https?://\S+", text):
            return True
        question_starts = (
            "apa ", "apa itu ", "kenapa ", "mengapa ", "bagaimana ", "siapa ", "kapan ", "dimana ",
            "di mana ", "jelaskan ", "menurutmu ", "kamu bisa ", "bisa jelaskan ", "tolong jelaskan ",
        )
        imperative = (
            "unduh", "download", "ambil semua", "carikan", "cari ", "temukan", "analisis", "cek ",
            "jeda", "pause", "lanjutkan", "resume", "batalkan", "cancel", "sertakan", "jangan unduh",
            "jangan download", "ubah ke", "jadikan", "setel", "gunakan format", "pilih format",
        )
        if any(x in lower for x in imperative):
            return True
        if lower.startswith(question_starts):
            return False
        settings = ("1080p", "720p", "480p", "360p", "2160p", "1440p", " mp3", " mp4", " m4a", " mkv", " webm", " opus")
        return any(x in f" {lower}" for x in settings) and any(x in lower for x in ("pakai", "pilih", "format", "kualitas"))

    def interpret(self, text: str, current_url: str | None = None, current_intent: DownloadIntent | None = None) -> AgentResult:
        text = text.strip()
        base = current_intent.model_copy(deep=True) if current_intent else DownloadIntent()
        if current_url:
            base.url = current_url
        if not text:
            patch = DownloadIntentPatch(action="unknown", explanation="Perintah kosong.")
            return AgentResult(intent=apply_intent_patch(base, patch), patch=patch, provider="local_fallback")
        self.last_error = None

        if not self._looks_like_action(text):
            return self._chat(text, base)

        if self.api_keys:
            context = f"\nURL aktif: {current_url}" if current_url and current_url not in text else ""
            config = types.GenerateContentConfig(
                system_instruction=ACTION_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=DownloadIntentPatch,
                temperature=0.0,
            )
            for model_name in self.models:
                for _ in range(len(self.api_keys)):
                    idx = self._cursor % len(self.api_keys)
                    self._cursor = (self._cursor + 1) % len(self.api_keys)
                    try:
                        response = self._client_call(idx, model_name, text + context, config)
                        patch = DownloadIntentPatch.model_validate_json(response.text)
                        self.last_model = model_name
                        return AgentResult(
                            intent=apply_intent_patch(base, patch),
                            patch=patch,
                            provider="gemini",
                            key_index=idx,
                            kind="action",
                        )
                    except Exception as exc:
                        self.last_error = str(exc)
                        if not self._should_rotate(exc):
                            break
        patch = self._local_patch(text, current_url)
        return AgentResult(intent=apply_intent_patch(base, patch), patch=patch, provider="local_fallback", kind="action")

    def _chat(self, text: str, base: DownloadIntent) -> AgentResult:
        if self.api_keys:
            history_lines: list[str] = []
            for role, message in self._chat_history[-8:]:
                history_lines.append(f"{role}: {message}")
            prompt = ""
            if history_lines:
                prompt += "Percakapan sebelumnya:\n" + "\n".join(history_lines) + "\n\n"
            prompt += "Pengguna: " + text
            config = types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_INSTRUCTION,
                temperature=0.4,
                max_output_tokens=900,
            )
            for model_name in self.models:
                for _ in range(len(self.api_keys)):
                    idx = self._cursor % len(self.api_keys)
                    self._cursor = (self._cursor + 1) % len(self.api_keys)
                    try:
                        response = self._client_call(idx, model_name, prompt, config)
                        reply = str(getattr(response, "text", "") or "").strip()
                        if not reply:
                            raise RuntimeError("Gemini mengembalikan jawaban kosong.")
                        self.last_model = model_name
                        self._remember_chat(text, reply)
                        return AgentResult(intent=base, provider="gemini", key_index=idx, kind="chat", reply_text=reply)
                    except Exception as exc:
                        self.last_error = str(exc)
                        if not self._should_rotate(exc):
                            break
        reply = self._local_chat_reply(text)
        self._remember_chat(text, reply)
        return AgentResult(intent=base, provider="local_fallback", kind="chat", reply_text=reply)

    def _remember_chat(self, user_text: str, assistant_text: str) -> None:
        self._chat_history.extend((("Pengguna", user_text[:1200]), ("Asisten", assistant_text[:2000])))
        self._chat_history = self._chat_history[-16:]

    def _local_chat_reply(self, text: str) -> str:
        lower = text.casefold()
        if "bisa" in lower and any(x in lower for x in ("apa saja", "ngapain", "melakukan apa", "fitur")):
            return (
                "Saya bisa diajak tanya-jawab dan juga mengendalikan fitur aplikasi. Contohnya: analisis URL YouTube, "
                "cari video/lagu, unduh video/playlist/channel, pilih MP4 atau audio MP3/M4A/Opus, atur kualitas, "
                "subtitle, thumbnail, Shorts/Live, jumlah unduhan paralel, serta jeda/lanjut/batal. Untuk jawaban "
                "umum yang lebih luas, masukkan API Gemini lalu gunakan panel chat ini seperti asisten biasa."
            )
        if not self.api_keys:
            return "Mode chat Gemini memerlukan API key. Masukkan API di Pengaturan, lalu Anda bisa bertanya normal di panel ini."
        return "Saya siap menjawab pertanyaan atau membantu menjalankan perintah aplikasi."

    def _friendly_error(self) -> str:
        raw = (self.last_error or "Gemini tidak dapat dihubungi.").strip()
        lower = raw.lower()
        if any(x in lower for x in ("401", "api key not valid", "invalid api key", "api_key_invalid")):
            return "API key Gemini tidak valid. Periksa key lalu simpan kembali."
        if any(x in lower for x in ("429", "quota", "resource_exhausted", "rate limit")):
            return "Kuota/rate limit API Gemini habis untuk key yang tersedia."
        if "404" in lower or "model" in lower and "not found" in lower:
            return "Model Gemini yang dipilih belum tersedia untuk API key/proyek ini."
        if any(x in lower for x in ("timeout", "timed out", "connection", "network")):
            return "Koneksi ke Gemini gagal. Periksa internet lalu coba lagi."
        return raw[:400]

    @staticmethod
    def _should_rotate(exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(
            x in msg
            for x in (
                "429", "quota", "rate limit", "resource_exhausted", "401", "403", "api key", "404", "model not found",
            )
        )

    @staticmethod
    def _local_patch(text: str, current_url: str | None = None) -> DownloadIntentPatch:
        lower = " ".join(text.lower().split())
        data = {"explanation": "Perintah dipahami dengan parser lokal."}
        m = re.search(r"https?://\S+", text)
        if m:
            data["url"] = m.group(0).rstrip(".,);]")
        if any(x in lower for x in ("jeda", "pause")):
            data["action"] = "pause"
        elif any(x in lower for x in ("lanjut", "resume")):
            data["action"] = "resume"
        elif any(x in lower for x in ("batal", "cancel")):
            data["action"] = "cancel"
        elif any(x in lower for x in ("carikan", "cari ", "temukan")) and not m:
            data["action"] = "search"
            data["source_type"] = "search"
            query = re.sub(r"\b(carikan|cari|temukan|tolong|semua|download|unduh|ambil|sebagai|format|mp3|mp4|m4a|opus|mkv|webm)\b", " ", lower)
            query = " ".join(query.split()).strip(" ,.-")
            data["search_query"] = query or lower
            data["search_limit"] = 100 if "semua" in lower else 50
            data["download_after_search"] = any(x in lower for x in ("unduh", "download", "ambil semua"))
        elif any(x in lower for x in ("cek", "analisis", "lihat isi", "tampilkan daftar", "berapa video")):
            data["action"] = "analyze"
        elif any(x in lower for x in ("unduh", "download", "ambil semua")):
            data["action"] = "download"
        else:
            data["action"] = "unknown"
        if any(x in lower for x in ("playlist", "daftar putar")):
            data["source_type"] = "playlist"
        elif any(x in lower for x in ("channel", "kanal", "semua video")):
            data["source_type"] = "channel"
        elif any(x in lower for x in ("satu video", "video ini")):
            data["source_type"] = "video"
        for q in ("2160p", "1440p", "1080p", "720p", "480p", "360p"):
            if q in lower:
                data["quality"] = q
                break
        if "kualitas terbaik" in lower or "resolusi terbaik" in lower:
            data["quality"] = "best"
        if any(x in lower for x in ("audio saja", "musik saja", "mp3 saja")):
            data["mode"] = "audio"
        for fmt in ("mp3", "m4a", "opus"):
            if fmt in lower:
                data["mode"] = "audio"
                data["audio_format"] = fmt
                break
        for fmt in ("mp4", "mkv", "webm"):
            if fmt in lower:
                data["mode"] = "video"
                data["video_format"] = fmt
                break
        if any(x in lower for x in ("jangan shorts", "tanpa shorts", "skip shorts")):
            data["include_shorts"] = False
        elif any(x in lower for x in ("sertakan shorts", "ikutkan shorts", "dengan shorts")):
            data["include_shorts"] = True
        if any(x in lower for x in ("jangan live", "tanpa live", "skip live")):
            data["include_live"] = False
        elif any(x in lower for x in ("sertakan live", "ikutkan live", "dengan live")):
            data["include_live"] = True
        neg = any(x in lower for x in ("jangan unduh subtitle", "jangan download subtitle", "tanpa subtitle", "tanpa subtitel", "jangan subtitle"))
        pos = any(x in lower for x in ("subtitle", "subtitel", " srt", "tambahkan sub"))
        if neg:
            data["include_subtitles"] = False
        elif pos:
            data["include_subtitles"] = True
            if "indonesia" in lower or "bahasa id" in lower:
                data["subtitle_languages"] = ["id", "id.*", "en", "en.*"]
        if any(x in lower for x in ("jangan thumbnail", "tanpa thumbnail")):
            data["include_thumbnail"] = False
        elif "thumbnail" in lower:
            data["include_thumbnail"] = True
        if any(x in lower for x in ("jangan download ulang", "jangan unduh ulang", "hindari download ulang")):
            data["use_archive"] = True
        elif any(x in lower for x in ("download ulang", "unduh ulang", "ulang semua")):
            data["use_archive"] = False
        m = re.search(r"(?:paralel|bersamaan)\s*(\d+)", lower)
        if m:
            data["concurrent_downloads"] = max(1, min(10, int(m.group(1))))
        return DownloadIntentPatch.model_validate(data)
