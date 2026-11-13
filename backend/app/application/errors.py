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


class EntryNotFoundError(CodedApplicationError, NotFoundError):
    code = "ENTRY_NOT_FOUND"
    status_code = 404


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


class ResourceNotFoundError(NotFoundError):
    """资源不存在。"""


class ResourceLinkNotFoundError(NotFoundError):
    """资源存在，但没有关联到指定条目。"""


class ResourceAlreadyLinkedError(ConflictError):
    """当前条目已经关联了同一个文件。"""


class ResourceFileMissingError(ConflictError):
    """资源文件不存在。"""


class ResourceAccessDeniedError(ConflictError):
    """资源文件无法访问。"""


class ResourceOpenFailedError(ConflictError):
    """系统默认程序无法打开资源。"""


class ResourceNotFileError(ValidationError):
    """资源路径存在，但不是普通文件。"""


class ResourcePathNotAbsoluteError(ValidationError):
    """资源路径不是绝对路径。"""
