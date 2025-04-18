import sys
import argparse
import json
import os
from pikepdf import Pdf
from scramblepdf import scramble_pdf


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
        font_mappings = None

    pdf = Pdf.open(args.input_pdf)

    scramble_pdf(pdf, font_mappings, ratio)

    # write back the mapping so you can repeat the same scramble
    if args.mapping is not None:
        with open(args.mapping, 'w') as f:
            json.dump(font_mappings, f, indent=2)

    # save the scrambled PDF
    pdf.save(args.output_pdf)
    print(f"Written scrambled PDF to {args.output_pdf}")
    return 0


sys.exit(main())
