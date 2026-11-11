"""Run the same installed unittest cases in chunks to avoid long single-test-run limits."""
from pathlib import Path
import importlib.util,sys,unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('test_projects',ROOT/'tests'/'test_projects.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
all_cases=unittest.TestLoader().loadTestsFromModule(mod)
flat=[]
def walk(t):
 if isinstance(t,unittest.TestSuite):
  for v in t:walk(v)
 else:flat.append(t)
walk(all_cases)
print('total',len(flat),flush=True)
idx=int(sys.argv[1]);sizes=[(0,25),(25,50),(50,len(flat))]
a,b=sizes[idx];result=unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(flat[a:b]))
print('chunk',idx,'range',a,b,'runs',result.testsRun,'fail',len(result.failures),'errors',len(result.errors),flush=True)
if not result.wasSuccessful():sys.exit(1)
