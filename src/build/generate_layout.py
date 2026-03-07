import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Layout:
    src: list[str]
    positions: list[tuple[int, int]]
    layers: dict[str, list[str]]


def parse_keys(g: str, delim: str):
    keys = []
    positions = []
    row = 0
    for line in g.split('\n'):
        if line.startswith('(def') or line == ')':
            continue
        fields = line.strip().split(delim)
        keys += fields
        positions += [(row, c) for c in range(len(fields))]
        row += 1
    return keys, positions


def parse_layout(text: str):
    src = []
    positions = []
    layers = {}

    for g in re.findall(r'\n\(def.*?\n\)', text, re.DOTALL):
        g = g.strip()
        if g.startswith('(defcfg'):
            pass
        elif g.startswith('(defalias'):
            pass
        elif g.startswith('(defsrc'):
            src, positions = parse_keys(g, ' ')
        elif g.startswith('(deflayer'):
            name = g.split('\n')[0].split(' ')[1]
            layer, _positions = parse_keys(g, '\t')
            layers[name] = layer
        else:
            raise ValueError('unknown pattern:', repr(g))

    assert src
    assert positions
    return Layout(src, positions, layers)


def apply_miryoku(miryoku: Layout, layout: Layout):
    '''Apply miryoku to an existing layout.
    Defsrc is copied as-is.
    Miryoku is applied to the given base_layer (with char-to-char mappings).
    Any other layers in the original layout will be discarded.
    '''

    mkey_positions = {
        s: (i, p)
        for i, (s, p) in enumerate(zip(miryoku.src, miryoku.positions))
    }

    layers = {layer: ['❌'] * len(layout.positions) for layer in miryoku.layers}

    for srcpos, key in zip(layout.positions, layout.src):
        lidx = layout.positions.index(srcpos)
        if res := mkey_positions.get(key):
            midx, _mpos = res
            for layer, mkeys in miryoku.layers.items():
                layers[layer][lidx] = mkeys[midx]

    for l, maps in layers.items():
        print()
        print(f'>>>> {l}\n')
        print()
        print(maps)


def main():
    miryoku_str = Path('miryoku_kmonad.kbd').read_text()
    c302_str = Path('c302-colemakdh-base.kbd').read_text()

    miryoku = parse_layout(miryoku_str)
    c302 = parse_layout(c302_str)

    print('\033[93m==== Miryoku ====\033[0m\n')
    print('Src:', miryoku.src)
    # print()
    # print(miryoku.positions)
    # print()
    # print('Layers:', list(miryoku.layers.keys()))

    print('\n\033[93m==== C302 ====\033[0m\n')
    print('Src:', c302.src)
    # print()
    # print(c302.positions)
    # print()
    # print('Layers:', list(c302.layers.keys()))

    print('-' * 30)
    apply_miryoku(miryoku, c302)


if __name__ == '__main__':
    main()
