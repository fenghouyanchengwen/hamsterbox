from enum import Enum

class EntryType(str, Enum):
    BOOK = "book"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    GAME = "game"
    MODEL = "model"
    OTHER = "other"
