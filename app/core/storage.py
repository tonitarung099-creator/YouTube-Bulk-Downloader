from __future__ import annotations
import json,os
from pathlib import Path
from typing import Any
from app.core.paths import data_dir

class JsonStorage:
    def __init__(self,path:Path|None=None)->None:self.path=path or data_dir()/"state.json"
    def load(self)->dict[str,Any]:
        try:return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError,json.JSONDecodeError,OSError):return {}
    def save(self,payload:dict[str,Any])->None:
        self.path.parent.mkdir(parents=True,exist_ok=True); tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(tmp,self.path)
