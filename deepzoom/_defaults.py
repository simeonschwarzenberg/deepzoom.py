import PIL.Image

NS_DEEPZOOM = "http://schemas.microsoft.com/deepzoom/2008"

DEFAULT_RESIZE_FILTER = PIL.Image.Resampling.LANCZOS
DEFAULT_IMAGE_FORMAT = "jpg"

RESIZE_FILTERS = {
    "cubic": PIL.Image.Resampling.BICUBIC,
    "bilinear": PIL.Image.Resampling.BILINEAR,
    "bicubic": PIL.Image.Resampling.BICUBIC,
    "nearest": PIL.Image.Resampling.NEAREST,
    "antialias": PIL.Image.Resampling.LANCZOS,
}

IMAGE_FORMATS = {
    "jpg": "jpg",
    "png": "png",
}