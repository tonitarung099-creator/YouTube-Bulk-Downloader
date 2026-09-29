from __future__ import annotations

import os, re
from typing import Iterable
from google import genai
from google.genai import types
from app.models.commands import AgentResult, DownloadIntent, DownloadIntentPatch
from app.models.intent_patch import apply_intent_patch

SYSTEM_INSTRUCTION="""Kamu adalah parser intent untuk aplikasi Pengunduh YouTube Massal. Keluarkan HANYA patch field DownloadIntentPatch yang benar-benar diminta pengguna; jangan mengisi default untuk field yang tidak disebut. Jangan membuat shell/Python/PowerShell/CMD atau URL palsu. Perintah cek/analisis hanya action=analyze dan tidak boleh mengunduh. Jeda/lanjut/batal memakai action masing-masing. Gunakan Bahasa Indonesia singkat pada explanation. Pahami negasi: 'jangan unduh subtitle' berarti false, 'jangan download ulang' berarti use_archive=true (hindari unduh ulang), sedangkan 'download ulang' berarti use_archive=false. 'tambahkan subtitle Indonesia' hanya mengubah subtitle/language."""

GEMINI_MODELS = (
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash-lite",
)


class GeminiLanguageAgent:
    def __init__(self,api_keys:Iterable[str]|None=None,model:str|None=None)->None:
        requested=(model or os.getenv("GEMINI_MODEL","")).strip()
        if requested in GEMINI_MODELS:
            self.models=(requested,)+tuple(m for m in GEMINI_MODELS if m!=requested)
        else:
            self.models=GEMINI_MODELS
        self.model=self.models[0]
        self.last_model: str|None=None
        self.api_keys=self._load_keys(api_keys)
        self._cursor=0

    @staticmethod
    def _load_keys(api_keys):
        values=list(api_keys) if api_keys is not None else [*os.getenv("GEMINI_API_KEYS","").split(","),os.getenv("GEMINI_API_KEY","")]; clean=[]
        for value in values:
            value=value.strip()
            if value and value not in clean: clean.append(value)
        return clean[:100]

    def interpret(self,text:str,current_url:str|None=None,current_intent:DownloadIntent|None=None)->AgentResult:
        text=text.strip(); base=current_intent.model_copy(deep=True) if current_intent else DownloadIntent()
        if current_url: base.url=current_url
        if not text:
            patch=DownloadIntentPatch(action="unknown",explanation="Perintah kosong."); return AgentResult(intent=apply_intent_patch(base,patch),patch=patch,provider="local_fallback")
        if self.api_keys:
            context=f"\nURL aktif: {current_url}" if current_url and current_url not in text else ""
            for model_name in self.models:
                # Untuk error key/quota, coba seluruh key pada model yang sama dulu.
                # Untuk error model/non-key, langsung turun ke model Flash Lite berikutnya.
                for _ in range(len(self.api_keys)):
                    idx=self._cursor%len(self.api_keys); self._cursor=(self._cursor+1)%len(self.api_keys)
                    try:
                        client=genai.Client(api_key=self.api_keys[idx])
                        response=client.models.generate_content(
                            model=model_name,
                            contents=text+context,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_INSTRUCTION,
                                response_mime_type="application/json",
                                response_schema=DownloadIntentPatch,
                                temperature=0.0,
                            ),
                        )
                        patch=DownloadIntentPatch.model_validate_json(response.text)
                        self.last_model=model_name
                        return AgentResult(intent=apply_intent_patch(base,patch),patch=patch,provider="gemini",key_index=idx)
                    except Exception as exc:
                        if not self._should_rotate(exc):
                            break
        patch=self._local_patch(text,current_url); return AgentResult(intent=apply_intent_patch(base,patch),patch=patch,provider="local_fallback")

    @staticmethod
    def _should_rotate(exc:Exception)->bool:
        msg=str(exc).lower(); return any(x in msg for x in ("429","quota","rate limit","resource_exhausted","401","403","api key"))

    @staticmethod
    def _local_patch(text:str,current_url:str|None=None)->DownloadIntentPatch:
        lower=" ".join(text.lower().split()); data={"explanation":"Perintah dipahami dengan parser lokal."}; m=re.search(r"https?://\S+",text)
        if m:data["url"]=m.group(0).rstrip(".,);]")
        if any(x in lower for x in ("jeda","pause")):data["action"]="pause"
        elif any(x in lower for x in ("lanjut","resume")):data["action"]="resume"
        elif any(x in lower for x in ("batal","cancel")):data["action"]="cancel"
        elif any(x in lower for x in ("cek","analisis","lihat isi","tampilkan daftar","berapa video")):data["action"]="analyze"
        elif any(x in lower for x in ("unduh","download","ambil semua")):data["action"]="download"
        else:data["action"]="unknown"
        if any(x in lower for x in ("playlist","daftar putar")):data["source_type"]="playlist"
        elif any(x in lower for x in ("channel","kanal","semua video")):data["source_type"]="channel"
        elif any(x in lower for x in ("satu video","video ini")):data["source_type"]="video"
        for q in ("2160p","1440p","1080p","720p","480p","360p"):
            if q in lower:data["quality"]=q;break
        if "kualitas terbaik" in lower or "resolusi terbaik" in lower:data["quality"]="best"
        if any(x in lower for x in ("audio saja","musik saja","mp3 saja")):data["mode"]="audio"
        for fmt in ("mp3","m4a","opus"):
            if fmt in lower:data["audio_format"]=fmt;break
        for fmt in ("mp4","mkv","webm"):
            if fmt in lower:data["video_format"]=fmt;break
        if any(x in lower for x in ("jangan shorts","tanpa shorts","skip shorts")):data["include_shorts"]=False
        elif any(x in lower for x in ("sertakan shorts","ikutkan shorts","dengan shorts")):data["include_shorts"]=True
        if any(x in lower for x in ("jangan live","tanpa live","skip live")):data["include_live"]=False
        elif any(x in lower for x in ("sertakan live","ikutkan live","dengan live")):data["include_live"]=True
        neg=any(x in lower for x in ("jangan unduh subtitle","jangan download subtitle","tanpa subtitle","tanpa subtitel","jangan subtitle")); pos=any(x in lower for x in ("subtitle","subtitel"," srt","tambahkan sub"))
        if neg:data["include_subtitles"]=False
        elif pos:
            data["include_subtitles"]=True
            if "indonesia" in lower or "bahasa id" in lower:data["subtitle_languages"]=["id","id.*","en","en.*"]
        if any(x in lower for x in ("jangan thumbnail","tanpa thumbnail")):data["include_thumbnail"]=False
        elif "thumbnail" in lower:data["include_thumbnail"]=True
        if any(x in lower for x in ("jangan download ulang","jangan unduh ulang","hindari download ulang")):data["use_archive"]=True
        elif any(x in lower for x in ("download ulang","unduh ulang","ulang semua")):data["use_archive"]=False
        m=re.search(r"(?:paralel|bersamaan)\s*(\d+)",lower)
        if m:data["concurrent_downloads"]=max(1,min(10,int(m.group(1))))
        return DownloadIntentPatch.model_validate(data)
