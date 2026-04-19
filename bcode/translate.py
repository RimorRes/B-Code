def test_print():
    for i in range(256):
        # Create raw Unicode escape string and decode it
        s = rf'\u28{i:02x}'
        print(s.encode('utf-8').decode('unicode-escape'))


class