def braille_to_dot_matrix(braille_char: str) -> list[list[int]]:
    """
    Convert a single braille Unicode character to a 2×4 dot matrix.
    Returns [[dot1,dot4], [dot2,dot5], [dot3,dot6], [dot7,dot8]].
    Standard Grade 1 cells only use the first three rows (dots 1–6).
    """
    _empty = [[0, 0], [0, 0], [0, 0], [0, 0]]
    if not braille_char:
        return _empty
    cp = ord(braille_char[0])
    if not (0x2800 <= cp <= 0x28FF):
        return _empty
    offset = cp - 0x2800
    bits = [(offset >> i) & 1 for i in range(8)]
    return [
        [bits[0], bits[3]],
        [bits[1], bits[4]],
        [bits[2], bits[5]],
        [bits[6], bits[7]],
    ]
