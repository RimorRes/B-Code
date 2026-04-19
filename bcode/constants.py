import enum

PAGE_FORMATS = {
    "A4":     {"width": 210, "height": 297},
    "Letter": {"width": 215.9, "height": 279.4},
    "Legal":  {"width": 215.9, "height": 355.6}
}

# G-CODE commads
class GCode(enum.Enum):
    PUNCH_UP = "M42 P8 S128"
    PUNCH_DOWN = "M42 P8 S0"
