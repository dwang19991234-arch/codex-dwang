"""Local geometry topology check; no HFSS solution is implied.
Requires numpy, scipy and matplotlib. Optional for the end user.
"""
import json
from pathlib import Path
import numpy as np
from scipy.ndimage import label
from matplotlib.path import Path as PolygonPath
from build_hfss import load_parameters,layout,evaluate,HERE

p=load_parameters(HERE/'parameters.json')
x=np.arange(np.floor(p['chip_left'])+0.5,p['chip_right'],1)
y=np.arange(-p['chip_half_y']+0.5,p['chip_half_y'],1)
xx,yy=np.meshgrid(x,y)
points=np.column_stack((xx.ravel(),yy.ravel()))
metal=np.ones(len(points),dtype=bool)
cuts,strips=layout()
for _,polygon in cuts:
    vertices=[(evaluate(a,p),evaluate(b,p)) for a,b in polygon]
    metal &= ~PolygonPath(vertices).contains_points(points)
for _,polygon in strips:
    vertices=[(evaluate(a,p),evaluate(b,p)) for a,b in polygon]
    metal |= PolygonPath(vertices).contains_points(points)
components,count=label(metal.reshape(xx.shape))
def at(a,b):return int(components[np.argmin(abs(y-b)),np.argmin(abs(x-a))])
left=at(-p['det_gap']/2-2,0)
right=at(p['det_gap']/2+2,0)
ground=at(250,250)
assert count==2, f'Expected signal island + ground, found {count} components'
assert left!=0 and right!=0 and left!=right, 'Port sides must be distinct conductors'
assert right==ground, 'Right feed must join the ground'
assert left==at(p['lead_x']+30,0), 'Choke and signal feed must remain continuous'
assert at(0,0)==0, 'Detector gap must be free of PEC'
report={'raster_pitch_um':1,'metal_connected_components':count,
        'port_conductors_distinct':True,'right_feed_connected_to_ground':True,
        'left_feed_connected_through_choke':True,'port_gap_clear':True,
        'limitation':'2D raster topology only, not AEDT Boolean or solver validation'}
(HERE/'output'/'local_geometry_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
