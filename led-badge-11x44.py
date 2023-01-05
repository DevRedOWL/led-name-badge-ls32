#! /usr/bin/python3
# -*- encoding: utf-8 -*-

import sys, os, re, time, argparse
from datetime import datetime
from array import array

try:
    if sys.version_info[0] < 3:
        raise Exception("prefer usb.core with python-2.x because of https://github.com/jnweiger/led-badge-ls32/issues/9")
    import pyhidapi

    pyhidapi.hid_init()
    have_pyhidapi = True
except:
    have_pyhidapi = False
    try:
        import usb.core
    except:
        print("ERROR: Need the pyhidapi or usb.core module.")
        if sys.platform == "darwin":
            print(
                """Please try
  pip3 install pyhidapi
  pip install pyhidapi
  brew install hidapi"""
            )
        elif sys.platform == "linux":
            print(
                """Please try
  sudo pip3 install pyhidapi
  sudo pip install pyhidapi
  sudo apt-get install libhidapi-hidraw0
  sudo ln -s /usr/lib/x86_64-linux-gnu/libhidapi-hidraw.so.0  /usr/local/lib/
or
  sudo apt-get install python3-usb """
            )
        else:  # windows?
            print("""Please with Linux or MacOS or help us implement support for """ + sys.platform)
        sys.exit(1)


__version = "0.12"

from fonts.font_11x44 import (
    font_11x44,
    charmap,
)

char_offset = {}
for i in range(len(charmap)):
    char_offset[charmap[i]] = 11 * i
    # print(i, charmap[i], char_offset[charmap[i]])


bitmap_preloaded = [([], 0)]
bitmaps_preloaded_unused = False

from fonts.bitmap_named import (
    bitmap_named,
)

bitmap_builtin = {}
for i in bitmap_named:
    bitmap_builtin[bitmap_named[i][2]] = bitmap_named[i]


def bitmap_char(ch):
    # Returns a tuple of 11 bytes,
    # ch = '_' returns (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 255)
    # The bits in each byte are horizontal, highest bit is left.
    if ord(ch) < 32:
        if ch in bitmap_builtin:
            return bitmap_builtin[ch][:2]

        global bitmaps_preloaded_unused
        bitmaps_preloaded_unused = False
        return bitmap_preloaded[ord(ch)]

    o = char_offset[ch]
    return (font_11x44[o : o + 11], 1)


def bitmap_text(text):
    # Returns a tuple of (buffer, length_in_byte_columns_aka_chars)
    # We preprocess the text string for substitution patterns
    # "::" is replaced with a single ":"
    # ":1: is replaced with CTRL-A referencing the first preloaded or loaded image.
    # ":happy:" is replaced with a reference to a builtin smiley glyph
    # ":heart:" is replaced with a reference to a builtin heart glyph
    # ":gfx/logo.png:" preloads the file gfx/logo.png and is replaced the corresponding control char.

    def colonrepl(m):
        name = m.group(1)
        if name == "":
            return ":"
        if re.match("^[0-9]*$", name):  # py3 name.isdecimal()
            return chr(int(name))
        if "." in name:
            bitmap_preloaded.append(bitmap_img(name))
            return chr(len(bitmap_preloaded) - 1)
        b = bitmap_named[name]
        return b[2]

    text = re.sub(r":([^:]*):", colonrepl, text)
    buf = array("B")
    cols = 0
    for c in text:
        (b, n) = bitmap_char(c)
        buf.extend(b)
        cols += n
    return (buf, cols)


def bitmap_img(file):
    # Returns a tuple of (buffer, length_in_byte_columns)
    from PIL import Image

    im = Image.open(file)
    print("fetching bitmap from file %s -> (%d x %d)" % (file, im.width, im.height))
    if im.height != 11:
        sys.exit("%s: image height must be 11px. Seen %d" % (file, im.height))
    buf = array("B")
    cols = int((im.width + 7) / 8)
    for col in range(cols):
        for row in range(11):  # [0..10]
            byte_val = 0
            for bit in range(8):  # [0..7]
                bit_val = 0
                x = 8 * col + bit
                if x < im.width and row < im.height:
                    pixel_color = im.getpixel((x, row))
                    if isinstance(
                        pixel_color,
                        tuple,
                    ):
                        monochrome_color = sum(pixel_color[:3]) / len(pixel_color[:3])
                    elif isinstance(pixel_color, int):
                        monochrome_color = pixel_color
                    else:
                        sys.exit(
                            "%s: Unknown pixel format detected (%s)!"
                            % (
                                file,
                                pixel_color,
                            )
                        )
                    if monochrome_color > 127:
                        bit_val = 1 << (7 - bit)
                    byte_val += bit_val
            buf.append(byte_val)
    im.close()
    return (buf, cols)


