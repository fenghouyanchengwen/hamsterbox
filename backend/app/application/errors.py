class ApplicationError(Exception):
    """所有应用层业务异常的基类。"""


class NotFoundError(ApplicationError):
    """请求的对象不存在。"""


class ConflictError(ApplicationError):
    """当前操作与已有数据冲突。"""


class InvalidStateError(ApplicationError):
    """对象当前状态不允许执行该操作。"""