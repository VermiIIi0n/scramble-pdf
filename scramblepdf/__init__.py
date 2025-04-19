import random
import re
from math import ceil
from typing import Optional, Dict, Sequence
from pikepdf import Pdf

# Combine ranges and default scramble flags
UNICODE_REGIONS = {
    "ASCII Non-punctuation": {
        "ranges": [
            (0x41, 0x5A),  # A-Z
            (0x61, 0x7A),  # a-z
            (0x30, 0x39),  # 0-9
        ],
        "scramble": True
    },
    "CJK Characters": {
        "ranges": [
            (0x4E00, 0x9FFF)  # Basic CJK characters
        ],
        "scramble": True
    },
    "CJK Symbols": {
        "ranges": [
            (0x3000, 0x303F),  # CJK punctuation
            (0xFF00, 0xFFEF),  # Full-width characters
        ],
        "scramble": False
    },
    "ASCII Punctuation": {
        "ranges": [
            (0x21, 0x2F),  # !"#$%&'()*+,-./
            (0x3A, 0x40),  # :;<=>?@
            (0x5B, 0x60),  # [\]^_`
            (0x7B, 0x7E),  # {|}~
        ],
        "scramble": False
    },
    "Custom Selection": {
        # Custom ranges have highest priority
        "ranges": [
            (0x49, 0x49),  # I
            (0x30, 0x39),  # numbers : 0 - 9
            (0x56FE, 0x56FE),  # 图
            (0x8868, 0x8868),  # 表
            (0x5C71, 0x5C71),  # 山
            (0x4E1C, 0x4E1C),  # 东
            (0x5927, 0x5927),  # 大
            (0x5B66, 0x5B66),  # 学
            (0x672C, 0x672C),  # 本
            (0x79D1, 0x79D1),  # 科
            (0x6BD5, 0x6BD5),  # 毕
            (0x4E1A, 0x4E1A),  # 业
            (0x8BBA, 0x8BBA),  # 论
            (0x6587, 0x6587),  # 文
            (0x8BBE, 0x8BBE),  # 设
            (0x8BA1, 0x8BA1),  # 计
        ],
        "scramble": False   # Don't scramble by default
    },
}


def in_ranges(codepoint: int, ranges: Sequence[tuple[int, int]]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def parse_cmap(cmap_bytes: bytes) -> list[tuple[str, str]]:
    text = cmap_bytes.decode('utf-8', errors='ignore')
    block = re.search(r"beginbfchar\s*(.*?)\s*endcmap", text, flags=re.DOTALL)
    content = block.group(1) if block else text
    return re.findall(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", content)


def build_cmap(mapping: Dict[str, str]) -> str:
    max_len = max(len(src) for src in mapping)
    byte_len = max_len // 2
    min_code = '0' * (2*byte_len)
    max_code = 'F' * (2*byte_len)

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
        if i and i % 100 == 0 and i != len(mapping)-1:
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


def scramble_pdf(
    pdf: Pdf,
    font_mappings: Optional[Dict[str, Dict[str, str]]] = None,
    ratio: float = 1.0,
    exclude_codes: Optional[Sequence[str]] = None
) -> None:
    """
    Scramble ToUnicode, region flags are now built into UNICODE_REGIONS.
    exclude_codes: list of hex strings, e.g. ["0041","4E2D"]
    """
    if font_mappings is None:
        font_mappings = {}
    if not (0.0 <= ratio <= 1.0):
        raise ValueError("Ratio must be between 0.0 and 1.0")
    if ratio == 0.0:
        return

    exclude_set = set(c.upper() for c in (exclude_codes or []))
    custom_ranges = UNICODE_REGIONS["Custom Selection"]["ranges"]
    custom_scramble = UNICODE_REGIONS["Custom Selection"]["scramble"]

    for page in pdf.pages:
        fonts = page.get('/Resources', {}).get('/Font', {})
        for font_ref, font_obj in fonts.items():
            if "/ToUnicode" not in font_obj:
                continue

            basefont = str(font_obj["/BaseFont"])
            if basefont in font_mappings:
                mapping = font_mappings[basefont]
            else:
                raw = font_obj["/ToUnicode"].read_bytes()
                entries = parse_cmap(raw)
                if not entries:
                    continue

                to_scramble = []
                to_keep = []
                for src, dst in entries:
                    dst_hex = dst.upper()
                    if dst_hex in exclude_set:
                        to_keep.append((src, dst))
                        continue

                    code = int(dst_hex, 16)
                    # Custom ranges have highest priority
                    if in_ranges(code, custom_ranges):
                        if custom_scramble:
                            to_scramble.append((src, dst))
                        else:
                            to_keep.append((src, dst))
                        continue

                    # Process all other ranges according to UNICODE_REGIONS definitions
                    hit = False
                    for region in UNICODE_REGIONS.values():
                        if region is UNICODE_REGIONS["Custom Selection"]:
                            continue
                        if region["scramble"] and in_ranges(code, region["ranges"]):
                            hit = True
                            break

                    (to_scramble if hit else to_keep).append((src, dst))

                if not to_scramble:
                    continue

                srcs, dsts = zip(*to_scramble)
                cutoff = ceil(len(dsts)*(1-ratio))
                fixed = list(dsts[:cutoff])
                shuffled = list(dsts[cutoff:])
                random.shuffle(shuffled)
                new_dsts = fixed + shuffled

                mapping = {s: d for s, d in to_keep}
                mapping.update({src: new for src, new in zip(srcs, new_dsts)})
                font_mappings[basefont] = mapping

            new_cmap = build_cmap(mapping)
            font_obj['/ToUnicode'] = pdf.make_stream(new_cmap.encode('utf-8'))
