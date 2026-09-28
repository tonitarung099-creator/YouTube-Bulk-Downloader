from __future__ import annotations

import argparse, json, sys
from dotenv import load_dotenv
from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.downloader import YouTubeDownloader


def run_cli(argv:list[str]) -> int:
    parser=argparse.ArgumentParser(description="Pengunduh YouTube Massal")
    parser.add_argument("command", nargs="+", help="Perintah bahasa manusia")
    parser.add_argument("--url", default=None, help="URL aktif dari UI")
    parser.add_argument("--execute", action="store_true", help="Eksekusi setelah preview intent")
    args=parser.parse_args(argv)
    result=GeminiLanguageAgent().interpret(" ".join(args.command), current_url=args.url)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    if not args.execute:return 0
    intent=result.intent; d=YouTubeDownloader()
    if intent.action=="analyze":
        if not intent.url: raise SystemExit("URL belum ada.")
        print(json.dumps(d.analyze(intent.url),ensure_ascii=False,indent=2)); return 0
    if intent.action=="download": return d.download(intent)
    raise SystemExit(f"Aksi '{intent.action}' belum memiliki executor CLI.")


def main() -> None:
    load_dotenv()
    if len(sys.argv)==1:
        from app.gui.bootstrap import run_gui
        raise SystemExit(run_gui())
    raise SystemExit(run_cli(sys.argv[1:]))

if __name__=="__main__": main()
