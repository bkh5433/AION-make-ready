from enum import Enum


class PropertyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
