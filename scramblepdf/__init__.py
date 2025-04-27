import random
import re
from itertools import chain
from typing import Container, Callable
from pikepdf import Pdf


def parse_cmap(cmap_bytes: bytes) -> list[tuple[str, str]]:
    text = cmap_bytes.decode('utf-8', errors='ignore')
    block = re.search(r"beginbfchar\s*(.*?)\s*endcmap", text, flags=re.DOTALL)
    content = block.group(1) if block else text
    return re.findall(r"<([0-9A-Fa-f]+)>\s+<([0-9A-Fa-f]+)>", content)


def build_cmap(mapping: dict[str, str]) -> str:
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
    ratio: float = 1.0,
    *,
    font_mappings: dict[str, dict[str, str]] | None = None,
    selector: Callable[[str], bool] | Container[str] | None = None,
    select_as_blacklist: bool = True,
) -> None:
    if font_mappings is None:
        font_mappings = {}
    if ratio < 0.0 or ratio > 1.0:
        raise ValueError("Ratio must be between 0.0 and 1.0")
    if ratio == 0.0:
        return
    if selector is not None and not callable(selector):
        if isinstance(selector, Container):
            sel_ctn = selector
            def selector(x): return x in sel_ctn
        else:
            raise ValueError("Selector must be callable or a container")

    # walk every page, every font, randomize its ToUnicode
    for page in pdf.pages:
        resources = page.get('/Resources', None)
        if resources is None:
            continue
        fonts = resources.get('/Font', None)
        if fonts is None:
            continue
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
                to_keep = list[tuple[str, str]]()
                to_scramble = list[tuple[str, str]]()
                for src, dst in entries:
                    dstc = bytes.fromhex(dst).decode(
                        'utf-16be', errors='ignore').strip('\x00')
                    if (
                        dstc and
                        (
                            selector is None
                            or (selector(dstc) != select_as_blacklist)
                        )
                        and random.random() <= ratio
                    ):
                        to_scramble.append((src, dst))
                    else:
                        to_keep.append((src, dst))
                srcs, dsts = zip(*to_scramble) if to_scramble else ([], [])
                ndsts = list(dsts)
                random.shuffle(ndsts)
                mapping = dict(chain(zip(srcs, ndsts), to_keep))
                font_mappings[basefont] = mapping

            # build a new CMap and replace the stream
            new_cmap_text = build_cmap(mapping)
            new_stream = pdf.make_stream(new_cmap_text.encode('utf-8'))
            font_obj['/ToUnicode'] = new_stream
