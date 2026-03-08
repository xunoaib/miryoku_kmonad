import argparse
import re
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import override

DEFAULT_DEVICE_FILE = '/dev/input/event2'  # NOTE: change as needed


@dataclass(frozen=True)
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


def apply_miryoku(miryoku: Layout, layout: Layout, default_key: Key):
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
        layer: [default_key] * len(layout.positions)
        for layer in miryoku.layers
    }

    for srcpos, key in zip(layout.positions, layout.src):
        lidx = layout.positions.index(srcpos)
        if res := mkey_positions.get(key.get_tap_key()):
            midx, _mpos = res
            for layer, mkeys in miryoku.layers.items():
                layers[layer][lidx] = mkeys[midx]

    return Layout(layout.src, layout.positions, layers)


def display(positions: list[tuple[int, int]], *keys_list: list[Key]):

    # fully copy the first layer (including empty/unmapping keys), for geometry
    d = {pos: key for pos, key in zip(positions, keys_list[0])}

    # fill in any fallback keys
    for keys in keys_list[::-1]:
        for pos, key in zip(positions, keys):
            if key.raw not in ('', '_'):
                d[pos] = key

    keys = list(d.values())

    for row in keys_to_matrix(positions, keys):
        for key in row:
            s = (key.get_tap_key() or '_').ljust(6)
            if key.is_expression:
                s = f'\033[93m{s}\033[0m'
            else:
                s = f'\033[92m{s}\033[0m'
            print(f'{s} ', end='')
        print()
    print()


def keys_to_matrix(positions: list[tuple[int, int]], keys: list[Key]):
    d = {pos: key for pos, key in zip(positions, keys)}

    matrix = []
    cur_row: int | None = None
    for (r, _c), key in sorted(d.items()):
        if r != cur_row:
            cur_row = r
            matrix.append([])
        matrix[-1].append(key)

    if matrix and not matrix[-1]:
        matrix.pop()

    return matrix


def generate_kbd(layout: Layout, device_file: str):
    buf = StringIO()

    buf.write(
        f'''(defcfg
  input  (device-file "{device_file}")
  output (uinput-sink "Custom Miryoku KMonad output")
  fallthrough false
)\n\n'''
    )

    matrix = keys_to_matrix(layout.positions, layout.src)
    maps = '\n'.join('\t'.join(k.raw for k in row) for row in matrix)
    buf.write(f'(defsrc\n{maps}\n)\n\n')

    for layer, keys in layout.layers.items():
        matrix = keys_to_matrix(layout.positions, keys)
        maps = '\n'.join('\t'.join(k.raw for k in row) for row in matrix)
        buf.write(f'(deflayer {layer}\n{maps}\n)\n\n')

    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-m',
        '--miryoku',
        help='Path to miryoku.kdb',
        default='miryoku_kmonad.kbd'
    )
    parser.add_argument(
        '-l',
        '--layout',
        help='Path to keyboard layout.kbd to apply miryoku to',
        default='c302-colemakdh-base.kbd'
    )
    parser.add_argument(
        '-o',
        '--outfile',
        help='Path to output.kbd',
    )
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument(
        '-df',
        '--device-file',
        default=DEFAULT_DEVICE_FILE,
        help='Device file for keyboard'
    )
    args = parser.parse_args()

    print('-' * 30)
    print('Miryoku will be applied to the target layout.')
    print()
    print('  Miryoku Def:', args.miryoku)
    print('Target Layout:', args.layout)
    print('  Output Path:', args.outfile or '(stdout)')
    print('-' * 30)

    miryoku = parse_layout(Path(args.miryoku).read_text())
    layout = parse_layout(Path(args.layout).read_text())

    new_src = list(
        map(
            Key, ' '.join(
                (
                    '1 2 3 4 5 ' + '7 8 9 0 -',
                    'q w e r t ' + 'u i o p [',
                    'a s d f g ' + "j k l ; '",
                    'c v b ' + 'n m ,',
                )
            ).split()
        )
    )

    assert len(new_src) == len(
        miryoku.src
    ), f'{len(new_src)} != {len(miryoku.src)}'

    miryoku.src = new_src

    if args.debug:
        print('\033[93m==== Miryoku ====\033[0m\n')
        print('Src:', miryoku.src)
        print()
        print(miryoku.positions)
        print()
        print('Layers:', list(miryoku.layers.keys()))

        print('\n\033[93m==== Target Layout ====\033[0m\n')
        print('Src:', layout.src)
        print()
        print(layout.positions)
        print()
        print('Layers:', list(layout.layers.keys()))

    final = apply_miryoku(miryoku, layout, Key('_'))
    # final = apply_miryoku(miryoku, layout, Key('XX'))

    if args.debug:
        print('Original Miryoku:\n')
        display(miryoku.positions, miryoku.layers['U_BASE'])

        print('\nAdapted Miryoku:\n')
        # display(final.positions, final.layers['U_BASE'])
        display(final.positions, final.layers['U_BASE'], final.src)

    out = generate_kbd(final, args.device_file)
    out = '\n'.join(
        (
            ';; === Generated Miryoku Layout ===',
            ';; Reference Layout: ' + Path(args.layout).name + '\n',
            out,
        )
    ).strip()

    if args.outfile:
        outfile = Path(args.outfile)
        with open(outfile, 'w') as f:
            f.write(out)
        print('Wrote layout to', outfile)

    else:
        print(out)


if __name__ == '__main__':
    main()
