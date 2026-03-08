import argparse
import re
import sys
from dataclasses import dataclass
from functools import partial
from io import StringIO
from pathlib import Path
from typing import override

DEFAULT_DEVICE_FILE = '/dev/input/event2'  # NOTE: change as needed

DEFAULT_LAYOUT = 'c302-base.kbd'
DEFAULT_MAPPING = 'c302-mapping.txt'
DEFAULT_MIRYOKU = 'miryoku_kmonad.kbd'

log = partial(print, file=sys.stderr)


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


def parse_keys(kmonad_conf: str,
               delim: str) -> tuple[list[Key], list[tuple[int, int]]]:
    keys = []
    positions = []
    row = 0
    for line in kmonad_conf.split('\n'):
        if line.startswith('(def') or line == ')':
            continue
        fields = line.strip().split(delim)
        keys += [Key(f) for f in fields]
        positions += [(row, c) for c in range(len(fields))]
        row += 1
    return keys, positions


def parse_layout(kmonad_conf: str):
    src = []
    positions = []
    layers = {}

    for g in re.findall(r'\n\(def.*?\n\)', kmonad_conf, re.DOTALL):
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
            log(f'{s} ', end='')
        log()
    log()


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


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-m', '--miryoku', help='Path to miryoku.kdb', default=DEFAULT_MIRYOKU
    )
    parser.add_argument(
        '-l',
        '--layout',
        help='Path to keyboard layout.kbd to apply miryoku to',
        default=DEFAULT_LAYOUT
    )
    parser.add_argument(
        '-p',
        '--mapping',
        help='Keys in target layout to map Miryoku to',
        default=DEFAULT_MAPPING
    )
    parser.add_argument(
        '-df',
        '--device-file',
        default=DEFAULT_DEVICE_FILE,
        help='Device file for keyboard'
    )
    parser.add_argument(
        '-o',
        '--outfile',
        help='Path to output.kbd',
    )
    parser.add_argument(
        '-fb',
        '--fallback-key',
        default='_',
        help='Key to use for unmapped keys in base layer (default: _)'
    )
    parser.add_argument('-d', '--debug', action='store_true')
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    log('-' * 30)
    log('Miryoku will be applied to the target layout.')
    log()
    log('Miryoku Reference KBD:', args.miryoku)
    log('    Custom Layout KBD:', args.layout)
    log('Custom Layout Mapping:', args.mapping)
    log()
    log('  Output Path:', args.outfile or '(stdout)')
    log('-' * 30)

    miryoku = parse_layout(Path(args.miryoku).read_text())
    layout = parse_layout(Path(args.layout).read_text())

    mapping_str = Path(args.mapping).read_text()
    src = list(map(Key, mapping_str.split()))

    if len(src) != len(miryoku.src):
        raise ValueError(
            f'Source map length does not match Miryoku keymap length: {len(src)} != {len(miryoku.src)}'
        )

    miryoku.src = src

    if args.debug:
        log('\033[93m==== Miryoku ====\033[0m\n')
        log('Src:', miryoku.src)
        log()
        log(miryoku.positions)
        log()
        log('Layers:', list(miryoku.layers.keys()))

        log('\n\033[93m==== Target Layout ====\033[0m\n')
        log('Src:', layout.src)
        log()
        log(layout.positions)
        log()
        log('Layers:', list(layout.layers.keys()))

    final = apply_miryoku(miryoku, layout, Key(args.fallback_key))

    if args.debug:
        log('Original Miryoku:\n')
        display(miryoku.positions, miryoku.layers['U_BASE'])

        log('\nAdapted Miryoku:\n')
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
        log('Wrote layout to', outfile)

    else:
        print(out)


if __name__ == '__main__':
    main()
