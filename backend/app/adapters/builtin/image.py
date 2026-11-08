from pathlib import Path
from PIL import Image
from ..enums import EntryType

class ImageAdapter:
    extensions = (".png", ".jpg", ".jpeg", ".webp")

    def detect_type(self, path: Path) -> EntryType:
        return EntryType.IMAGE

    def read_metadata(self, path: Path) -> dict[str, object]:
        meta: dict[str, object] = {"file_size": path.stat().st_size if path.exists() else 0}
        #path.exists()：判断文件是否存在；path.stat().st_size：获取文件大小（单位字节）
        #作用：若文件存在取真实大小，不存在取file_size=0。兜底，哪怕图片解析全部失败，前端一定能拿到返回值file_size

        try:
            with Image.open(path) as img:
                meta["width"] = img.width
                meta["height"] = img.height
                meta["format"] = img.format
        except Exception:
            pass
        return meta

    def supports_preview(self) -> bool:
        # Alpha 阶段不实际生成缩略图，但标识图片支持预览（留给 Beta）
        return True
