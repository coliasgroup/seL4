import glob
import re
from pathlib import Path
from argparse import ArgumentParser

import os

def main():
    parser = ArgumentParser()
    parser.add_argument('out_dir')
    parser.add_argument('include_dirs')
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    include_dirs = list(map(Path, args.include_dirs.split(':')))

    for d in include_dirs:
        for abs_path in glob.glob(f'{d}/**/*.h', recursive=True):
            rel_path = Path(abs_path).relative_to(d)
            in_path = d / rel_path
            out_path = out_dir / rel_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            in_text = in_path.read_text()
            if in_path.name == 'macros.h':
                out_text = in_text
            else:
                out_text = transform(in_text)
            out_path.write_text(out_text)

def transform(text):
    return \
        remove_definitions(
            remove_redundant_declarations(
                text
            )
        )

def remove_redundant_declarations(text):
    r = re.compile(
            r'LIBSEL4_INLINE(_FUNC)?(?P<sig>[^{;]*);',
            re.MULTILINE | re.DOTALL,
            )

    return r.sub('', text)

def remove_definitions(text):
    r = re.compile(
            r'LIBSEL4_INLINE(_FUNC)?(?P<sig>[^{;]*){.*?^}',
            re.MULTILINE | re.DOTALL,
            )

    def f(match):
        sig = match['sig']
        sig = sig.replace('LIBSEL4_INLINE_FUNC', '') # HACK for cases where on sig is chosen from many by an #ifdef (e.g. with CONFIG_KERNEL_MCS)
        return f'{sig};'

    return r.sub(f, text)

if __name__ == '__main__':
    main()
