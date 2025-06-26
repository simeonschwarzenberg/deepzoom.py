import math
import xml.dom.minidom

from ._utils import safe_open, remove
from ._defaults import NS_DEEPZOOM

class DeepZoomImageDescriptor(object):
    def __init__(
        self, width=None, height=None, tile_size=254, tile_overlap=1, tile_format="jpg"
    ):
        self.width = width
        self.height = height
        self.tile_size = tile_size
        self.tile_overlap = tile_overlap
        self.tile_format = tile_format
        self._num_levels = None

    def open(self, source):
        """Intialize descriptor from an existing descriptor file."""
        doc = xml.dom.minidom.parse(safe_open(source))
        image = doc.getElementsByTagName("Image")[0]
        size = doc.getElementsByTagName("Size")[0]
        self.width = int(size.getAttribute("Width"))
        self.height = int(size.getAttribute("Height"))
        self.tile_size = int(image.getAttribute("TileSize"))
        self.tile_overlap = int(image.getAttribute("Overlap"))
        self.tile_format = image.getAttribute("Format")

    def save(self, destination):
        """Save descriptor file."""
        file = open(destination, "wb")
        doc = xml.dom.minidom.Document()
        image = doc.createElementNS(NS_DEEPZOOM, "Image")
        image.setAttribute("xmlns", NS_DEEPZOOM)
        image.setAttribute("TileSize", str(self.tile_size))
        image.setAttribute("Overlap", str(self.tile_overlap))
        image.setAttribute("Format", str(self.tile_format))
        size = doc.createElementNS(NS_DEEPZOOM, "Size")
        size.setAttribute("Width", str(self.width))
        size.setAttribute("Height", str(self.height))
        image.appendChild(size)
        doc.appendChild(image)
        descriptor = doc.toxml(encoding="UTF-8")
        file.write(descriptor)
        file.close()

    @classmethod
    def remove(self, filename):
        """Remove descriptor file (DZI) and tiles folder."""
        remove(filename)

    @property
    def num_levels(self):
        """Number of levels in the pyramid."""
        if self._num_levels is None:
            max_dimension = max(self.width, self.height)
            self._num_levels = int(math.ceil(math.log(max_dimension, 2))) + 1
        return self._num_levels

    def get_scale(self, level):
        """Scale of a pyramid level."""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        max_level = self.num_levels - 1
        return math.pow(0.5, max_level - level)

    def get_dimensions(self, level):
        """Dimensions of level (width, height)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        scale = self.get_scale(level)
        width = int(math.ceil(self.width * scale))
        height = int(math.ceil(self.height * scale))
        return (width, height)

    def get_num_tiles(self, level):
        """Number of tiles (columns, rows)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        w, h = self.get_dimensions(level)
        return (
            int(math.ceil(float(w) / self.tile_size)),
            int(math.ceil(float(h) / self.tile_size)),
        )

    def get_tile_bounds(self, level, column, row):
        """Bounding box of the tile (x1, y1, x2, y2)"""
        assert 0 <= level and level < self.num_levels, "Invalid pyramid level"
        offset_x = 0 if column == 0 else self.tile_overlap
        offset_y = 0 if row == 0 else self.tile_overlap
        x = (column * self.tile_size) - offset_x
        y = (row * self.tile_size) - offset_y
        level_width, level_height = self.get_dimensions(level)
        w = self.tile_size + (1 if column == 0 else 2) * self.tile_overlap
        h = self.tile_size + (1 if row == 0 else 2) * self.tile_overlap
        w = min(w, level_width - x)
        h = min(h, level_height - y)
        return (x, y, x + w, y + h)