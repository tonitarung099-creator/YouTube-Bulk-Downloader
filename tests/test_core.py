import importlib.util,sys,types,time

if importlib.util.find_spec("google.genai") is None:
    google=types.ModuleType("google");genai=types.ModuleType("google.genai");genai.types=types.SimpleNamespace();google.genai=genai;sys.modules["google"]=google;sys.modules["google.genai"]=genai
if importlib.util.find_spec("yt_dlp") is None:sys.modules["yt_dlp"]=types.SimpleNamespace(YoutubeDL=object)

from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.downloader import YouTubeDownloader
from app.core import queue_manager as qm
from app.models.commands import DownloadIntent,DownloadIntentPatch
from app.models.intent_patch import apply_intent_patch
from app.models.state import VideoItem,JobStatus

def merge(text,base=None):return apply_intent_patch(base or DownloadIntent(),GeminiLanguageAgent._local_patch(text))

def test_patch_preserves_prior_settings():
    out=merge("tambahkan subtitle Indonesia",DownloadIntent(quality="1080p",include_shorts=False,include_subtitles=False));assert out.quality=="1080p" and out.include_shorts is False and out.include_subtitles

def test_negation_archive():assert merge("jangan download ulang").use_archive is True and merge("download ulang semua").use_archive is False

def test_negation_subtitle():assert merge("jangan unduh subtitle").include_subtitles is False and merge("tambahkan subtitle Indonesia").include_subtitles is True

def test_check_is_analyze_not_download():assert merge("cek dulu berapa video").action=="analyze"

def test_quality_is_strict_maximum():
    fmt=YouTubeDownloader._video_format("1080p");assert "height<=1080" in fmt and fmt.endswith("best[height<=1080]")

def test_video_parallel_not_fragment_parallel():
    opts=YouTubeDownloader().build_options(DownloadIntent(concurrent_downloads=9,fragment_downloads=3));assert opts["concurrent_fragment_downloads"]==3

def test_duplicate_is_skipped(monkeypatch):
    def slow(self,intent,progress_cb=None,pause_event=None,cancel_event=None):time.sleep(.15);return 0
    monkeypatch.setattr(qm.YouTubeDownloader,"download",slow);q=qm.QueueManager(max_workers=1);v=VideoItem(id="abc",title="A",url="https://youtu.be/abc");q.add(v,DownloadIntent(quality="1080p"));b=q.add(v,DownloadIntent(quality="1080p"));assert b.status==JobStatus.SKIPPED

def test_portable_tools_are_wired_into_ytdlp(monkeypatch,tmp_path):
    tools=tmp_path/"tools";tools.mkdir();ffmpeg=tools/"ffmpeg.exe";deno=tools/"deno.exe";ffmpeg.write_bytes(b"");deno.write_bytes(b"")
    monkeypatch.setattr("app.core.downloader.bundled_tool_path",lambda name:{"ffmpeg":ffmpeg,"deno":deno}.get(name))
    opts=YouTubeDownloader._portable_tool_options();assert opts["ffmpeg_location"]==str(tools);assert opts["js_runtimes"]["deno"]["path"]==str(deno)
