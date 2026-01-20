from hashlib import md5
from typing import (
    Any,
    Protocol,
    Callable,
    TYPE_CHECKING,
    List,
    Optional,
    Iterable,
    Sequence,
    Collection,
)

def compute_args_hash(*args: Any) -> str:
    """Compute a hash for the given arguments with safe Unicode handling.

    Args:
        *args: Arguments to hash
    Returns:
        str: Hash string
    """
    # Convert all arguments to strings and join them
    args_str = "".join([str(arg) for arg in args])

    # Use 'replace' error handling to safely encode problematic Unicode characters
    # This replaces invalid characters with Unicode replacement character (U+FFFD)
    try:
        return md5(args_str.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        # Handle surrogate characters and other encoding issues
        safe_bytes = args_str.encode("utf-8", errors="replace")
        return md5(safe_bytes).hexdigest()


def compute_mdhash_id(content: str, prefix: str = "") -> str:
    """
    Compute a unique ID for a given content string.

    The ID is a combination of the given prefix and the MD5 hash of the content string.
    """
    return prefix + compute_args_hash(content)