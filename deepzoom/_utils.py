import shutil
from urllib.parse import urlparse
import urllib.request
import io
import os

def get_or_create_path(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def clamp(val, min, max):
    if val < min:
        return min
    elif val > max:
        return max
    return val


def get_files_path(path):
    return os.path.splitext(path)[0] + "_files"


def remove(path):
    os.remove(path)
    tiles_path = get_files_path(path)
    shutil.rmtree(tiles_path)


def safe_open(path):
    # `urllib` in Python 2 supported both local paths as well as URLs. To
    # continue this in Python 3, we manually add `file://` prefix if `path` is
    # not a URL. This change is isolated to this function as we want the output
    # XML to still have the original input paths instead of absolute paths:
    has_scheme = bool(urlparse(path).scheme)
    normalized_path = ("file:%s" % urllib.request.pathname2url(os.path.abspath(path))) if not has_scheme else path
    return io.BytesIO(urllib.request.urlopen(normalized_path).read())