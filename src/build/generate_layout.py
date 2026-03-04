import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Layout:
    src: list[list[str]]
    layers: dict[str, list[list[str]]]


def parse_keys(g: str, delim: str) -> list[list[str]]:
    rows = []
    for line in g.split('\n'):
        if line.startswith('(def') or line == ')':
            continue
        fields = line.strip().split(delim)
        rows.append(fields)
    return rows


def parse_layout(text: str):
    src = None
    layers = {}

    for g in re.findall(r'\n\(def.*?\n\)', text, re.DOTALL):
        g = g.strip()
        if g.startswith('(defcfg'):
            pass
        elif g.startswith('(defalias'):
            pass
        elif g.startswith('(defsrc'):
            src = parse_keys(g, '\t')
        elif g.startswith('(deflayer'):
            name = g.split('\n')[0].split(' ')[1]
            layer = parse_keys(g, '\t')
            layers[name] = layer
        else:
            raise ValueError('unknown pattern:', repr(g))

    assert src
    return Layout(src, layers)


def main():
    text = Path('miryoku_kmonad.kbd').read_text()
    text = Path('c302-colemakdh-base.kbd').read_text()
    layout = parse_layout(text)

    print('Src:', layout.src)
    print()
    print('Layers:', list(layout.layers.keys()))


if __name__ == '__main__':
    main()
