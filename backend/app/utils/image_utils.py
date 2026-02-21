import base64


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode raw image bytes to a base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


def decode_base64_to_bytes(b64_string: str) -> bytes:
    """Decode a base64 string back to raw bytes."""
    return base64.b64decode(b64_string)
