# -*- coding: utf-8 -*-
# Run INSIDE HFSS 2021 R1: Tools > Run Script. No PyAEDT or pip required.
# Estimated geometry, not an author model. Build only; does not start a solve.
import os
import time
import traceback
import re
import ScriptEnv

PARAMETERS = {'air_H': 1000.0,
 'chip_half_y': 400.0,
 'chip_right': 350.0,
 'choke_L': 120.0,
 'det_gap': 6.0,
 'epsilon_si': 11.7,
 'feed_W': 12.0,
 'gap': 6.0,
 'high_W': 12.0,
 'lead_L': 250.0,
 'lead_W': 60.0,
 'lead_gap': 31.0,
 'low_W': 110.0,
 'margin': 900.0,
 'port_ohm': 1000.0,
 'si_H': 1000.0,
 'sigma_si': 1.0,
 'slot_D': 125.0,
 'slot_L': 260.0,
 'slot_W': 12.0,
 'taper_L': 130.0}

DERIVED = {'chip_left': 'lead_x-100',
 'choke_n': '10',
 'choke_x': 'taper_x-choke_n*choke_L',
 'corridor_half': 'low_W/2+gap',
 'lead_x': 'choke_x-lead_L',
 'taper_x': '-slot_D/2-slot_W/2-taper_L'}

CUTS = [('LeadClearance',
  [('lead_x-20', '-lead_W/2-lead_gap'),
   ('choke_x', '-lead_W/2-lead_gap'),
   ('choke_x', 'lead_W/2+lead_gap'),
   ('lead_x-20', 'lead_W/2+lead_gap')]),
 ('ChokeClearance',
  [('choke_x', '-corridor_half'),
   ('taper_x', '-corridor_half'),
   ('taper_x', 'corridor_half'),
   ('choke_x', 'corridor_half')]),
 ('TaperClearance',
  [('taper_x', '-corridor_half'),
   ('-slot_D/2-slot_W/2', '-feed_W/2-gap'),
   ('-slot_D/2-slot_W/2', 'feed_W/2+gap'),
   ('taper_x', 'corridor_half')]),
 ('FeedClearance',
  [('-slot_D/2-slot_W/2', '-feed_W/2-gap'),
   ('slot_D/2+slot_W/2', '-feed_W/2-gap'),
   ('slot_D/2+slot_W/2', 'feed_W/2+gap'),
   ('-slot_D/2-slot_W/2', 'feed_W/2+gap')]),
 ('SlotNeg_upper',
  [('(-1*slot_D/2)-slot_W/2', 'feed_W/2'),
   ('(-1*slot_D/2)+slot_W/2', 'feed_W/2'),
   ('(-1*slot_D/2)+slot_W/2', 'slot_L/2'),
   ('(-1*slot_D/2)-slot_W/2', 'slot_L/2')]),
 ('SlotNeg_lower',
  [('(-1*slot_D/2)-slot_W/2', '-slot_L/2'),
   ('(-1*slot_D/2)+slot_W/2', '-slot_L/2'),
   ('(-1*slot_D/2)+slot_W/2', '-feed_W/2'),
   ('(-1*slot_D/2)-slot_W/2', '-feed_W/2')]),
 ('SlotPos_upper',
  [('(1*slot_D/2)-slot_W/2', 'feed_W/2'),
   ('(1*slot_D/2)+slot_W/2', 'feed_W/2'),
   ('(1*slot_D/2)+slot_W/2', 'slot_L/2'),
   ('(1*slot_D/2)-slot_W/2', 'slot_L/2')]),
 ('SlotPos_lower',
  [('(1*slot_D/2)-slot_W/2', '-slot_L/2'),
   ('(1*slot_D/2)+slot_W/2', '-slot_L/2'),
   ('(1*slot_D/2)+slot_W/2', '-feed_W/2'),
   ('(1*slot_D/2)-slot_W/2', '-feed_W/2')])]

