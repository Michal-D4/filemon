from radon.raw import analyze
from radon.metrics import mi_visit
from radon.complexity import cc_visit
from radon.cli.tools import iter_filenames
from pathlib import Path

for filename in iter_filenames(['.'], ignore="test,ui,tmp", exclude="*__init__.py"):
    module = Path(filename).stem
    with open(filename) as fobj:
        source = fobj.read()

    # get cc blocks
    blocks = cc_visit(source)
    for blk in blocks:
        if isinstance(blk, radon.visitors.Function):
            pass # 
            continue
        if isinstance(blk, radon.visitors.Class):
            pass
            continue
