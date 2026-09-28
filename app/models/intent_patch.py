from __future__ import annotations
from app.models.commands import DownloadIntent, DownloadIntentPatch


def apply_intent_patch(base: DownloadIntent, patch: DownloadIntentPatch) -> DownloadIntent:
    data=base.model_dump()
    for name in patch.model_fields_set:
        if name=="explanation": continue
        value=getattr(patch,name)
        if value is not None: data[name]=value
    if patch.explanation: data["explanation"]=patch.explanation
    return DownloadIntent.model_validate(data)