STRIPS = [('Lead',
  [('lead_x', '-lead_W/2'),
   ('choke_x', '-lead_W/2'),
   ('choke_x', 'lead_W/2'),
   ('lead_x', 'lead_W/2')]),
 ('Choke_1',
  [('choke_x+0*choke_L', '-high_W/2'),
   ('choke_x+1*choke_L', '-high_W/2'),
   ('choke_x+1*choke_L', 'high_W/2'),
   ('choke_x+0*choke_L', 'high_W/2')]),
 ('Choke_2',
  [('choke_x+1*choke_L', '-low_W/2'),
   ('choke_x+2*choke_L', '-low_W/2'),
   ('choke_x+2*choke_L', 'low_W/2'),
   ('choke_x+1*choke_L', 'low_W/2')]),
 ('Choke_3',
  [('choke_x+2*choke_L', '-high_W/2'),
   ('choke_x+3*choke_L', '-high_W/2'),
   ('choke_x+3*choke_L', 'high_W/2'),
   ('choke_x+2*choke_L', 'high_W/2')]),
 ('Choke_4',
  [('choke_x+3*choke_L', '-low_W/2'),
   ('choke_x+4*choke_L', '-low_W/2'),
   ('choke_x+4*choke_L', 'low_W/2'),
   ('choke_x+3*choke_L', 'low_W/2')]),
 ('Choke_5',
  [('choke_x+4*choke_L', '-high_W/2'),
   ('choke_x+5*choke_L', '-high_W/2'),
   ('choke_x+5*choke_L', 'high_W/2'),
   ('choke_x+4*choke_L', 'high_W/2')]),
 ('Choke_6',
  [('choke_x+5*choke_L', '-low_W/2'),
   ('choke_x+6*choke_L', '-low_W/2'),
   ('choke_x+6*choke_L', 'low_W/2'),
   ('choke_x+5*choke_L', 'low_W/2')]),
 ('Choke_7',
  [('choke_x+6*choke_L', '-high_W/2'),
   ('choke_x+7*choke_L', '-high_W/2'),
   ('choke_x+7*choke_L', 'high_W/2'),
   ('choke_x+6*choke_L', 'high_W/2')]),
 ('Choke_8',
  [('choke_x+7*choke_L', '-low_W/2'),
   ('choke_x+8*choke_L', '-low_W/2'),
   ('choke_x+8*choke_L', 'low_W/2'),
   ('choke_x+7*choke_L', 'low_W/2')]),
 ('Choke_9',
  [('choke_x+8*choke_L', '-high_W/2'),
   ('choke_x+9*choke_L', '-high_W/2'),
   ('choke_x+9*choke_L', 'high_W/2'),
   ('choke_x+8*choke_L', 'high_W/2')]),
 ('Choke_10',
  [('choke_x+9*choke_L', '-low_W/2'),
   ('choke_x+10*choke_L', '-low_W/2'),
   ('choke_x+10*choke_L', 'low_W/2'),
   ('choke_x+9*choke_L', 'low_W/2')]),
 ('SignalTaper',
  [('taper_x', '-low_W/2'),
   ('-slot_D/2-slot_W/2', '-feed_W/2'),
   ('-slot_D/2-slot_W/2', 'feed_W/2'),
   ('taper_x', 'low_W/2')]),
 ('FeedLeft',
  [('-slot_D/2-slot_W/2', '-feed_W/2'),
   ('-det_gap/2', '-feed_W/2'),
   ('-det_gap/2', 'feed_W/2'),
   ('-slot_D/2-slot_W/2', 'feed_W/2')]),
 ('FeedRight',
  [('det_gap/2', '-feed_W/2'),
   ('slot_D/2+slot_W/2', '-feed_W/2'),
   ('slot_D/2+slot_W/2', 'feed_W/2'),
   ('det_gap/2', 'feed_W/2')])]



