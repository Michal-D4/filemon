from radon.complexity import cc_visit
from radon.cli.tools import iter_filenames
from pathlib import Path

def cc_report(module: str='') -> list:
    lst = []
    for filename in iter_filenames(['.'], ignore="test,ui,tmp", exclude="*__init__.py"):
        modu_ = Path(filename).stem
        if (not module) | (module == modu_):
            with open(filename) as fobj:
                source = fobj.read()
                lst.extend(in_cc_report(modu_, source))    
    return lst


def in_cc_report(module: str, source: str) -> list:
    res = []
    # get cc blocks
    blocks = cc_visit(source)
    for blk in blocks:
        tt = str(blk).split()[0:5:2]
        length = blk.endline - blk.lineno + 1
        if tt[0] == 'C':
            res.append((tt[2], length, tt[0], module, tt[1], ''))
        elif tt[0] == 'F':
            res.append((tt[2], length, tt[0], module, '', tt[1]))
        else:
            res.append((tt[2], length ,tt[0], module, *tt[1].split('.')))
    return res
