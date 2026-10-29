"""Check the 2D topology without AEDT. Requires numpy/scipy/matplotlib."""
import ast,json,os,re,warnings
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR','/tmp/paper-layout-mpl')
import numpy as np
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as ShapePath
from matplotlib.patches import Polygon
ROOT=Path(__file__).resolve().parent

def load_geometry(file):
 tree=ast.parse(file.read_text())
 keep=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id=='P' for v in n.targets)
       or isinstance(n,ast.FunctionDef) and n.name in ('rectangle','core_geometry','geometry','paper_outline')]
 ns={};exec(compile(ast.Module(body=keep,type_ignores=[]),str(file),'exec'),ns)
 return ns

def main():
 ns=load_geometry(ROOT/'build_paper_layout_2021.py');p=ns['P']
 left,cuts,strips=ns['geometry'](p);outline=ns['paper_outline'](p)[3]
 names=[n for n,v in cuts+strips]
 assert len(names)==len(set(names)) and all(re.fullmatch('[A-Za-z][A-Za-z0-9_]*',n) for n in names)
 x=np.arange(np.floor(left)+.5,p['chip_right'],1.)
 y=np.arange(-p['chip_half_y']+.5,p['chip_half_y'],1.)
 xx,yy=np.meshgrid(x,y);points=np.column_stack((xx.ravel(),yy.ravel()))
 mask=ShapePath(outline).contains_points(points)
 for n,v in cuts: mask &= ~ShapePath(v).contains_points(points)
 for n,v in strips: mask |= ShapePath(v).contains_points(points)
 components,count=label(mask.reshape(xx.shape))
 def at(a,b):return int(components[np.argmin(abs(y-b)),np.argmin(abs(x-a))])
 assert count==2, count
 assert at(0,0)==0
 assert at(-p['det_gap']/2-2,0)!=0
 assert at(-p['det_gap']/2-2,0)==at(left+50,0)
 assert at(p['det_gap']/2+2,0)==at(300,200)
 assert at(-p['det_gap']/2-2,0)!=at(300,200)
 # At the left edge the signal pad is separated from the G pads by exposed substrate.
 assert at(left+5,120)==0 and at(left+5,-120)==0
 assert at(left+5,300)==at(left+5,-300)==at(300,200)
 report={'2D_components':count,'left_GSG_pad_gaps_open':True,
         'signal_continuity':True,'port_gap_clear':True,'ground_return_connected':True,
         'oxide_thickness_um':p['oxide_t'],'radiation_faces_expected':14,
         'HFSS_model_build':'not_run','HFSS_solution':'not_run',
         'scope':'1 um raster geometry check, not electromagnetic validation'}
 (ROOT/'geometry_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 fig,ax=plt.subplots(figsize=(12,5))
 ax.add_patch(Polygon(outline,facecolor='#efb52c',edgecolor='#875900',lw=.7))
 for n,v in cuts:ax.add_patch(Polygon(v,facecolor='white',edgecolor='none'))
 for n,v in strips:ax.add_patch(Polygon(v,facecolor='#efb52c',edgecolor='none'))
 ax.add_patch(Polygon(ns['rectangle'](-p['det_gap']/2,-p['feed_W']/2,p['det_gap']/2,p['feed_W']/2),color='#a82a63'))
 ax.set(xlim=(left-50,p['chip_right']+50),ylim=(-600,600),xlabel='x (um)',ylabel='y (um)',
        title='Revised finite G-S-G layout: photo-derived geometry, not verified reproduction')
 ax.set_aspect('equal');fig.tight_layout();fig.savefig(ROOT/'layout_preview.png',dpi=180);plt.close(fig)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
