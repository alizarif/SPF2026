"""Rerun the replication from supplied cache/source files; no external APIs."""
from pathlib import Path
import subprocess,sys,argparse,os,shutil
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--rebuild-cache',action='store_true');p.add_argument('--with-workbook',action='store_true');a=p.parse_args()
env=dict(os.environ);env.setdefault('MPLCONFIGDIR',str(root/'runtime_cache/matplotlib'))
def run(name):
 print(f'Running {name}',flush=True);subprocess.run([sys.executable,str(root/'scripts'/name)],check=True,cwd=root.parent,env=env)
if a.rebuild_cache:
 run('build_data_cache.py');run('validate_data_cache.py')
for name in ['replicate_core_tables.py','replicate_table7.py','replicate_extended_tables.py','replicate_figures.py','check_oos_forecast_errors.py','assemble_report.py']:run(name)
if a.with_workbook:
 node=os.environ.get('NODE_BINARY') or shutil.which('node')
 if not node:raise RuntimeError('Optional workbook rebuild requires Node.js on PATH or NODE_BINARY.')
 subprocess.run([str(node),str(root/'scripts/build_comparison_workbook.mjs')],check=True,cwd=root.parent,env=env)
 run('validate_comparison_workbook.py')
print('Replication outputs rebuilt. Inspect updated discrepancies before interpreting results.')
