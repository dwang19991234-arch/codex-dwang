"""Approximate paper Fig. 2d. Units: um, GHz, ohm; not an author model.

Run --dry-run without AEDT to validate parameters and draw the shared geometry.
Default builds a new project; --solve additionally requests the HFSS solution.
"""
import argparse
import ast
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
DERIVED = {
    'choke_n': '10',
    'taper_x': '-slot_D/2-slot_W/2-taper_L',
    'choke_x': 'taper_x-choke_n*choke_L',
    'lead_x': 'choke_x-lead_L',
    'chip_left': 'lead_x-100',
    'corridor_half': 'low_W/2+gap',
}
DIMENSIONLESS = {'epsilon_si', 'sigma_si', 'port_ohm', 'choke_n'}


def evaluate(expr, values):
    """Arithmetic only; never execute expressions supplied in configuration."""
    node = ast.parse(str(expr), mode='eval').body
    def walk(n):
        if isinstance(n, ast.Constant) and type(n.value) in (int, float):
            return float(n.value)
        if isinstance(n, ast.Name):
            return values[n.id]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.USub, ast.UAdd)):
            return -walk(n.operand) if isinstance(n.op, ast.USub) else walk(n.operand)
        if isinstance(n, ast.BinOp):
            a, b = walk(n.left), walk(n.right)
            if isinstance(n.op, ast.Add): return a+b
            if isinstance(n.op, ast.Sub): return a-b
            if isinstance(n.op, ast.Mult): return a*b
            if isinstance(n.op, ast.Div): return a/b
        raise ValueError('Unsupported geometry expression: ' + str(expr))
    return walk(node)


def load_parameters(path):
    p = json.loads(Path(path).read_text(encoding='utf-8'))
    for k, v in p.items():
        if type(v) not in (int, float) or not math.isfinite(v) or v <= 0:
            raise ValueError(f'{k} must be a finite positive number')
    for k, expr in DERIVED.items(): p[k] = evaluate(expr, p)
    assert p['slot_L'] > 2*p['gap'] + p['feed_W']
    assert p['slot_D'] > p['slot_W'] + p['det_gap']
    assert p['corridor_half'] > p['high_W']/2
    assert p['slot_L']/2 < p['chip_half_y']
    assert p['margin'] >= 750, 'At 100 GHz keep >=lambda0/4 air clearance'
    assert p['air_H'] >= 750 and p['si_H'] >= 750/math.sqrt(p['epsilon_si'])
    return p


def rectangle(x0, y0, x1, y1):
    return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]


def layout():
    """Symbolic polygons used by both the preview and the AEDT geometry."""
    cuts = []
    strips = []
    cuts.append(('LeadClearance', rectangle('lead_x-20', '-lead_W/2-lead_gap',
                                          'choke_x', 'lead_W/2+lead_gap')))
    cuts.append(('ChokeClearance', rectangle('choke_x','-corridor_half',
                                            'taper_x','corridor_half')))
    cuts.append(('TaperClearance', [('taper_x','-corridor_half'),
        ('-slot_D/2-slot_W/2','-feed_W/2-gap'),
        ('-slot_D/2-slot_W/2','feed_W/2+gap'),('taper_x','corridor_half')]))
    cuts.append(('FeedClearance', rectangle('-slot_D/2-slot_W/2','-feed_W/2-gap',
                                            'slot_D/2+slot_W/2','feed_W/2+gap')))
    for side in [-1,1]:
        xc = f'({side}*slot_D/2)'
        cuts.append((f'Slot{side}_upper', rectangle(xc+'-slot_W/2','feed_W/2',
                                                   xc+'+slot_W/2','slot_L/2')))
        cuts.append((f'Slot{side}_lower', rectangle(xc+'-slot_W/2','-slot_L/2',
                                                   xc+'+slot_W/2','-feed_W/2')))
    strips.append(('Lead', rectangle('lead_x','-lead_W/2','choke_x','lead_W/2')))
    for i in range(10):
        w = 'high_W' if i % 2 == 0 else 'low_W'
        strips.append((f'Choke_{i+1}', rectangle(f'choke_x+{i}*choke_L',f'-{w}/2',
                                        f'choke_x+{i+1}*choke_L',f'{w}/2')))
    strips.append(('SignalTaper', [('taper_x','-low_W/2'),
        ('-slot_D/2-slot_W/2','-feed_W/2'),
        ('-slot_D/2-slot_W/2','feed_W/2'),('taper_x','low_W/2')]))
    strips.append(('FeedLeft', rectangle('-slot_D/2-slot_W/2','-feed_W/2',
                                        '-det_gap/2','feed_W/2')))
    strips.append(('FeedRight', rectangle('det_gap/2','-feed_W/2',
                                         'slot_D/2+slot_W/2','feed_W/2')))
    return cuts, strips


