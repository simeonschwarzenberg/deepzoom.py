import os
import sys
from deepzoom import ImageCreator
from deepzoom._defaults import DEFAULT_IMAGE_FORMAT, DEFAULT_RESIZE_FILTER, RESIZE_FILTERS

import optparse

def main():
    parser = optparse.OptionParser(usage="Usage: %prog [options] filename")

    parser.add_option(
        "-d",
        "--destination",
        dest="destination",
        help="Set the destination of the output.",
    )
    parser.add_option(
        "-s",
        "--tile_size",
        dest="tile_size",
        type="int",
        default=254,
        help="Size of the tiles. Default: 254",
    )
    parser.add_option(
        "-f",
        "--tile_format",
        dest="tile_format",
        default=DEFAULT_IMAGE_FORMAT,
        help="Image format of the tiles (jpg or png). Default: jpg",
    )
    parser.add_option(
        "-o",
        "--tile_overlap",
        dest="tile_overlap",
        type="int",
        default=1,
        help="Overlap of the tiles in pixels (0-10). Default: 1",
    )
    parser.add_option(
        "-q",
        "--image_quality",
        dest="image_quality",
        type="float",
        default=0.8,
        help="Quality of the image output (0-1). Default: 0.8",
    )
    parser.add_option(
        "-r",
        "--resize_filter",
        dest="resize_filter",
        default=DEFAULT_RESIZE_FILTER,
        help="Type of filter for resizing (bicubic, nearest, bilinear, antialias (best). Default: antialias",
    )

    (options, args) = parser.parse_args()

    if not args:
        parser.print_help()
        sys.exit(1)

    source = args[0]

    if not options.destination:
        if os.path.exists(source):
            options.destination = os.path.splitext(source)[0] + ".dzi"
        else:
            options.destination = os.path.splitext(os.path.basename(source))[0] + ".dzi"
    if options.resize_filter and options.resize_filter in RESIZE_FILTERS:
        options.resize_filter = RESIZE_FILTERS[options.resize_filter]

    creator = ImageCreator(
        tile_size=options.tile_size,
        tile_format=options.tile_format,
        image_quality=options.image_quality,
        resize_filter=options.resize_filter,
    )
    creator.create(source, options.destination)


if __name__ == "__main__":
    main()