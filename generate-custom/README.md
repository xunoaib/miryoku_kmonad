# Miryoku Layout Adapter

This tool applies Miryoku to a custom keyboard layout via KMonad.

**Note:** There's probably a more robust way to do this with the existing Miryoku/KMonad toolchain, but I wasn't sure how to do it.

## Inputs

The "base" layout defines the actual keyboard layout you're targeting. All keys should be defined in `defsrc`. Everything else, such as layers, are ignored.

The Miryoku "reference" layout defines all the Miryoku layers to be applied to the base layout. `defsrc` is ignored, as it will be substituted with an explicit miryoku-to-base key "mapping".

The "mapping" file defines which base keys to apply Miryoku to, and literally replaces the `defsrc` of the Miryoku reference layout. (In hindsight, this is suboptimal and overly complex. The appropriate `defsrc` can probably be modified directly in the Miryoku reference file, but alas.)

The input device path defines which input device to apply the KMonad config to (i.e. `/dev/input/event2`). This will likely have to be changed depending on your system, and should ideally be a uniquely identifiable device path (`/dev/input/by-id/...`).

## Example Usage

```sh
python generate_layout.py \
    -m miryoku_kmonad.kbd \
    -l c302-base.kbd \
    -p c302-mapping.txt \
    -df /dev/input/event2 \
    -o c302-miryoku-output.kbd
```
