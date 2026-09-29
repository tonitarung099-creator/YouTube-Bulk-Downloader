from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from app.core.paths import data_dir


class GeminiKeyStore:
    """Simpan API key secara lokal di folder data portable.

    File ini tidak pernah dibundel ke ZIP rilis karena folder data/ diabaikan Git.
    Isi key tidak pernah ditulis ke log aplikasi.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "gemini-api-keys.json"

    @staticmethod
    def normalize(values: Iterable[str] | str | None) -> list[str]:
        if values is None:
            return []
        if isinstance(values, str):
            raw = values.replace(";", "\n").replace(",", "\n").splitlines()
        else:
            raw = list(values)
        clean: list[str] = []
        for value in raw:
            key = str(value).strip()
            if key and key not in clean:
                clean.append(key)
        return clean[:100]

    def load(self) -> list[str]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []
        return self.normalize(payload.get("keys", []))

    def save(self, keys: Iterable[str] | str) -> list[str]:
        clean = self.normalize(keys)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"version": 1, "keys": clean}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return clean

    def clear(self) -> None:
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