def preview(p, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon
    cuts, strips = layout()
    fig, axes = plt.subplots(2,1,figsize=(12,8),gridspec_kw={'height_ratios':[1,1]})
    ground = rectangle('chip_left','-chip_half_y','chip_right','chip_half_y')
    for ax in axes:
        for poly, color in [(ground,'#dca62e')]+[(v,'#344255') for _,v in cuts]+[(v,'#dca62e') for _,v in strips]:
            ax.add_patch(Polygon([(evaluate(x,p),evaluate(y,p)) for x,y in poly],color=color,lw=0))
        ax.add_patch(Polygon([(-p['det_gap']/2,-p['feed_W']/2),
                    (p['det_gap']/2,-p['feed_W']/2),(p['det_gap']/2,p['feed_W']/2),
                    (-p['det_gap']/2,p['feed_W']/2)],color='#db3e51',lw=0))
        ax.set_aspect('equal'); ax.set_xlabel('x (um)');ax.set_ylabel('y (um)')
    axes[0].set_xlim(p['chip_left']-30,p['chip_right']+30)
    axes[0].set_ylim(-p['chip_half_y']-30,p['chip_half_y']+30)
    axes[0].set_title('Approximate layout: PEC metal (gold), openings (dark), port (red)')
    axes[1].set_xlim(-240,180);axes[1].set_ylim(-180,180)
    axes[1].set_title('Double-slot / detector detail; dimensions estimated from Fig. 1a')
    axes[1].annotate('1 kohm reference port',xy=(0,0),xytext=(40,60),
                      arrowprops={'arrowstyle':'->'})
    fig.tight_layout();fig.savefig(out/'layout.png',dpi=180);plt.close(fig)
    (out/'resolved_parameters.json').write_text(json.dumps(p,indent=2),encoding='utf-8')


def require(result, operation):
    if result is False or result is None:
        raise RuntimeError('AEDT operation failed: '+operation)
    return result


def build(args, p, out):
    # Import only after dry-run, so the preview needs no AEDT installation.
    from ansys.aedt.core import Hfss
    project = (out/'graphene_double_slot.aedt').resolve()
    if project.exists():
        raise FileExistsError(f'Use a new --output directory; refusing to overwrite {project}')
    hfss = Hfss(project=str(project),design='Fig2d_approx',solution_type='Modal',
                version=args.aedt_version,non_graphical=args.headless,
                new_desktop=True,close_on_exit=False)
    try:
        hfss.modeler.model_units = 'um'
        originals = json.loads(Path(args.parameters).read_text(encoding='utf-8'))
        for k,v in originals.items():
            hfss[k] = str(v) if k in DIMENSIONLESS else f'{v}um'
        for k,expr in DERIVED.items(): hfss[k] = expr
        material = hfss.materials.add_material('Si_100ohm_cm_approx')
        material.permittivity = p['epsilon_si']
        material.conductivity = p['sigma_si']
        material.dielectric_loss_tangent = 0  # sigma already accounts for conduction
        x0='chip_left-margin';y0='-chip_half_y-margin'
        dx='chip_right-chip_left+2*margin';dy='2*(chip_half_y+margin)'
        air = require(hfss.modeler.create_box([x0,y0,0],[dx,dy,'air_H'],
                                             name='AirDomain',material='vacuum'),'air box')
        si = require(hfss.modeler.create_box([x0,y0,'-si_H'],[dx,dy,'si_H'],
                    name='SiliconHalfSpaceApprox',material=material.name),'silicon box')
        def sheet(name, points):
            return require(hfss.modeler.create_polyline([[x,y,0] for x,y in points],
                cover_surface=True,close_surface=True,name=name),'sheet '+name)
        ground = sheet('Ground',rectangle('chip_left','-chip_half_y','chip_right','chip_half_y'))
        cuts, strips = layout()
        # Sequential subtraction handles intersecting/overlapping slot openings.
        for name,poly in cuts:
            void = sheet(name,poly)
            require(hfss.modeler.subtract(ground.name,void.name,keep_originals=False),'cut '+name)
        conductors = {name:sheet(name,poly).name for name,poly in strips}
        # Keep the two disconnected port conductors as distinct modeler objects.
        # Within each conductor, adjacent sheets share exact edge expressions.
        require(hfss.modeler.unite([ground.name,conductors['FeedRight']]),'unite ground')
        signal = [name for key,name in conductors.items() if key != 'FeedRight']
        require(hfss.modeler.unite(signal),'unite signal island')
        metal = [ground.name,signal[0]]
        require(hfss.assign_perfecte_to_sheets(metal,name='Metal_PEC'),'PEC boundary')
        port = sheet('GraphenePort',rectangle('-det_gap/2','-feed_W/2','det_gap/2','feed_W/2'))
        port_boundary = require(hfss.lumped_port(port.name,create_port_sheet=False,
                    integration_line=[[-p['det_gap']/2,0,0],[p['det_gap']/2,0,0]],
                    impedance=p['port_ohm'],name='Graphene',renormalize=True,
                    deembed=False),'lumped port')
        # The helper appends model units to numeric coordinates. Replace these
        # with expressions after creation so det_gap changes also move the line.
        mode = port_boundary.props['Modes']['Mode1']
        mode['IntLine']['Start'] = ['-det_gap/2','0um','0um']
        mode['IntLine']['End'] = ['det_gap/2','0um','0um']
        mode['RenormImp'] = 'port_ohm*1ohm'
        port_boundary.props['Impedance'] = 'port_ohm*1ohm'
        require(port_boundary.update(),'parametric port')
        # The port replaces graphene for input matching. No parallel 1 kohm resistor.
        # Exterior faces only: never assign radiation to the internal z=0 interface.
        faces = [f.id for obj in [air,si] for f in obj.faces if abs(f.center[2]) > 1e-6]
        if len(faces) != 10:
            raise RuntimeError(f'Expected ten exterior box faces; got {len(faces)}')
        require(hfss.assign_radiation_boundary_to_faces(faces,name='OuterRadiation'),
                'radiation boundaries')
        require(hfss.mesh.assign_length_mesh(metal,inside_selection=False,
                  maximum_length='12um',maximum_elements=None,name='MetalEdges'),'metal mesh')
        require(hfss.mesh.assign_length_mesh(port.name,inside_selection=False,
                  maximum_length='2um',maximum_elements=None,name='PortMesh'),'port mesh')
        setup = require(hfss.create_setup('Setup130'),'adaptive setup')
        setup.props['Frequency']='130GHz'
        setup.props['MaxDeltaS']=0.02
        setup.props['MaximumPasses']=15
        setup.props['MinimumPasses']=3
        setup.props['MinimumConvergedPasses']=2
        require(setup.update(),'update setup')
        require(setup.enable_adaptive_setup_multifrequency([100,130,220],max_delta_s=0.02),
                'multi-frequency adaptation')
        sweep = require(hfss.create_linear_count_sweep(setup='Setup130',units='GHz',
            start_frequency=100,stop_frequency=220,num_of_freq_points=241,
            name='Sweep100_220',sweep_type='Interpolating',save_fields=False,
            interpolation_tol=0.3,interpolation_max_solutions=150),'broadband sweep')
        # Additional direct frequency solves check the interpolated sweep.
        require(hfss.create_linear_count_sweep(setup='Setup130',units='GHz',
            start_frequency=100,stop_frequency=220,num_of_freq_points=13,
            name='CheckDiscrete',sweep_type='Discrete',save_fields=False),'discrete check')
        require(hfss.save_project(),'save project')
        messages, valid = hfss.validate_full_design(output_dir=str(out),ports=1)
        (out/'validation.json').write_text(json.dumps({'valid':bool(valid),'messages':messages},
                                            indent=2,default=str),encoding='utf-8')
        if not valid: raise RuntimeError('HFSS validation failed; see validation.json and AEDT logs')
        if args.solve:
            require(hfss.analyze_setup('Setup130',cores=args.cores),'solve')
            export_results(hfss,out,'Sweep100_220')
            export_results(hfss,out,'CheckDiscrete')
            require(hfss.export_convergence('Setup130',output_file=str(out/'convergence.txt')),
                    'export convergence')
            hfss.save_project()
        (out/'status.json').write_text(json.dumps({
            'project_created':True,'solver_requested':args.solve,
            'note':'Inspect adaptive convergence in HFSS; successful API calls do not establish convergence.'},
            indent=2),encoding='utf-8')
        print('Saved:',project)
    finally:
        # Leave interactive AEDT open for inspection. Headless sessions must release their license.
        if args.headless: hfss.release_desktop(close_projects=True,close_desktop=True)


def export_results(hfss,out,sweep):
    expression='S(Graphene,Graphene)'
    data = require(hfss.post.get_solution_data(expressions=[expression],
        setup_sweep_name='Setup130 : '+sweep,primary_sweep_variable='Freq'), 'read S11')
    freq = list(data.primary_sweep_values)
    unit = data.units_sweeps['Freq']
    multiplier={'Hz':1e-9,'kHz':1e-6,'MHz':1e-3,'GHz':1,'THz':1e3}[unit]
    re,im = data.data_real(expression),data.data_imag(expression)
    if not freq or len(freq)!=len(re) or len(freq)!=len(im):
        raise RuntimeError('Empty or inconsistent solver result')
    r = float(hfss['port_ohm'])
    with (out/(sweep+'.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f)
        writer.writerow(['frequency_GHz','S11_real','S11_imag','S11_dB',
                         'Zin_real_ohm','Zin_imag_ohm','accepted_fraction_1port'])
        for f0,a,b in zip(freq,re,im):
            s=complex(a,b)
            if not math.isfinite(abs(s)) or abs(1-s)<1e-14:
                raise RuntimeError('Invalid or singular S11 data')
            z=r*(1+s)/(1-s)
            # This is net accepted power fraction; it is NOT radiation efficiency.
            writer.writerow([f0*multiplier,a,b,20*math.log10(max(abs(s),1e-15)),
                             z.real,z.imag,1-abs(s)**2])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--parameters',default=str(HERE/'parameters.json'))
    parser.add_argument('--output',default=str(HERE/'output'))
    parser.add_argument('--aedt-version',default=None,help='e.g. 2024.2; default detects installed AEDT')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--solve',action='store_true')
    parser.add_argument('--headless',action='store_true')
    parser.add_argument('--cores',type=int,default=4)
    args=parser.parse_args()
    p=load_parameters(args.parameters)
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    preview(p,out)
    if args.dry_run: print('Parameter checks and layout generated; no HFSS session or solution.');return
    build(args,p,out)

if __name__=='__main__': main()
