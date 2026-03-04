import re
from pathlib import Path

text = Path('miryoku_kmonad.kbd').read_text()

for g in re.findall(r'\n\(def.*?\n\)', text, re.DOTALL):
    print(repr(g))
    print()
