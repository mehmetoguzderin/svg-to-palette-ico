import re
import cairosvg
import requests
from PIL import Image
from xml.etree import ElementTree as ET
import argparse


def download_svg_from_url(url, save_path):
    response = requests.get(url)
    with open(save_path, "wb") as file:
        file.write(response.content)
    return save_path


def hex_to_rgb(value):
    value = value.lstrip("#")
    result = [0, 0, 0, 255]
    length = len(value)
    for index, i in enumerate(range(0, length, length // 3)):
        result[index] = int(value[i : i + length // 3], 16)
    return tuple(result)


def next_power_of_two(n):
    # Find the next power of two
    p = 1
    while p < n:
        p <<= 1
    return p


def get_next_power_of_two(n):
    # Find the next power of two
    p = next_power_of_two(n)
    # Get the next power of two
    return p << 1


# Generate number of palette colors by finding colors in SVG, adding empty transparent, and getting next power of two
def extract_colors_from_svg(svg_file):
    with open(svg_file, "r") as file:
        content = file.read()
    colors = re.findall(r"#[0-9a-fA-F]{6}", content)
    unique_colors = list(set(colors))
    unique_colors = [hex_to_rgb(color) for color in unique_colors]
    unique_colors.append((0, 0, 0, 0))
    return min(256, get_next_power_of_two(len(unique_colors)))


def rasterize_svg_with_palette(svg_file, palette):
    # Parse the SVG file to extract its width and height
    tree = ET.parse(svg_file)
    root = tree.getroot()
    width = float(root.attrib.get("width", "0").replace("px", ""))
    height = float(root.attrib.get("height", "0").replace("px", ""))

    # Calculate padding to make it square
    if width > height:
        padding = (width - height) / 2
        new_viewbox = f"{root.attrib['viewBox']} -{padding} {width} {width}"
        root.attrib["viewBox"] = new_viewbox
        root.attrib["height"] = f"{width}px"
    elif height > width:
        padding = (height - width) / 2
        new_viewbox = f"-{padding} {root.attrib['viewBox']} {height} {height}"
        root.attrib["viewBox"] = new_viewbox
        root.attrib["width"] = f"{height}px"

    # Convert modified SVG tree back to a string
    modified_svg = ET.tostring(root, encoding="unicode")

    # Rasterize the modified SVG to PNG
    png_output = svg_file.replace(".svg", ".png")
    cairosvg.svg2png(
        bytestring=modified_svg.encode("utf-8"),
        write_to=png_output,
        output_width=2048,
        output_height=2048,
    )
    with Image.open(png_output) as im:
        # im = im.resize((256, 256))
        im = im.convert("RGBA")
        im = im.quantize(colors=palette)
        im.save(png_output)
    return png_output


def downsample_and_create_ico(png_file, palette, sizes):
    with Image.open(png_file) as im:
        im = im.convert("RGBA")
        ico_output = png_file.replace(".png", ".ico")
        images = [im.resize((i, i)).quantize(colors=palette, method=2) for i in sizes]
        images[-1].save(
            ico_output,
            format="ICO",
            sizes=[(i, i) for i in sizes],
            append_images=images,
        )
        icons = images
        total_width = sum(icon.width for icon in icons)
        max_height = max(icon.height for icon in icons)
        combined_image = Image.new("RGBA", (total_width, max_height))
        x_offset = 0
        for icon in icons:
            combined_image.paste(icon, (x_offset, 0))
            x_offset += icon.width
        combined_image.save(png_file.replace(".png", "-summary.png"))


def downsample_png(png_file, palette, sizes):
    with Image.open(png_file) as im:
        for i in sizes:
            im.resize((i, i)).quantize(colors=palette, method=2).save(
                png_file.replace(".png", f"-{i}.png")
            )
            im.resize((i, i)).quantize(colors=palette, method=2).save(
                png_file.replace(".png", f"-{i}.ico"), format="ICO", sizes=[(i, i)]
            )


def combine_icons_from_ico(ico_path, output_path):
    ico = Image.open(ico_path)
    icons = [ico.seek(index).copy() for index in range(len(ico.info.get("sizes")))]
    total_width = sum(icon.width for icon in icons)
    max_height = max(icon.height for icon in icons)
    combined_image = Image.new("RGBA", (total_width, max_height))
    x_offset = 0
    for icon in icons:
        combined_image.paste(icon, (x_offset, 0))
        x_offset += icon.width
    combined_image.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Utility for SVG and ICO processing.")
    subparsers = parser.add_subparsers(dest="command")

    # SVG Processing command
    svg_parser = subparsers.add_parser("svg2ico", help="Convert SVG to ICO.")
    svg_parser.add_argument("url", type=str, help="URL of the SVG file to download.")
    svg_parser.add_argument(
        "save_path", type=str, help="Local path to save the SVG file."
    )

    # ICO Processing command
    """ ico_parser = subparsers.add_parser(
        "combineico", help="Combine icons from ICO into a preview."
    )
    ico_parser.add_argument("ico_path", type=str, help="Path to the ICO file.")
    ico_parser.add_argument(
        "output_path", type=str, help="Output path for combined icons."
    ) """

    args = parser.parse_args()

    if args.command == "svg2ico":
        svg_path = download_svg_from_url(args.url, args.save_path)
        palette = extract_colors_from_svg(svg_path)
        png_file = rasterize_svg_with_palette(svg_path, palette)
        downsample_and_create_ico(
            png_file, palette, [16, 24, 32, 48, 64, 72, 80, 96, 128, 256]
        )
    # elif args.command == "combineico":
        # combine_icons_from_ico(args.ico_path, args.output_path)
    else:
        parser.print_help()
