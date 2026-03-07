from typing import override
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Key:
    raw: str

    @property
    def is_expression(self):
        return self.raw.startswith('(') and self.raw.endswith(')')

    @property
    def type(self):
        if not self.is_expression:
            return 'simple'
        match = re.search(r'^\(\s*([^\s\)]+)', self.raw)
        return match.group(1) if match else 'unknown'

    def get_tap_key(self):
        if 'tap-hold' in self.type:
            parts = self.raw.strip('()').split()
            return parts[2] if len(parts) >= 3 else None
        return self.raw if not self.is_expression else None

    @override
    def __repr__(self):
        return repr(self.raw)


@dataclass
class Layout:
    src: list[Key]
    positions: list[tuple[int, int]]
    layers: dict[str, list[Key]]


def parse_keys(g: str, delim: str) -> tuple[list[Key], list[tuple[int, int]]]:
    keys = []
    positions = []
    row = 0
    for line in g.split('\n'):
        if line.startswith('(def') or line == ')':
            continue
        fields = line.strip().split(delim)
        keys += [Key(f) for f in fields]
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

    Note: Primary key mappings are controlled by modifying the "miryoku" src
    key layout. For example, to map 'a' on miryoku's U_BASE layer (aka '2' on
    miryoku's src layer) to 'q' on the target layout's SRC layer, change '2' to
    'q' in miryoku's SRC layer.
    '''

    mkey_positions = {
        s.get_tap_key(): (i, p)
        for i, (s, p) in enumerate(zip(miryoku.src, miryoku.positions))
    }

    layers = {
        layer: [Key('') for _ in range(len(layout.positions))]
        for layer in miryoku.layers
    }

    for srcpos, key in zip(layout.positions, layout.src):
        lidx = layout.positions.index(srcpos)
        if res := mkey_positions.get(key.get_tap_key()):
            midx, _mpos = res
            for layer, mkeys in miryoku.layers.items():
                layers[layer][lidx] = mkeys[midx]

    for l, maps in layers.items():
        print()
        print(f'>>>> {l}\n')
        print()
        print(maps)

    return Layout(layout.src, layout.positions, layers)


def display(positions: list[tuple[int, int]], *keys_list: list[Key]):

    # fully copy the first layer (including empty/unmapping keys), for geometry
    d = {pos: key for pos, key in zip(positions, keys_list[0])}

    # fill in any fallback keys
    for keys in keys_list[::-1]:
        for pos, key in zip(positions, keys):
            if key.raw:
                d[pos] = key

    cur_row = 0
    for (r, c), key in sorted(d.items()):
        if r != cur_row:
            print()
            cur_row = r
        s = (key.get_tap_key() or '_').ljust(6)
        if key.is_expression:
            s = f'\033[93m{s}\033[0m'
        else:
            s = f'\033[92m{s}\033[0m'
        print(f'{s} ', end='')

    print()


def main():
    miryoku_str = Path('miryoku_kmonad.kbd').read_text()
    c302_str = Path('c302-colemakdh-base.kbd').read_text()

    miryoku = parse_layout(miryoku_str)
    c302 = parse_layout(c302_str)

    new_src = list(
        map(
            Key, ' '.join(
                (
                    '1 2 3 4 5 ' + '8 9 0 - =',
                    'q w e r t ' + 'u i o p [',
                    'a s d f g ' + "j k l ; '",
                    'c v b ' + 'n m ,',
                )
            ).split()
        )
    )

    print(new_src)

    assert len(new_src) == len(
        miryoku.src
    ), f'{len(new_src)} != {len(miryoku.src)}'
    miryoku.src = new_src

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
    final = apply_miryoku(miryoku, c302)

    print()
    # display(final.src, final.positions)
    print('Original Miryoku:\n')
    display(miryoku.positions, miryoku.layers['U_BASE'])
    print()
    print('Adapted Miryoku:\n')
    # display(final.positions, final.layers['U_BASE'], final.src)
    display(final.positions, final.layers['U_BASE'])


if __name__ == '__main__':
    main()
