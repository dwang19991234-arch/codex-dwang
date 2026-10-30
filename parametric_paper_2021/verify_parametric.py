"""Offline checks for geometry expressions and conductor topology; not HFSS QA."""
from pathlib import Path
import ast,itertools,json,os,warnings,re
os.environ.setdefault('MPLCONFIGDIR','/tmp/parametric-check-mpl')
import numpy as np
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
from matplotlib.path import Path as PolygonPath
from matplotlib.patches import Polygon
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parent
FUNS={'u','rectangle','core_geometry','paper_outline','geometry','parametric_geometry','check_local_parameters'}

def load(path):
 tree=ast.parse(path.read_text())
 body=[n for n in tree.body if isinstance(n,ast.Assign) or isinstance(n,ast.FunctionDef) and n.name in FUNS]
 ns={};exec(compile(ast.Module(body=body,type_ignores=[]),str(path),'exec'),ns);return ns

def scalar(v,p):
 if isinstance(v,(float,int)):return float(v)
 expr=ast.parse(v.replace('um',''),mode='eval').body
 def calc(n):
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.Name):return p[n.id]
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):return -calc(n.operand)
  if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.UAdd):return calc(n.operand)
  if isinstance(n,ast.BinOp):
   a,b=calc(n.left),calc(n.right)
   if isinstance(n.op,ast.Add):return a+b
   if isinstance(n.op,ast.Sub):return a-b
   if isinstance(n.op,ast.Mult):return a*b
   if isinstance(n.op,ast.Div):return a/b
  raise ValueError(v)
 return float(calc(expr))

def concrete(polys,p):return [(name,[(scalar(x,p),scalar(y,p)) for x,y in v]) for name,v in polys]

def main():
 ns=load(R/'build_parametric_2021.py');p=ns['P'];left,cuts,strips=ns['parametric_geometry'](p)
 old=load(R.parent/'paper_layout_2021/build_paper_layout_2021.py')
 a,b,c=old['geometry'](old['P'])
 assert left==a
 for actual,expected in zip(concrete(cuts+strips,p),b+c):
  assert actual[0]==expected[0] and np.allclose(actual[1],expected[1],atol=1e-10)
 strings=' '.join(str(v) for name,poly in cuts+strips for pt in poly for v in pt if isinstance(v,str))
 for variable in ['slot_L','slot_D','slot_shift']:assert variable in strings
 lengths=[260,300,340,380,420];distances=[100,125,150,175,200];shifts=[-20,-10,0,10,20]
 allcases=list(itertools.product(lengths,distances,shifts))
 for ll,dd,ss in allcases:
  q=dict(p,slot_L=ll,slot_D=dd,slot_shift=ss);ns['check_local_parameters'](q)
 cases=set([(ll,125,0) for ll in lengths]+[(260,dd,0) for dd in distances]+[(260,125,ss) for ss in shifts]+list(itertools.product([260,420],[100,200],[-20,20])))
 anchor=dict(p);anchor['slot_D']=ns['ANCHOR_SLOT_D'];outline=ns['paper_outline'](anchor)[3]
 x=np.arange(np.floor(left)+.5,p['chip_right'],4.);y=np.arange(-600+.5,600,4.)
 xx,yy=np.meshgrid(x,y);points=np.column_stack((xx.ravel(),yy.ravel()))
 def at(comp,xx0,yy0):return int(comp[np.argmin(abs(y-yy0)),np.argmin(abs(x-xx0))])
 for ll,dd,ss in sorted(cases):
  q=dict(p,slot_L=ll,slot_D=dd,slot_shift=ss)
  _,cuts,strips=ns['parametric_geometry'](q)
  mask=PolygonPath(outline).contains_points(points)
  for n,v in concrete(cuts,q):mask &= ~PolygonPath(v).contains_points(points)
  for n,v in concrete(strips,q):mask |= PolygonPath(v).contains_points(points)
  comp,n=label(mask.reshape(xx.shape))
  assert n==2,(ll,dd,ss,n)
  assert at(comp,-5,0)!=0 and at(comp,5,0)!=0
  assert at(comp,-5,0)!=at(comp,5,0)
  assert at(comp,5,0)==at(comp,300,250)
  assert at(comp,-5,0)==at(comp,left+50,0)
 figs=[('Nominal',260,125,0),('Longer slots',420,125,0),('Larger separation',260,200,0),('Shifted pair',260,125,20)]
 fig,axes=plt.subplots(2,2,figsize=(11,9),sharex=True,sharey=True,layout='constrained')
 for ax,(title,ll,dd,ss) in zip(axes.ravel(),figs):
  q=dict(p,slot_L=ll,slot_D=dd,slot_shift=ss);_,cuts,strips=ns['parametric_geometry'](q)
  ax.add_patch(Polygon(outline,color='#e5b641',lw=0))
  for n,v in concrete(cuts,q):ax.add_patch(Polygon(v,color='white',lw=0))
  for n,v in concrete(strips,q):ax.add_patch(Polygon(v,color='#e5b641',lw=0))
  ax.add_patch(Polygon(ns['rectangle'](-3,-6,3,6),color='#aa3d70',lw=0))
  ax.set(xlim=(-250,180),ylim=(-250,250),xlabel='x (um)',ylabel='y (um)',title='%s: L=%g, D=%g, shift=%g um'%(title,ll,dd,ss));ax.set_aspect('equal')
 fig.suptitle('Parametric geometry previews; fixed port at x=0 (pink) — not simulation results')
 fig.savefig(R/'parameter_preview.png',dpi=170);plt.close(fig)
 warnings.filterwarnings('ignore',category=DeprecationWarning)
 from lib2to3.refactor import RefactoringTool
 RefactoringTool([]).refactor_string((R/'build_parametric_2021.py').read_text(),'build_parametric_2021.py')
 # Capture the actual port payload from a complete fake desktop run is not used
 # as a solver test. Check fixed integration line construction directly instead.
 assert ns['u'](-p['det_gap']/2)=='-3um' and ns['u'](p['det_gap']/2)=='3um'
 report={'nominal_geometry_matches_previous_model':True,
 'HFSS_coordinate_expressions_reference_all_three_variables':True,
 'geometric_constraints_checked':len(allcases),'raster_connectivity_cases':len(cases),'raster_pitch_um':4,
 'port_integration_line_fixed':['-3um','3um'],'python2_grammar':'passed',
 'HFSS_runtime':'not_executed','HFSS_Optimetrics_API':'prepared using native schema; not runtime-validated',
 'scope':'Geometry and syntax checks do not establish solver or sweep readiness in AEDT.'}
 (R/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
