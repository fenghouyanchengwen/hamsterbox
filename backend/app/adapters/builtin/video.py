from pathlib import Path
from ..enums import EntryType

class VideoAdapter:
    extensions = (".mp4", ".mkv", ".avi")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.VIDEO

    def read_metadata(self, path: Path) -> dict[str, object]:
        meta: dict[str, object] = {"file_size": path.stat().st_size if path.exists() else 0}
        try:
            info = MediaInfo.parse(str(path))
            for track in info.tracks:
                if track.track_type == "Video":
                    meta["duration_ms"] = track.duration
                    meta["width"] = track.width
                    meta["height"] = track.height
                    meta["codec"] = track.codec_id
                    break
                if track.track_type == "General" and "container" not in meta:
                    meta["container"] = track.format
        except Exception:
            pass
        return meta

    def supports_preview(self) -> bool:
        return False
