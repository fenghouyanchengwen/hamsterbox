import zipfile
import tarfile
from pathlib import Path
from app.adapters.enums import EntryType
##

class ArchiveAdapter:
    """
    压缩包适配器：用于识别常见压缩包格式，并尝试提取基础元数据。
    """
    # 声明插件支持的扩展名
    extensions = (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz")

    def detect_type(self, path: Path) -> EntryType:
        """
        识别类型。由于数据库约束中没有“压缩包”这一分类，统一映射为 OTHER。
        """
        return EntryType.OTHER

    def read_metadata(self, path: Path) -> dict[str, object]:
        """
        读取压缩包元数据：获取文件大小，并尝试统计内部文件数量。
        """
        meta: dict[str, object] = {
            "file_size": path.stat().st_size if path.exists() else 0,
            "is_archive": True
        }

        suffix = path.suffix.lower()

        try:
            # 使用标准库解析 ZIP (不需要第三方依赖)
            if suffix == ".zip":
                with zipfile.ZipFile(path, 'r') as z:
                    meta["file_count"] = len(z.namelist())
                    meta["archive_format"] = "ZIP"

            # 使用标准库解析 TAR/GZ
            elif suffix in (".tar", ".gz", ".bz2", ".xz"):
                with tarfile.open(path, 'r:*') as t:
                    meta["file_count"] = len(t.getnames())
                    meta["archive_format"] = "TAR"

            # RAR 和 7Z 需要第三方库，Alpha 阶段仅提供基础信息
            elif suffix in (".rar", ".7z"):
                meta["archive_format"] = suffix.upper().lstrip(".")
                meta["note"] = "需要外部工具支持才能统计文件数量"

        except Exception:
            # 极度重要：插件内部的解析错误绝对不能向上抛给主程序！
            # 如果压缩包损坏，直接吞掉异常，返回基础的 file_size 即可
            meta["parse_status"] = "failed"

        return meta

    def supports_preview(self) -> bool:
        """压缩包不支持内嵌预览"""
        return False
