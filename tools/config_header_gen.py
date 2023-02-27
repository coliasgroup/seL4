# Copyright 2022, seL4 Project a Series of LF Projects, LLC
#
# SPDX-License-Identifier: BSD-2-Clause
#

import sys
import yaml
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Generate a configuration C header from a configuration YAML file.",
    )
    parser.add_argument(
        "in_file",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Input YAML file.",
    )
    parser.add_argument(
        "-o",
        dest="out_file",
        type=argparse.FileType("w"),
        default=sys.stdout,
        help="Output C header file.",
    )
    args = parser.parse_args()
    generate(args.in_file, args.out_file)


def generate(in_file, out_file):
    config = yaml.safe_load(in_file)

    header_contents = "#pragma once\n\n"

    for key, value in config.items():
        macro = f"CONFIG_{key}"

        if isinstance(value, bool):
            if value:
                entry = f"#define {macro}  1"
            else:
                entry = f"/* disabled: {macro} */"
        elif isinstance(value, str):
            if value:
                entry = f"#define {macro}  {value}"
            else:
                entry = f"#define {macro}  /* empty */"
        else:
            raise Exception(
                f"Unexpected type for configuration key {key}:", type(value))

        header_contents += f"{entry}\n"

    out_file.write(header_contents)


if __name__ == "__main__":
    main()
