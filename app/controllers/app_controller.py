from __future__ import annotations
import concurrent.futures,os
from pathlib import Path
from PySide6.QtCore import QObject,Signal
from app.ai.gemini_agent import GeminiLanguageAgent
from app.core.paths import default_download_dir
from app.core.queue_manager import QueueManager
from app.core.source_service import SourceService
from app.core.storage import JsonStorage
from app.models.commands import DownloadIntent
from app.models.state import AppState,DownloadJob

class AppController(QObject):
    state_changed=Signal(object);source_loaded=Signal(object);analysis_failed=Signal(str);job_changed=Signal(object);ai_reply=Signal(str,object);ai_status=Signal(str)
    def __init__(self)->None:
        super().__init__();self.storage=JsonStorage();saved=self.storage.load();self.state=AppState()
        if saved.get("intent"):
            try:self.state.intent=DownloadIntent.model_validate(saved["intent"])
            except Exception:pass
        if not self.state.intent.output_folder:self.state.intent.output_folder=str(default_download_dir())
        self.source_service=SourceService();self._pool=concurrent.futures.ThreadPoolExecutor(max_workers=4,thread_name_prefix="ui-work");self._analysis_seq=0;self.queue=QueueManager(self.state.intent.concurrent_downloads,self._on_job);self.agent=GeminiLanguageAgent(model=saved.get("gemini_model") or None)
    def persist(self)->None:self.storage.save({"intent":self.state.intent.model_dump(mode="json"),"gemini_model":self.agent.model})
    def update_intent(self,**changes)->None:self.state.intent=self.state.intent.model_copy(update=changes);self.persist();self.state_changed.emit(self.state)
    def analyze(self,url:str)->None:
        self._analysis_seq+=1;seq=self._analysis_seq;self.state.active_url=url.strip();self.state_changed.emit(self.state);f=self._pool.submit(self.source_service.analyze,self.state.active_url);f.add_done_callback(lambda x:self._finish_analysis(seq,x))
    def _finish_analysis(self,seq,f)->None:
        if seq!=self._analysis_seq:return
        try:source=f.result()
        except Exception as exc:self.analysis_failed.emit(str(exc));return
        self.state.source=source;self.state.selected_ids={i.id for i in source.items};self.source_loaded.emit(source);self.state_changed.emit(self.state)
    def queue_selected(self,all_items:bool=False)->int:
        if not self.state.source:return 0
        items=self.state.source.items if all_items else [i for i in self.state.source.items if i.id in self.state.selected_ids]
        eligible=[i for i in items if (self.state.intent.include_shorts or i.is_short is not True) and (self.state.intent.include_live or not i.is_live)]
        for item in eligible:self.queue.add(item,self.state.intent)
        return len(eligible)
    def pause(self)->None:self.queue.pause()
    def resume(self)->None:self.queue.resume()
    def cancel(self)->None:self.queue.cancel()
    def _on_job(self,job:DownloadJob)->None:
        by_id={j.job_id:j for j in self.state.jobs};by_id[job.job_id]=job;self.state.jobs=list(by_id.values());self.job_changed.emit(job);self.state_changed.emit(self.state)
    def interpret_ai(self,text:str)->None:
        self.ai_status.emit("Menghubungkan" if self.agent.api_keys else "Mode lokal");f=self._pool.submit(self.agent.interpret,text,self.state.active_url,self.state.intent);f.add_done_callback(self._finish_ai)
    def _finish_ai(self,f)->None:
        try:result=f.result()
        except Exception as exc:self.ai_status.emit("Gangguan");self.ai_reply.emit(f"Gagal memahami perintah: {exc}",None);return
        self.state.intent=result.intent
        if result.intent.url:self.state.active_url=result.intent.url
        self.persist();self.ai_status.emit("Online" if result.provider=="gemini" else "Mode lokal")
        fields=sorted(result.patch.model_fields_set) if result.patch else [];summary=result.intent.explanation or "Perintah dipahami."
        if fields:summary+="\nPerubahan: "+", ".join(x for x in fields if x!="explanation")
        self.ai_reply.emit(summary,result);self.state_changed.emit(self.state)
        if result.intent.action=="analyze" and result.intent.url:self.analyze(result.intent.url)
        elif result.intent.action=="pause":self.pause()
        elif result.intent.action=="resume":self.resume()
        elif result.intent.action=="cancel":self.cancel()
    def disk_stats(self)->tuple[int,int,int]:
        folder=Path(self.state.intent.output_folder or default_download_dir())
        import shutil
        u=shutil.disk_usage(folder);used=u.total-u.free;percent=round(used*100/u.total) if u.total else 0;return used,u.total,percent