def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def attributes(name, solve_inside=True, material='vacuum'):
    if not re.match(r'^[A-Za-z][A-Za-z0-9_]*$', name):
        raise ValueError('Invalid AEDT object name: ' + name)
    return ['NAME:Attributes', 'Name:=', name, 'Flags:=', '',
            'Color:=', '(220 165 45)', 'Transparency:=', 0,
            'PartCoordinateSystem:=', 'Global', 'UDMId:=', '',
            'MaterialValue:=', '"' + material + '"',
            'SolveInside:=', solve_inside]


def poly(editor, name, vertices):
    points = list(vertices) + [vertices[0]]
    point_args = ['NAME:PolylinePoints']
    for x, y in points:
        point_args.append(['NAME:PLPoint', 'X:=', str(x), 'Y:=', str(y), 'Z:=', '0um'])
    segments = ['NAME:PolylineSegments']
    for i in range(len(vertices)):
        segments.append(['NAME:PLSegment', 'SegmentType:=', 'Line',
                         'StartIndex:=', i, 'NoOfPoints:=', 2])
    editor.CreatePolyline(
        ['NAME:PolylineParameters', 'IsPolylineCovered:=', True,
         'IsPolylineClosed:=', True, point_args, segments,
         ['NAME:PolylineXSection', 'XSectionType:=', 'None',
          'XSectionOrient:=', 'Auto', 'XSectionWidth:=', '0um',
          'XSectionTopWidth:=', '0um', 'XSectionHeight:=', '0um',
          'XSectionNumSegments:=', '0', 'XSectionBendType:=', 'Corner']],
        # AEDT 2021 R1 rejects vacuum objects with SolveInside=False,
        # including the temporary sheets used for Boolean subtraction.
        # The conductor sheets receive explicit Perfect E boundaries below;
        # the port sheet must remain a dielectric/interface sheet.
        attributes(name, True))


def box(editor, name, xyz, sizes, material):
    editor.CreateBox(
        ['NAME:BoxParameters', 'XPosition:=', xyz[0], 'YPosition:=', xyz[1],
         'ZPosition:=', xyz[2], 'XSize:=', sizes[0], 'YSize:=', sizes[1],
         'ZSize:=', sizes[2]], attributes(name, True, material))


def unite(editor, names):
    editor.Unite(['NAME:Selections', 'Selections:=', ','.join(names)],
                 ['NAME:UniteParameters', 'KeepOriginals:=', False])


def length_mesh(mesh, name, objects, length):
    mesh.AssignLengthOp(['NAME:' + name, 'RefineInside:=', False,
        'Enabled:=', True, 'Objects:=', objects, 'RestrictElem:=', False,
        'NumMaxElem:=', '1000', 'RestrictLength:=', True, 'MaxLength:=', length])


def message(desktop, text, error=False):
    desktop.AddMessage('', '', 2 if error else 0, text)


