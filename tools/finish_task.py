# GENERATED TASK FINALIZATION 2.0.1; canonical CLI delegation
import pathlib,runpy,sys
sys.dont_write_bytecode=True
cli=pathlib.Path('C:\\Users\\Dell\\.codex\\local-marketplace\\plugins\\finish-task-publisher\\core\\cli.py')
sys.path.insert(0,str(cli.parent))
def check_path(value):
 import git_ops
 root=pathlib.Path(__file__).resolve().parents[1]
 if not git_ops.safe_path(root,value):raise ValueError("Unsafe declared task path: "+str(value))
 return (root/value).resolve().relative_to(root).as_posix()

if __name__=="__main__":
 sys.argv=[str(cli),'finish',*sys.argv[1:]]
 runpy.run_path(str(cli),run_name="__main__")
