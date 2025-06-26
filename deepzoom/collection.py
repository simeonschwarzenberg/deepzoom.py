import math
from collections import deque
import xml.dom.minidom
import os
import warnings

import PIL.Image

from ._utils import (
    get_or_create_path,
    get_files_path,
    remove,
    safe_open,
)
from ._defaults import NS_DEEPZOOM
from ._image_descriptor import DeepZoomImageDescriptor


__all__ = (
    "DeepZoomCollection",
)


class DeepZoomCollection(object):
    def __init__(
        self,
        filename,
        image_quality=0.8,
        max_level=7,
        tile_size=256,
        tile_format="jpg",
        tile_background_color="#000000",
        items=[],
    ):
        self.source = filename
        self.image_quality = image_quality
        self.tile_size = tile_size
        self.max_level = max_level
        self.tile_format = tile_format
        self.tile_background_color = tile_background_color
        self.items = deque(items)
        self.next_item_id = len(self.items)
        # XML
        self.doc = xml.dom.minidom.Document()
        collection = self.doc.createElementNS(NS_DEEPZOOM, "Collection")
        collection.setAttribute("xmlns", NS_DEEPZOOM)
        collection.setAttribute("MaxLevel", str(self.max_level))
        collection.setAttribute("TileSize", str(self.tile_size))
        collection.setAttribute("Format", str(self.tile_format))
        collection.setAttribute("Quality", str(self.image_quality))
        # TODO: Append items passed in as argument
        items = self.doc.createElementNS(NS_DEEPZOOM, "Items")
        collection.appendChild(items)
        collection.setAttribute("NextItemId", str(self.next_item_id))
        self.doc.appendChild(collection)

    @classmethod
    def from_file(self, filename):
        """Open collection descriptor."""
        doc = xml.dom.minidom.parse(safe_open(filename))
        collection = doc.getElementsByTagName("Collection")[0]
        image_quality = float(collection.getAttribute("Quality"))
        max_level = int(collection.getAttribute("MaxLevel"))
        tile_size = int(collection.getAttribute("TileSize"))
        tile_format = collection.getAttribute("Format")
        items = [
            DeepZoomCollectionItem.from_xml(item)
            for item in doc.getElementsByTagName("I")
        ]

        collection = DeepZoomCollection(
            filename,
            image_quality=image_quality,
            max_level=max_level,
            tile_size=tile_size,
            tile_format=tile_format,
            items=items,
        )
        return collection

    @classmethod
    def remove(self, filename):
        """Remove collection file (DZC) and tiles folder."""
        remove(filename)

    def append(self, source):
        descriptor = DeepZoomImageDescriptor()
        descriptor.open(source)
        item = DeepZoomCollectionItem(
            source, descriptor.width, descriptor.height, id=self.next_item_id
        )
        self.items.append(item)
        self.next_item_id += 1

    def save(self, pretty_print_xml=False):
        """Save collection descriptor."""
        collection = self.doc.getElementsByTagName("Collection")[0]
        items = self.doc.getElementsByTagName("Items")[0]
        while len(self.items) > 0:
            item = self.items.popleft()
            i = self.doc.createElementNS(NS_DEEPZOOM, "I")
            i.setAttribute("Id", str(item.id))
            i.setAttribute("N", str(item.id))
            i.setAttribute("Source", item.source)
            # Size
            size = self.doc.createElementNS(NS_DEEPZOOM, "Size")
            size.setAttribute("Width", str(item.width))
            size.setAttribute("Height", str(item.height))
            i.appendChild(size)
            items.appendChild(i)
            self._append_image(item.source, item.id)
        collection.setAttribute("NextItemId", str(self.next_item_id))
        with open(self.source, "wb") as f:
            if pretty_print_xml:
                xml = self.doc.toprettyxml(encoding="UTF-8")
            else:
                xml = self.doc.toxml(encoding="UTF-8")
            f.write(xml)

    def _append_image(self, path, i):
        descriptor = DeepZoomImageDescriptor()
        descriptor.open(path)
        files_path = get_or_create_path(get_files_path(self.source))
        for level in reversed(range(self.max_level + 1)):
            level_path = get_or_create_path("%s/%s" % (files_path, level))
            level_size = 2 ** level
            images_per_tile = int(math.floor(self.tile_size / level_size))
            column, row = self.get_tile_position(i, level, self.tile_size)
            tile_path = "%s/%s_%s.%s" % (level_path, column, row, self.tile_format)
            if not os.path.exists(tile_path):
                tile_image = PIL.Image.new(
                    "RGB", (self.tile_size, self.tile_size), self.tile_background_color
                )
                if self.tile_format == "jpg":
                    jpeg_quality = int(self.image_quality * 100)
                    tile_image.save(tile_path, "JPEG", quality=jpeg_quality)
                else:
                    tile_image.save(tile_path)
            tile_image = PIL.Image.open(tile_path)
            source_path = "%s/%s/%s_%s.%s" % (
                get_files_path(path),
                level,
                0,
                0,
                descriptor.tile_format,
            )
            # Local
            if os.path.exists(source_path):
                try:
                    source_image = PIL.Image.open(safe_open(source_path))
                except IOError:
                    warnings.warn("Skipped invalid level: %s" % source_path)
                    continue
            # Remote
            else:
                if level == self.max_level:
                    try:
                        source_image = PIL.Image.open(safe_open(source_path))
                    except IOError:
                        warnings.warn("Skipped invalid image: %s" % source_path)
                        return
                    # Expected width & height of the tile
                    e_w, e_h = descriptor.get_dimensions(level)
                    # Actual width & height of the tile
                    w, h = source_image.size
                    # Correct tile because of IIP bug where low-level tiles have
                    # wrong dimensions (they are too large)
                    if w != e_w or h != e_h:
                        # Resize incorrect tile to correct size
                        source_image = source_image.resize(
                            (e_w, e_h), PIL.Image.Resampling.LANCZOS
                        )
                        # Store new dimensions
                        w, h = e_w, e_h
                else:
                    w = int(math.ceil(w * 0.5))
                    h = int(math.ceil(h * 0.5))
                    source_image.thumbnail((w, h), PIL.Image.Resampling.LANCZOS)
            column, row = self.get_position(i)
            x = (column % images_per_tile) * level_size
            y = (row % images_per_tile) * level_size
            tile_image.paste(source_image, (x, y))
            tile_image.save(tile_path)

    def get_position(self, z_order):
        """Returns position (column, row) from given Z-order (Morton number.)"""
        column = 0
        row = 0
        for i in range(0, 32, 2):
            offset = i // 2
            # column
            column_offset = i
            column_mask = 1 << column_offset
            column_value = (z_order & column_mask) >> column_offset
            column |= column_value << offset
            # row
            row_offset = i + 1
            row_mask = 1 << row_offset
            row_value = (z_order & row_mask) >> row_offset
            row |= row_value << offset
        return int(column), int(row)

    def get_z_order(self, column, row):
        """Returns the Z-order (Morton number) from given position."""
        z_order = 0
        for i in range(32):
            z_order |= (column & 1 << i) << i | (row & 1 << i) << (i + 1)
        return z_order

    def get_tile_position(self, z_order, level, tile_size):
        level_size = 2 ** level
        x, y = self.get_position(z_order)
        return (
            int(math.floor((x * level_size) / tile_size)),
            int(math.floor((y * level_size) / tile_size)),
        )


class DeepZoomCollectionItem(object):
    def __init__(self, source, width, height, id=0):
        self.id = id
        self.source = source
        self.width = width
        self.height = height

    @classmethod
    def from_xml(cls, xml):
        id = int(xml.getAttribute("Id"))
        source = xml.getAttribute("Source")
        size = xml.getElementsByTagName("Size")[0]
        width = int(size.getAttribute("Width"))
        height = int(size.getAttribute("Height"))
        return DeepZoomCollectionItem(source, width, height, id)