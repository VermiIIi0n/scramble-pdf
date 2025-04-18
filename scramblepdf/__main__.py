import sys
import argparse
import random
import json
import os
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Obfuscate PDF text by scrambling each font’s /ToUnicode mapping"
    )
    parser.add_argument("input_pdf", help="Source PDF path")
    parser.add_argument("output_pdf", help="Scrambled PDF output path")
    parser.add_argument(
        "--mapping", default=None,
        help="Where to read/write the old→new codepoint mappings"
    )
    parser.add_argument("-r", "--ratio", type=float, default=1.0,
                        help="Ratio of encoding mappings to scramble (0.0-1.0)")
    args = parser.parse_args()

    ratio = max(0.0, min(1.0, args.ratio))

    # load or init the mapping store
    if args.mapping is not None and  os.path.exists(args.mapping):
            with open(args.mapping, 'r') as f:
                font_mappings = json.load(f)
    else:
        font_mappings = {}

    pdf = Pdf.open(args.input_pdf)

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

    # write back the mapping so you can repeat the same scramble
    if args.mapping is not None:
        with open(args.mapping, 'w') as f:
            json.dump(font_mappings, f, indent=2)

    # save the scrambled PDF
    pdf.save(args.output_pdf)
    print(f"Written scrambled PDF to {args.output_pdf}")
    return 0


sys.exit(main())
