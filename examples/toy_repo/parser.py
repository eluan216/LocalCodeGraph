def validate(value):
    return bool(value)


def decode_input(value):
    """Decode input after checking its shape."""
    if not validate(value):
        raise ValueError("empty input")
    return value.strip()
