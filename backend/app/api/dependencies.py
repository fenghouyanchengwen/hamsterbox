from collections.abc import Generator
from functools import lru_cache

from app.application.entry_service import EntryService
from app.application.ports import FileTypeDetector
from app.application.rating_service import RatingService
from app.application.resource_service import ResourceService
from app.application.search_service import SearchService
from app.application.tag_service import TagService
from app.db.entry_query_repository import SqliteEntryQueryRepository
from app.db.entry_repository import SqliteEntryRepository
from app.db.entry_tag_repository import SqliteEntryTagRepository
from app.db.resource_repository import SqliteResourceRepository
from app.db.session import get_session
from app.db.tag_category_repository import SqliteTagCategoryRepository
from app.db.tag_repository import SqliteTagRepository


@lru_cache(maxsize=1)
def get_type_detector() -> FileTypeDetector | None:
    """获取文件类型识别注册表；在成员七 PR #53 合入前提供兼容回退注册表。"""
    try:
        from app.adapters.bootstrap import build_registry

        return build_registry()
    except ValueError:
        from app.adapters.builtin.ebook import EbookAdapter
        from app.adapters.builtin.fallback import FallbackAdapter
        from app.adapters.builtin.image import ImageAdapter
        from app.adapters.builtin.video import VideoAdapter
        from app.adapters.enums import EntryType as AdapterEntryType
        from app.adapters.registry import TypeRegistry

        class _GameFallbackAdapter(FallbackAdapter):
            def __init__(self) -> None:
                super().__init__(AdapterEntryType.GAME, extensions=(".exe", ".lnk"))

        class _ModelFallbackAdapter(FallbackAdapter):
            def __init__(self) -> None:
                super().__init__(AdapterEntryType.MODEL, extensions=(".glb", ".gltf", ".obj"))

        class _AudioFallbackAdapter(FallbackAdapter):
            def __init__(self) -> None:
                super().__init__(
                    AdapterEntryType.AUDIO,
                    extensions=(".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"),
                )

        registry = TypeRegistry()
        registry.register(ImageAdapter())
        registry.register(VideoAdapter())
        registry.register(EbookAdapter())
        registry.register(_GameFallbackAdapter())
        registry.register(_ModelFallbackAdapter())
        registry.register(_AudioFallbackAdapter())
        registry.register(FallbackAdapter(AdapterEntryType.OTHER), is_default=True)
        return registry
    except Exception:
        return None


def get_entry_service() -> Generator[EntryService, None, None]:
    session = get_session()

    try:
        yield EntryService(
            repository=SqliteEntryRepository(session),
            resource_repository=SqliteResourceRepository(session),
        )
    finally:
        session.close()


def get_resource_service() -> Generator[ResourceService, None, None]:
    """为每个请求创建资源服务和数据库会话。"""
    session = get_session()

    try:
        yield ResourceService(
            entry_repository=SqliteEntryRepository(session),
            resource_repository=SqliteResourceRepository(session),
            type_detector=get_type_detector(),
        )
    finally:
        session.close()


def get_tag_service() -> Generator[TagService, None, None]:
    session = get_session()
    try:
        yield TagService(
            category_repository=SqliteTagCategoryRepository(session),
            tag_repository=SqliteTagRepository(session),
            entry_tag_repository=SqliteEntryTagRepository(session),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_search_service() -> Generator[SearchService, None, None]:
    session = get_session()
    try:
        yield SearchService(repository=SqliteEntryQueryRepository(session))
    finally:
        session.close()


def get_rating_service() -> Generator[RatingService, None, None]:
    session = get_session()
    try:
        yield RatingService(
            entry_repository=SqliteEntryRepository(session),
            tag_repository=SqliteTagRepository(session),
            entry_tag_repository=SqliteEntryTagRepository(session),
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
