from pathlib import Path
from pymediainfo import MediaInfo
from ..enums import EntryType

class VideoAdapter:
    extensions = (".mp4", ".mkv", ".avi")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.VIDEO

    def read_metadata(self, path: Path) -> dict[str, object]:
        meta: dict[str, object] = {"file_size": path.stat().st_size if path.exists() else 0}
        #与image适配器相同
        try:
            info = MediaInfo.parse(str(path))#把Path对象转字符串传入
            for track in info.tracks:
                if track.track_type == "Video":
                    meta["duration_ms"] = track.duration
                    meta["width"] = track.width
                    meta["height"] = track.height

                    #视频压缩格式，说明视频是用什么算法压缩的，需要用什么算法把它解压出来播放
                    #beta阶段可能使用，目前无影响
                    meta["codec"] = track.codec_id
                    break
                elif track.track_type == "General" and "format" not in meta:
                    meta["format"] = track.format#容器名称，即文件的格式
        except Exception:
            pass
        return meta

    def supports_preview(self) -> bool:
        return False
