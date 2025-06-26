import os
import PIL.Image

from ._utils import (
    get_or_create_path,
    get_files_path,
    clamp,
    safe_open,
)
from ._defaults import IMAGE_FORMATS, DEFAULT_IMAGE_FORMAT, RESIZE_FILTERS
from ._image_descriptor import DeepZoomImageDescriptor
from .collection import DeepZoomCollection


__all__ = (
    "ImageCreator",
    "CollectionCreator"
)


class ImageCreator(object):
    """Creates Deep Zoom images."""

    def __init__(
        self,
        tile_size=254,
        tile_overlap=1,
        tile_format="jpg",
        image_quality=0.8,
        resize_filter=None,
        copy_metadata=False,
    ):
        self.tile_size = int(tile_size)
        self.tile_format = tile_format
        self.tile_overlap = clamp(int(tile_overlap), 0, 10)
        self.image_quality = clamp(image_quality, 0, 1.0)
        if not tile_format in IMAGE_FORMATS:
            self.tile_format = DEFAULT_IMAGE_FORMAT
        self.resize_filter = resize_filter
        self.copy_metadata = copy_metadata

    def get_image(self, level):
        """Returns the bitmap image at the given level."""
        assert (
            0 <= level and level < self.descriptor.num_levels
        ), "Invalid pyramid level"
        width, height = self.descriptor.get_dimensions(level)
        # don't transform to what we already have
        if self.descriptor.width == width and self.descriptor.height == height:
            return self.image
        if (self.resize_filter is None) or (self.resize_filter not in RESIZE_FILTERS):
            return self.image.resize((width, height), PIL.Image.Resampling.LANCZOS)
        return self.image.resize((width, height), RESIZE_FILTERS[self.resize_filter])

    def tiles(self, level):
        """Iterator for all tiles in the given level. Returns (column, row) of a tile."""
        columns, rows = self.descriptor.get_num_tiles(level)
        for column in range(columns):
            for row in range(rows):
                yield (column, row)

    def create(self, source, destination):
        """Creates Deep Zoom image from source file and saves it to destination."""
        if isinstance(source, PIL.Image.Image):
            self.image = source
        else:
            self.image = PIL.Image.open(safe_open(source))
        width, height = self.image.size
        self.descriptor = DeepZoomImageDescriptor(
            width=width,
            height=height,
            tile_size=self.tile_size,
            tile_overlap=self.tile_overlap,
            tile_format=self.tile_format,
        )
        # Create tiles
        image_files = get_or_create_path(get_files_path(destination))
        for level in range(self.descriptor.num_levels):
            level_dir = get_or_create_path(os.path.join(image_files, str(level)))
            level_image = self.get_image(level)
            for (column, row) in self.tiles(level):
                bounds = self.descriptor.get_tile_bounds(level, column, row)
                tile = level_image.crop(bounds)
                format = self.descriptor.tile_format
                tile_path = os.path.join(level_dir, "%s_%s.%s" % (column, row, format))
                if self.descriptor.tile_format == "jpg":
                    jpeg_quality = int(self.image_quality * 100)
                    tile.save(tile_path, "JPEG", quality=jpeg_quality)
                else:
                    tile.save(tile_path)
        # Create descriptor
        self.descriptor.save(destination)


class CollectionCreator(object):
    """Creates Deep Zoom collections."""

    def __init__(
        self,
        image_quality=0.8,
        tile_size=256,
        max_level=7,
        tile_format="jpg",
        copy_metadata=False,
        tile_background_color="#000000",
    ):
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.tile_background_color = tile_background_color
        # TODO
        self.copy_metadata = copy_metadata

    def create(self, images, destination):
        """Creates a Deep Zoom collection from a list of images."""
        collection = DeepZoomCollection(
            destination,
            image_quality=self.image_quality,
            max_level=self.max_level,
            tile_size=self.tile_size,
            tile_format=self.tile_format,
            tile_background_color=self.tile_background_color,
        )
        for image in images:
            collection.append(image)
        collection.save()