def bitmap(arg):
    # If arg is a valid and existing path name, we load it as an image.
    # Otherwise we take it as a string.
    if os.path.exists(arg):
        return bitmap_img(arg)
    return bitmap_text(arg)


from proto_header import proto_header


def header(
    lengths,
    speeds,
    modes,
    blink,
    ants,
    brightness=100,
):
    # lengths[0] is the number of chars of the first text
    # Speeds come in as 1..8, but are needed 0..7 here.

    a = [int(x) for x in re.split(r"[\s,]+", ants)]
    a = a + [a[-1]] * (8 - len(a))  # repeat last element

    b = [int(x) for x in re.split(r"[\s,]+", blink)]
    b = b + [b[-1]] * (8 - len(b))  # repeat last element

    s = [int(x) - 1 for x in re.split(r"[\s,]+", speeds)]
    s = s + [s[-1]] * (8 - len(s))  # repeat last element

    m = [int(x) for x in re.split(r"[\s,]+", modes)]
    m = m + [m[-1]] * (8 - len(m))  # repeat last element

    h = list(proto_header)

    if brightness <= 25:
        h[5] = 0x40
    elif brightness <= 50:
        h[5] = 0x20
    elif brightness <= 75:
        h[5] = 0x10

    for i in range(8):
        h[6] += b[i] << i
        h[7] += a[i] << i

    for i in range(8):
        h[8 + i] = 16 * s[i] + m[i]

    for i in range(len(lengths)):
        h[17 + (2 * i) - 1] = lengths[i] // 256
        h[17 + (2 * i)] = lengths[i] % 256

    cdate = datetime.now()
    h[38 + 0] = cdate.year % 100
    h[38 + 1] = cdate.month
    h[38 + 2] = cdate.day
    h[38 + 3] = cdate.hour
    h[38 + 4] = cdate.minute
    h[38 + 5] = cdate.second

    return h


parser = argparse.ArgumentParser(
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description="Upload messages or graphics to a 11x44 led badge via USB HID.\nVersion %s from https://github.com/jnweiger/led-badge-ls32\n -- see there for more examples and for updates." % __version,
    epilog='Example combining image and text:\n sudo %s "I:HEART2:you"' % sys.argv[0],
)
parser.add_argument(
    "-t",
    "--type",
    default="11x44",
    help="Type of display: supported values are 12x48 or (default) 11x44. Rename the program to led-badge-12x48, to switch the default.",
)
parser.add_argument(
    "-s",
    "--speed",
    default="4",
    help="Scroll speed (Range 1..8). Up to 8 comma-separated values",
)
parser.add_argument(
    "-B",
    "--brightness",
    default="100",
    help="Brightness for the display in percent: 25, 50, 75, or 100",
)
parser.add_argument(
    "-m",
    "--mode",
    default="0",
    help="Up to 8 mode values: Scroll-left(0) -right(1) -up(2) -down(3); still-centered(4); animation(5); drop-down(6); curtain(7); laser(8); See '--mode-help' for more details.",
)
parser.add_argument(
    "-b",
    "--blink",
    default="0",
    help="1: blinking, 0: normal. Up to 8 comma-separated values",
)
parser.add_argument(
    "-a",
    "--ants",
    default="0",
    help="1: animated border, 0: normal. Up to 8 comma-separated values",
)
parser.add_argument(
    "-p",
    "--preload",
    metavar="FILE",
    action="append",
    help=argparse.SUPPRESS,
)  # "Load bitmap images. Use ^A, ^B, ^C, ... in text messages to make them visible. Deprecated, embed within ':' instead")
parser.add_argument(
    "-l",
    "--list-names",
    action="version",
    help="list named icons to be embedded in messages and exit",
    version=":" + ":  :".join(bitmap_named.keys()) + ":  ::  or e.g. :path/to/some_icon.png:",
)
parser.add_argument(
    "message",
    metavar="MESSAGE",
    nargs="+",
    help="Up to 8 message texts with embedded builtin icons or loaded images within colons(:) -- See -l for a list of builtins",
)
parser.add_argument(
    "--mode-help",
    action="version",
    help=argparse.SUPPRESS,
    version="""

-m 5 "Animation"

 Animation frames are 6 character (or 48px) wide. Upload an animation of
 N frames as one image N*48 pixels wide, 11 pixels high.
 Frames run from left to right and repeat endless.
 Speeds [1..8] result in ca. [1.2 1.3 2.0 2.4 2.8 4.5 7.5 15] fps.

 Example of a slowly beating heart:
  sudo %s -s1 -m5 "  :heart2:    :HEART2:"

-m 9 "Smooth"
-m 10 "Rotate"

 These modes are mentioned in the BMP Badge software.
 Text is shown static, or sometimes (longer texts?) not shown at all.
 One significant difference is: The text of the first message stays visible after
 upload, even if the USB cable remains connected.
 (No "rotation" or "smoothing"(?) effect can be expected, though)
"""
    % sys.argv[0],
)
args = parser.parse_args()
if have_pyhidapi:
    devinfo = pyhidapi.hid_enumerate(0x0416, 0x5020)
    # dev = pyhidapi.hid_open(0x0416, 0x5020)
