from __future__ import annotations

import argparse
import binascii
import json
import struct
import zlib
from pathlib import Path

from skillbridge import Workspace


def skill_string(value: str) -> str:
    return json.dumps(value)


def export_png_via_skillbridge(workspace_id: str, out_png: Path) -> None:
    ws = Workspace.open(None if workspace_id == "default" else workspace_id)
    try:
        expr = (
            'let((w) '
            'w=hiGetCurrentWindow() '
            'schZoomFit(1.0 1.0) '
            f'hiExportImage(?fileName {skill_string(str(out_png))} '
            '?window w ?bgColor "white" ?transparentBG nil ?fileType "png" ?keepAspect t ?width 2600 ?verbose nil))'
        )
        ws._channel.send(expr)
    finally:
        ws.close()


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def parse_png(png_path: Path) -> tuple[int, int, bytes]:
    data = png_path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a PNG file")

    pos = 8
    width = height = bit_depth = color_type = None
    idat_parts: list[bytes] = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk_data = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, compression, flt, interlace = struct.unpack(">IIBBBBB", chunk_data)
            if bit_depth != 8 or interlace != 0 or compression != 0 or flt != 0:
                raise ValueError("Unsupported PNG encoding")
            if color_type not in {2, 6}:
                raise ValueError(f"Unsupported PNG color type {color_type}")
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            break

    assert width is not None and height is not None and color_type is not None
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(b"".join(idat_parts))
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError("Unexpected decompressed PNG size")

    rows: list[bytearray] = []
    prev = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        row = bytearray(raw[offset:offset + stride])
        offset += stride
        if filter_type == 1:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                row[i] = (row[i] + left) & 0xFF
        elif filter_type == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif filter_type == 3:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = prev[i]
                row[i] = (row[i] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            for i in range(stride):
                left = row[i - channels] if i >= channels else 0
                up = prev[i]
                up_left = prev[i - channels] if i >= channels else 0
                row[i] = (row[i] + paeth(left, up, up_left)) & 0xFF
        elif filter_type != 0:
            raise ValueError(f"Unsupported PNG filter {filter_type}")
        rows.append(row)
        prev = row

    rgb = bytearray()
    if channels == 3:
        for row in rows:
            rgb.extend(row)
    else:
        for row in rows:
            for i in range(0, len(row), 4):
                alpha = row[i + 3] / 255.0
                rgb.append(int(round(row[i] * alpha + 255 * (1 - alpha))))
                rgb.append(int(round(row[i + 1] * alpha + 255 * (1 - alpha))))
                rgb.append(int(round(row[i + 2] * alpha + 255 * (1 - alpha))))
    return width, height, bytes(rgb)


def contrast_enhance_rgb(rgb: bytes) -> bytes:
    out = bytearray(len(rgb))
    for i in range(0, len(rgb), 3):
        r = rgb[i]
        g = rgb[i + 1]
        b = rgb[i + 2]
        if r > 245 and g > 245 and b > 245:
            nr, ng, nb = 255, 255, 255
        elif r > 200 and g > 190 and b < 140:
            nr, ng, nb = 130, 90, 0
        elif g > 170 and r < 150 and b < 150:
            nr, ng, nb = 0, 115, 45
        elif b > 180 and g > 170 and r < 170:
            nr, ng, nb = 20, 95, 170
        elif r > 190 and g < 120 and b < 120:
            nr, ng, nb = 180, 35, 25
        elif r > 170 and g > 120 and b < 120:
            nr, ng, nb = 165, 80, 10
        else:
            nr = max(0, min(255, int(r * 0.78)))
            ng = max(0, min(255, int(g * 0.78)))
            nb = max(0, min(255, int(b * 0.78)))
        out[i] = nr
        out[i + 1] = ng
        out[i + 2] = nb
    return bytes(out)


def write_png(width: int, height: int, rgb: bytes, out_png: Path) -> None:
    stride = width * 3
    raw = bytearray()
    for row_idx in range(height):
        raw.append(0)
        start = row_idx * stride
        raw.extend(rgb[start:start + stride])
    compressed = zlib.compress(bytes(raw), level=9)

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = binascii.crc32(chunk_type)
        crc = binascii.crc32(data, crc) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(chunk(b"IHDR", ihdr))
    png.extend(chunk(b"IDAT", compressed))
    png.extend(chunk(b"IEND", b""))
    out_png.write_bytes(png)


def make_pdf_with_rgb_image(width: int, height: int, rgb: bytes, out_pdf: Path) -> None:
    compressed = zlib.compress(rgb)
    page_w = float(width)
    page_h = float(height)
    objects: list[bytes] = []

    def add_object(payload: bytes) -> int:
        objects.append(payload)
        return len(objects)

    catalog_id = add_object(b"<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    page_id = add_object(
        f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_w:.2f} {page_h:.2f}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>".encode(),
    )
    image_id = add_object(
        f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(compressed)} >>\nstream\n".encode()
        + compressed + b"\nendstream",
    )
    contents_stream = f"q\n{page_w:.2f} 0 0 {page_h:.2f} 0 0 cm\n/Im0 Do\nQ\n".encode()
    contents_id = add_object(
        f"<< /Length {len(contents_stream)} >>\nstream\n".encode() + contents_stream + b"endstream",
    )
    _ = (catalog_id, page_id, image_id, contents_id)

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode(),
    )
    out_pdf.write_bytes(pdf)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export the current live schematic window to a white-background PDF")
    parser.add_argument("--workspace-id", default="default")
    parser.add_argument("--png", type=Path, default=Path("/tmp/live_schematic_export.png"))
    parser.add_argument("--pdf", type=Path, default=Path("/tmp/live_schematic_export.pdf"))
    parser.add_argument("--contrast-png", type=Path, default=None)
    args = parser.parse_args()

    export_png_via_skillbridge(args.workspace_id, args.png)
    width, height, rgb = parse_png(args.png)
    contrast_png = args.contrast_png or args.png.with_name(args.png.stem + "_contrast.png")
    contrast_rgb = contrast_enhance_rgb(rgb)
    write_png(width, height, contrast_rgb, contrast_png)
    make_pdf_with_rgb_image(width, height, contrast_rgb, args.pdf)

    print(json.dumps({
        "png": str(args.png),
        "contrast_png": str(contrast_png),
        "pdf": str(args.pdf),
        "width": width,
        "height": height,
        "png_size": args.png.stat().st_size,
        "contrast_png_size": contrast_png.stat().st_size,
        "pdf_size": args.pdf.stat().st_size,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
