import random
import re
from math import ceil
from pikepdf import Pdf


def parse_cmap(cmap_bytes):
    """
    Extract all <src> <dst> pairs from the beginbfchar...endbfchar block.
    Returns a list of (src_hex, dst_hex) strings (without angle brackets).
    """
    text = cmap_bytes.decode('utf-8', errors='ignore')
    m = re.search(r"beginbfchar\s*(.*?)\s*endcmap", text, flags=re.DOTALL)
    block = m.group(1) if m else text
    return re.findall(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", block)


def build_cmap(mapping):
    """
    Given a dict of src_hex->dst_hex, build a minimal CMap text
    that uses beginbfchar with exactly those entries.
    """
    # determine byte‐width from length of hex digits
    max_len = max(len(src) for src in mapping)
    byte_len = max_len // 2
    min_code = '0' * (2 * byte_len)
    max_code = 'F' * (2 * byte_len)

    lines = [
        "%!PS-Adobe-3.0 Resource-CMap",
        "%%DocumentNeededResources: procset CIDInit",
        "%%IncludeResource: procset CIDInit",
        "%%BeginResource: CMap Custom",
        "%%Title: (Custom Adobe Identity 0)",
        "%%Version: 1",
        "%%EndComments",
        "/CIDInit /ProcSet findresource begin",
        "12 dict begin",
        "begincmap",
        "/CIDSystemInfo 3 dict dup begin",
        "    /Registry (Adobe) def",
        "    /Ordering (Identity) def",
        "    /Supplement 0 def",
        "end def",
        "/CMapName /Custom def",
        "/CMapVersion 1 def",
        "/CMapType 0 def",
        "/WMode 0 def",
        "1 begincodespacerange",
        f"<{min_code}> <{max_code}>",
        "endcodespacerange",
        f"{min(100, len(mapping))} beginbfchar",
    ]
    for i, (src, dst) in enumerate(mapping.items()):
        if i and i % 100 == 0 and i != len(mapping) - 1:
            # break the list into chunks of 100
            lines.append("endbfchar")
            lines.append(f"{min(100, len(mapping)-i)} beginbfchar")
        lines.append(f"<{src}> <{dst}>")
    lines += [
        "endbfchar",
        "endcmap",
        "CMapName currentdict /CMap defineresource pop",
        "end",
        "end",
        "%%EndResource",
        "%%EOF"
    ]

    return "\n".join(lines)


def scramble_pdf(pdf: Pdf, font_mappings: dict | None = None, ratio=1.0) -> None:
    if font_mappings is None:
        font_mappings = {}
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError("Ratio must be between 0.0 and 1.0")
    if ratio == 0.0:
        # nothing to do
        return
    # walk every page, every font, randomize its ToUnicode
    for page in pdf.pages:
        resources = page.get('/Resources', {})
        fonts = resources.get('/Font', {})
        for font_ref, font_obj in fonts.items():
            if '/ToUnicode' not in font_obj:
                continue

            basefont = str(font_obj.get('/BaseFont'))
            # either reuse a previous shuffle...
            if basefont in font_mappings:
                mapping = font_mappings[basefont]
            else:
                # parse original ToUnicode CMap
                cmap_stream = font_obj['/ToUnicode']
                raw = cmap_stream.read_bytes()
                entries = parse_cmap(raw)
                if not entries:
                    # nothing to shuffle
                    continue

                srcs, dsts = zip(*entries)
                new_dsts = list(dsts[ceil(len(dsts) * (1 - ratio)):])
                random.shuffle(new_dsts)
                new_dsts = list(dsts[:ceil(len(dsts) * (1 - ratio))]) + new_dsts
                mapping = dict(zip(srcs, new_dsts))
                font_mappings[basefont] = mapping

            # build a new CMap and replace the stream
            new_cmap_text = build_cmap(mapping)
            new_stream = pdf.make_stream(new_cmap_text.encode('utf-8'))
            font_obj['/ToUnicode'] = new_stream
