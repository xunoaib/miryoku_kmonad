import re
from pathlib import Path


def parse_keys(g: str):
    rows = []
    for line in g.split('\n'):
        if line.startswith('(def') or line == ')':
            continue
        fields = line.strip().split(' ')
        rows.append(fields)
    return rows


def main():
    text = Path('miryoku_kmonad.kbd').read_text()

    keys = {}

    for g in re.findall(r'\n\(def.*?\n\)', text, re.DOTALL):
        g = g.strip()

        # print(repr(g))
        # print()

        if g.startswith('(defcfg'):
            pass
        elif g.startswith('(defsrc'):
            keys = parse_keys(g)
            __import__('pprint').pprint(keys)
        elif g.startswith('(deflayer'):
            pass
        else:
            raise ValueError('unknown pattern:', repr(g))


if __name__ == '__main__':
    main()
