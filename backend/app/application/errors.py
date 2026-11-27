class ApplicationError(Exception):
    """所有应用层业务异常的基类。"""


class NotFoundError(ApplicationError):
    """请求的对象不存在。"""


class ConflictError(ApplicationError):
    """当前操作与已有数据冲突。"""


class InvalidStateError(ApplicationError):
    """对象当前状态不允许执行该操作。"""


class ValidationError(ApplicationError):
    """业务字段或输入不符合要求。"""


class CodedApplicationError(ApplicationError):
    """带稳定 API 错误码的应用异常。"""

    code = "APPLICATION_ERROR"
    status_code = 400

    def __init__(
        self,
        message: str = "",
        *,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.details: dict[str, object] = details or {}


class EntryNotFoundError(CodedApplicationError, NotFoundError):
    code = "ENTRY_NOT_FOUND"
    status_code = 404


class EntryReviewTooLongError(CodedApplicationError, ValidationError):
    code = "ENTRY_REVIEW_TOO_LONG"
    status_code = 422


class InvalidEntryLifecycleError(CodedApplicationError, InvalidStateError):
    code = "ENTRY_LIFECYCLE_INVALID"
    status_code = 400


class RatingRangeInvalidError(CodedApplicationError, ValidationError):
    code = "RATING_RANGE_INVALID"
    status_code = 422


class TagCategoryNotFoundError(CodedApplicationError, NotFoundError):
    code = "TAG_CATEGORY_NOT_FOUND"
    status_code = 404


class TagNotFoundError(CodedApplicationError, NotFoundError):
    code = "TAG_NOT_FOUND"
    status_code = 404


class EntryTagNotFoundError(CodedApplicationError, NotFoundError):
    code = "ENTRY_TAG_NOT_FOUND"
    status_code = 404


class TagCategoryNameDuplicatedError(CodedApplicationError, ConflictError):
    code = "TAG_CATEGORY_NAME_DUPLICATED"
    status_code = 409


class TagNameDuplicatedError(CodedApplicationError, ConflictError):
    code = "TAG_NAME_DUPLICATED"
    status_code = 409


class TagInUseError(CodedApplicationError, ConflictError):
    code = "TAG_IN_USE"
    status_code = 409


class TagCategoryNotEmptyError(CodedApplicationError, ConflictError):
    code = "TAG_CATEGORY_NOT_EMPTY"
    status_code = 409


class SystemCategoryProtectedError(CodedApplicationError, ConflictError):
    code = "SYSTEM_CATEGORY_PROTECTED"
    status_code = 409


class ResourceNotFoundError(CodedApplicationError, NotFoundError):
    """资源不存在。"""

    code = "RESOURCE_NOT_FOUND"
    status_code = 404


class ResourceLinkNotFoundError(CodedApplicationError, NotFoundError):
    """资源存在，但没有关联到指定条目。"""

    code = "RESOURCE_LINK_NOT_FOUND"
    status_code = 404


class ResourceAlreadyLinkedError(CodedApplicationError, ConflictError):
    """当前条目已经关联了同一个文件。"""

    code = "RESOURCE_ALREADY_LINKED"
    status_code = 409


class ResourceFileMissingError(CodedApplicationError, ConflictError):
    """资源文件不存在。"""

    code = "RESOURCE_FILE_MISSING"
    status_code = 409


class ResourceAccessDeniedError(CodedApplicationError, ConflictError):
    """资源文件无法访问。"""

    code = "RESOURCE_ACCESS_DENIED"
    status_code = 409


class ResourceOpenFailedError(CodedApplicationError, ConflictError):
    """系统默认程序无法打开资源。"""

    code = "RESOURCE_OPEN_FAILED"
    status_code = 409


class ResourceNotFileError(CodedApplicationError, ValidationError):
    """资源路径存在，但不是普通文件。"""

    code = "RESOURCE_NOT_FILE"
    status_code = 422


class ResourcePathNotAbsoluteError(CodedApplicationError, ValidationError):
    """资源路径不是绝对路径。"""

    code = "RESOURCE_PATH_NOT_ABSOLUTE"
    status_code = 422


class ResourceDeleteConfirmRequiredError(CodedApplicationError, InvalidStateError):
    """删除磁盘文件到回收站前必须经过显式二次确认。"""

    code = "RESOURCE_DELETE_CONFIRM_REQUIRED"
    status_code = 400


class ResourceSharedConfirmRequiredError(CodedApplicationError, ConflictError):
    """删除被多个条目共享引用的物理文件前必须显式确认共享影响。"""

    code = "RESOURCE_SHARED_CONFIRM_REQUIRED"
    status_code = 409


class ResourceRecycleFailedError(CodedApplicationError, ConflictError):
    """将资源移入系统回收站失败。"""

    code = "RESOURCE_RECYCLE_FAILED"
    status_code = 409
