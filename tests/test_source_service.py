from app.core.source_service import SourceService


class FakeDownloader:
    def analyze(self, url):
        return {
            "id":"channel",
            "title":"Contoh",
            "webpage_url":url,
            "type":"channel",
            "entries":[
                {"id":"known-video","title":"Video","url":"https://youtu.be/a","is_short":False,"is_live":False},
                {"id":"unknown","title":"Belum diklasifikasi","url":"https://youtu.be/b","is_short":None,"is_live":False},
            ],
        }


def test_unknown_short_classification_is_not_labeled_as_video():
    source=SourceService(FakeDownloader()).analyze("https://youtube.com/@contoh")
    assert source.items[0].kind=="Video"
    assert source.items[1].kind=="Belum diketahui"
    assert source.shorts_count is None
