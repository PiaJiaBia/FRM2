"""Execute actual notebook kernels and save outputs/errors; independent chapter environments."""
from pathlib import Path
import json
import os
import sys
import time

PROJECT=Path(__file__).resolve().parents[1]
RUNTIME=PROJECT/'outputs'/'runtime'
if RUNTIME.exists():
    sys.path.insert(0,str(RUNTIME))
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager

ROOT=PROJECT/'service'/'Market Risk Measurement and Mangement'
OUT=PROJECT/'outputs'/'verification'
OUT.mkdir(exist_ok=True)
kernel=OUT/'kernels'/'python3'
kernel.mkdir(parents=True,exist_ok=True)
(kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
 'display_name':'Python 3','language':'python','env':{'PYTHONPATH':str(RUNTIME),'MPLBACKEND':'Agg'}}),encoding='utf-8')
os.environ['JUPYTER_RUNTIME_DIR']=str(OUT/'jupyter')
os.environ['IPYTHONDIR']=str(OUT/'ipython')
os.environ['PYTHONPATH']=str(RUNTIME)
report=[]
numbers=[int(x) if x.isdigit() else x for x in sys.argv[1:]] or list(range(1,19))
for number in numbers:
    path=(ROOT/f'Chapter{number}'/f'Chapter{number}_test.ipynb' if isinstance(number,int)
          else PROJECT/number if str(number).endswith('.ipynb')
          else PROJECT/number/f'{number}_test.ipynb')
    nb=nbformat.read(path,as_version=4)
    nbformat.validate(nb)
    manager=KernelManager(kernel_name='python3',kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(kernel.parent)]))
    client=NotebookClient(nb,timeout=180,kernel_name='python3',km=manager,resources={'metadata':{'path':str(path.parent)}})
    start=time.monotonic()
    try:
        client.execute()
        status='passed'
        error=''
    except Exception as exc:
        status='failed'
        error=str(exc)
    finally:
        if manager.has_kernel:
            manager.shutdown_kernel(now=True)
    nbformat.write(nb,path)
    row={'chapter':number,'status':status,'seconds':round(time.monotonic()-start,2),'error':error}
    report.append(row)
    print(f'Chapter {number}: {status} ({row["seconds"]}s)',flush=True)
    if error: print(error[-2200:],flush=True)
(OUT/('notebook_results_'+ '_'.join(str(x).replace('/', '_').replace('\\', '_') for x in numbers)+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
sys.exit(any(row['status']=='failed' for row in report))