else:
    dev = usb.core.find(
        idVendor=0x0416,
        idProduct=0x5020,
    )

if have_pyhidapi:
    if devinfo:
        dev = pyhidapi.hid_open_path(devinfo[0].path)
        print(
            "using [%s %s] int=%d page=%s via pyHIDAPI"
            % (
                devinfo[0].manufacturer_string,
                devinfo[0].product_string,
                devinfo[0].interface_number,
                devinfo[0].usage_page,
            )
        )
    else:
        print("No led tag with vendorID 0x0416 and productID 0x5020 found.")
        print("Connect the led tag and run this tool as root.")
        sys.exit(1)
else:
    if dev is None:
        print("No led tag with vendorID 0x0416 and productID 0x5020 found.")
        print("Connect the led tag and run this tool as root.")
        sys.exit(1)
    try:
        # win32: NotImplementedError: is_kernel_driver_active
        if dev.is_kernel_driver_active(0):
            dev.detach_kernel_driver(0)
    except:
        pass
    dev.set_configuration()
    print(
        "using [%s %s] bus=%d dev=%d"
        % (
            dev.manufacturer,
            dev.product,
            dev.bus,
            dev.address,
        )
    )

if args.preload:
    for file in args.preload:
        bitmap_preloaded.append(bitmap_img(file))
        bitmaps_preloaded_unused = True

msgs = []
for arg in args.message:
    msgs.append(bitmap(arg))

if bitmaps_preloaded_unused == True:
    print("\nWARNING:\n Your preloaded images are not used.\n Try without '-p' or embed the control character '^A' in your message.\n")

if "12" in args.type or "12" in sys.argv[0]:
    print("Type: 12x48")
    for msg in msgs:
        # trivial hack to support 12x48 badges:
        # patch extra empty lines into the message stream.
        for o in reversed(
            range(
                1,
                int(len(msg[0]) / 11) + 1,
            )
        ):
            msg[0][o * 11 : o * 11] = array("B", [0])
else:
    print("Type: 11x44")

buf = array("B")
buf.extend(
    header(
        list(map(lambda x: x[1], msgs)),
        args.speed,
        args.mode,
        args.blink,
        args.ants,
        int(args.brightness),
    )
)

for msg in msgs:
    buf.extend(msg[0])

needpadding = len(buf) % 64
if needpadding:
    buf.extend((0,) * (64 - needpadding))

# print(buf)      # array('B', [119, 97, 110, 103, 0, 0, 0, 0, 48, 48, 48, 48, 48, 48, 48, 48, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 60, 126, 255, 255, 255, 255, 126, 60, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

if len(buf) > 8192:
    print("Writing more than 8192 bytes damages the display!")
    sys.exit(1)

if have_pyhidapi:
    pyhidapi.hid_write(dev, buf)
else:
    for i in range(int(len(buf) / 64)):
        time.sleep(0.1)
        dev.write(1, buf[i * 64 : i * 64 + 64])

if have_pyhidapi:
    pyhidapi.hid_close(dev)
