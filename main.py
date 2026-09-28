from __future__ import annotations

import argparse
import json

from dotenv import load_dotenv

from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.downloader import YouTubeDownloader


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="YouTube Bulk Downloader - AI command prototype")
    parser.add_argument("command", nargs="+", help="Perintah bahasa manusia")
    parser.add_argument("--url", help="URL aktif dari UI", default=None)
    parser.add_argument("--execute", action="store_true", help="Eksekusi setelah intent dipahami")
    args = parser.parse_args()

    text = " ".join(args.command)
    agent = GeminiLanguageAgent()
    result = agent.interpret(text, current_url=args.url)

    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))

    if not args.execute:
        return

    downloader = YouTubeDownloader()
    intent = result.intent
    if intent.action == "analyze":
        if not intent.url:
            raise SystemExit("URL belum ada.")
        print(json.dumps(downloader.analyze(intent.url), ensure_ascii=False, indent=2))
    elif intent.action == "download":
        raise SystemExit(downloader.download(intent))
    else:
        raise SystemExit(f"Aksi '{intent.action}' belum memiliki executor.")


if __name__ == "__main__":
    main()
