#!/usr/bin/env python3
"""Run every query with its DEMO arguments and compare with its known-good CHECK. Run after the pipeline."""
import glob, importlib.util, os, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, here)
bad = 0
files = sorted(glob.glob(os.path.join(here, 'q[0-9][0-9]_*.py')))
for f in files:
    name = os.path.basename(f)[:-3]
    spec = importlib.util.spec_from_file_location(name, f)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    try:
        ans = m.answer(**m.DEMO)
        ok = bool(m.CHECK(ans)) if hasattr(m, 'CHECK') else bool(ans)
    except Exception as e:                       # report, do not hide
        ans, ok = repr(e), False
    bad += not ok
    print(('PASS ' if ok else 'FAIL ') + name + '  ' + m.QUESTION + ('' if ok else '  -> ' + str(ans)[:200]))
print('\n%d/%d questions answered and checked' % (len(files) - bad, len(files)))
sys.exit(1 if bad else 0)