def run():
    ScriptEnv.Initialize('Ansoft.ElectronicsDesktop')
    desktop = oDesktop
    desktop.RestoreWindow()
    base = os.path.dirname(os.path.abspath(__file__))
    run_dir = os.path.join(base, 'run_' + time.strftime('%Y%m%d_%H%M%S'))
    if os.path.exists(run_dir):
        raise RuntimeError('Output already exists. Wait a second and run again.')
    os.makedirs(run_dir)
    log_path = os.path.join(run_dir, 'build_log.txt')
    log = open(log_path, 'w')
    def stage(text):
        log.write(text + '\n')
        log.flush()
        message(desktop, text)
    try:
        stage('Starting approximate Fig. 2d model. No solve will run.')
        stage('AEDT version: ' + str(desktop.GetVersion()))
        project = desktop.NewProject()
        project.InsertDesign('HFSS', 'Fig2d_approx_2021', 'DrivenModal', '')
        design = project.SetActiveDesign('Fig2d_approx_2021')
        editor = design.SetActiveEditor('3D Modeler')
        editor.SetModelUnits(['NAME:Units Parameter', 'Units:=', 'um', 'Rescale:=', False])
        properties = ['NAME:NewProps']
        for name in sorted(PARAMETERS):
            value = str(PARAMETERS[name])
            if name not in ('epsilon_si', 'sigma_si', 'port_ohm'):
                value += 'um'
            properties.append(['NAME:' + name, 'PropType:=', 'VariableProp',
                               'UserDef:=', True, 'Value:=', value])
        # Dependencies are created in explicit order for the native AEDT parser.
        design.ChangeProperty(['NAME:AllTabs', ['NAME:LocalVariableTab',
            ['NAME:PropServers', 'LocalVariables'], properties]])
        for name in ('choke_n', 'taper_x', 'choke_x', 'lead_x', 'chip_left', 'corridor_half'):
            design.ChangeProperty(['NAME:AllTabs', ['NAME:LocalVariableTab',
                ['NAME:PropServers', 'LocalVariables'], ['NAME:NewProps',
                ['NAME:' + name, 'PropType:=', 'VariableProp', 'UserDef:=', True,
                 'Value:=', DERIVED[name]]]]])
        stage('Variables created.')
        manager = project.GetDefinitionManager()
        manager.AddMaterial(['NAME:Si_100ohm_cm_approx',
            'CoordinateSystemType:=', 'Cartesian', 'BulkOrSurfaceType:=', 1,
            ['NAME:PhysicsTypes', 'set:=', ['Electromagnetic']],
            'permittivity:=', str(PARAMETERS['epsilon_si']),
            'conductivity:=', str(PARAMETERS['sigma_si']),
            'dielectric_loss_tangent:=', '0'])
        size = ['chip_right-chip_left+2*margin', '2*(chip_half_y+margin)']
        box(editor, 'AirDomain', ['chip_left-margin', '-chip_half_y-margin', '0um'],
            size + ['air_H'], 'vacuum')
        box(editor, 'SiliconHalfSpaceApprox',
            ['chip_left-margin', '-chip_half_y-margin', '-si_H'],
            size + ['si_H'], 'Si_100ohm_cm_approx')
        poly(editor, 'Ground', rect('chip_left', '-chip_half_y', 'chip_right', 'chip_half_y'))
        for name, vertices in CUTS:
            poly(editor, name, vertices)
            editor.Subtract(['NAME:Selections', 'Blank Parts:=', 'Ground', 'Tool Parts:=', name],
                            ['NAME:SubtractParameters', 'KeepOriginals:=', False])
        for name, vertices in STRIPS:
            poly(editor, name, vertices)
        unite(editor, ['Ground', 'FeedRight'])
        signal = [name for name, vertices in STRIPS if name != 'FeedRight']
        unite(editor, signal)
        metal = ['Ground', signal[0]]
        boundary = design.GetModule('BoundarySetup')
        boundary.AssignPerfectE(['NAME:Metal_PEC', 'Objects:=', metal,
                                'InfGroundPlane:=', False])
        stage('PEC geometry created: two separate port conductors.')
        poly(editor, 'GraphenePort', rect('-det_gap/2', '-feed_W/2', 'det_gap/2', 'feed_W/2'))
        boundary.AssignLumpedPort(['NAME:Graphene', 'Objects:=', ['GraphenePort'],
            'RenormalizeAllTerminals:=', True, 'DoDeembed:=', False,
            ['NAME:Modes', ['NAME:Mode1', 'ModeNum:=', 1, 'UseIntLine:=', True,
                ['NAME:IntLine', 'Start:=', ['-det_gap/2', '0um', '0um'],
                 'End:=', ['det_gap/2', '0um', '0um']],
                'AlignmentGroup:=', 0, 'CharImp:=', 'Zpi', 'RenormImp:=', 'port_ohm*1ohm']],
            'ShowReporterFilter:=', False, 'ReporterFilter:=', [True],
            'Impedance:=', 'port_ohm*1ohm'])
        exterior_faces = []
        for obj in ('AirDomain', 'SiliconHalfSpaceApprox'):
            for face in editor.GetFaceIDs(obj):
                # Native GetFaceCenter returns coordinates in model units.
                center = editor.GetFaceCenter(int(face))
                if abs(float(center[2])) > 1e-8:
                    exterior_faces.append(int(face))
        if len(exterior_faces) != 10:
            raise RuntimeError('Expected ten exterior box faces, got ' + str(len(exterior_faces)))
        boundary.AssignRadiation(['NAME:OuterRadiation', 'Faces:=', exterior_faces,
                                 'IsFssReference:=', False, 'IsForPML:=', False])
        stage('Lumped port and exterior radiation faces assigned.')
        mesh = design.GetModule('MeshSetup')
        length_mesh(mesh, 'MetalEdges', metal, '12um')
        length_mesh(mesh, 'PortMesh', ['GraphenePort'], '2um')
        analysis = design.GetModule('AnalysisSetup')
        # Single-frequency adaptation at band maximum uses the conservative,
        # established native setup format available in AEDT 2021 R1.
        analysis.InsertSetup('HfssDriven', ['NAME:Setup220', 'Frequency:=', '220GHz',
            'PortsOnly:=', False, 'MaxDeltaS:=', 0.02, 'UseMatrixConv:=', False,
            'MaximumPasses:=', 15, 'MinimumPasses:=', 3, 'MinimumConvergedPasses:=', 2,
            'PercentRefinement:=', 30, 'IsEnabled:=', True, 'BasisOrder:=', 1,
            'DoLambdaRefine:=', True, 'DoMaterialLambda:=', True,
            'SetLambdaTarget:=', False, 'Target:=', 0.3333,
            'UseMaxTetIncrease:=', False, 'PortAccuracy:=', 2,
            'UseABCOnPort:=', False, 'SetPortMinMaxTri:=', False])
        analysis.InsertFrequencySweep('Setup220', ['NAME:Sweep100_220',
            'IsEnabled:=', True, 'RangeType:=', 'LinearCount',
            'RangeStart:=', '100GHz', 'RangeEnd:=', '220GHz', 'RangeCount:=', 241,
            'Type:=', 'Interpolating', 'SaveFields:=', False, 'SaveRadFields:=', False,
            'InterpTolerance:=', 0.3, 'InterpMaxSolns:=', 150,
            'InterpMinSolns:=', 0, 'InterpMinSubranges:=', 1,
            'InterpUseS:=', True, 'InterpUsePortImped:=', False,
            'InterpUsePropConst:=', True])
        analysis.InsertFrequencySweep('Setup220', ['NAME:CheckDiscrete',
            'IsEnabled:=', True, 'RangeType:=', 'LinearCount',
            'RangeStart:=', '100GHz', 'RangeEnd:=', '220GHz', 'RangeCount:=', 13,
            'Type:=', 'Discrete', 'SaveFields:=', False, 'SaveRadFields:=', False])
        stage('Mesh and 100-220 GHz sweeps configured; adapting at 220 GHz.')
        project_path = os.path.join(run_dir, 'Graphene_Fig2d_2021.aedt')
        project.SaveAs(project_path, True)
        stage('Project saved: ' + project_path)
        validation = design.ValidateDesign(os.path.join(run_dir, 'validation.log'))
        stage('ValidateDesign returned: ' + str(validation))
        if validation != 1:
            raise RuntimeError('HFSS design validation did not pass. Inspect validation.log and Message Manager.')
        editor.FitAll()
        # Domains can obscure the sheets. Display transparency is cosmetic only.
        editor.ChangeProperty(['NAME:AllTabs', ['NAME:Geometry3DAttributeTab',
            ['NAME:PropServers', 'AirDomain', 'SiliconHalfSpaceApprox'],
            ['NAME:ChangedProps', ['NAME:Transparent', 'Value:=', 0.9]]]])
        project.Save()
        stage('BUILD COMPLETE. Inspect geometry, then run solve_export_2021.py in the same design.')
        stage('Approximate model only. No full-wave simulation has run.')
    except Exception:
        detail = traceback.format_exc()
        log.write(detail)
        log.flush()
        message(desktop, 'Build failed. See ' + log_path + '\n' + detail, True)
        raise
    finally:
        log.close()


run()
