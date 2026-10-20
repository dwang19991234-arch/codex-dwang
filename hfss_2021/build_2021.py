# -*- coding: utf-8 -*-
# Run inside HFSS 2021 R1: Tools > Run Script.
# Builds a NEW approximate model. Does not start a solve.
import os
import time
import traceback
import ScriptEnv

P = {
    'slot_L': 260.0, 'slot_W': 12.0, 'slot_D': 125.0,
    'feed_W': 12.0, 'gap': 6.0, 'det_gap': 6.0,
    'choke_L': 120.0, 'low_W': 110.0, 'high_W': 12.0,
    'taper_L': 130.0, 'lead_L': 250.0,
    'lead_W': 60.0, 'lead_gap': 31.0,
    'chip_right': 350.0, 'chip_half_y': 400.0,
    'margin': 900.0, 'air_H': 1000.0, 'si_H': 1000.0,
    'epsilon_si': 11.7, 'sigma_si': 1.0, 'port_ohm': 1000.0
}


def u(value):
    return ('%.15g' % float(value)) + 'um'


def rectangle(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def geometry(p):
    left_slot = -p['slot_D']/2 - p['slot_W']/2
    right_slot = p['slot_D']/2 + p['slot_W']/2
    taper = left_slot - p['taper_L']
    choke = taper - 10*p['choke_L']
    lead = choke - p['lead_L']
    chip_left = lead - 100
    outer = p['low_W']/2 + p['gap']
    inner = p['feed_W']/2 + p['gap']
    cuts = [
        ('LeadClearance', rectangle(lead-20, -p['lead_W']/2-p['lead_gap'],
                                    choke, p['lead_W']/2+p['lead_gap'])),
        ('ChokeClearance', rectangle(choke, -outer, taper, outer)),
        ('TaperClearance', [(taper,-outer), (left_slot,-inner),
                            (left_slot,inner), (taper,outer)]),
        ('FeedClearance', rectangle(left_slot,-inner,right_slot,inner))
    ]
    for sign, name in [(-1,'SlotNeg'), (1,'SlotPos')]:
        x = sign*p['slot_D']/2
        cuts.append((name+'_upper', rectangle(x-p['slot_W']/2,p['feed_W']/2,
                                              x+p['slot_W']/2,p['slot_L']/2)))
        cuts.append((name+'_lower', rectangle(x-p['slot_W']/2,-p['slot_L']/2,
                                              x+p['slot_W']/2,-p['feed_W']/2)))
    strips = [('Lead', rectangle(lead,-p['lead_W']/2,choke,p['lead_W']/2))]
    for i in range(10):
        width = p['high_W'] if i % 2 == 0 else p['low_W']
        strips.append(('Choke_'+str(i+1), rectangle(choke+i*p['choke_L'],-width/2,
                                       choke+(i+1)*p['choke_L'],width/2)))
    strips.extend([
        ('SignalTaper', [(taper,-p['low_W']/2), (left_slot,-p['feed_W']/2),
                          (left_slot,p['feed_W']/2), (taper,p['low_W']/2)]),
        ('FeedLeft', rectangle(left_slot,-p['feed_W']/2,-p['det_gap']/2,p['feed_W']/2)),
        ('FeedRight', rectangle(p['det_gap']/2,-p['feed_W']/2,right_slot,p['feed_W']/2))
    ])
    return chip_left, cuts, strips


def attrs(name, material='vacuum', transparency=0):
    return ['NAME:Attributes', 'Name:=', name, 'Flags:=', '',
            'Color:=', '(220 165 45)', 'Transparency:=', transparency,
            'PartCoordinateSystem:=', 'Global', 'UDMId:=', '',
            'MaterialValue:=', '"'+material+'"', 'SolveInside:=', True]


def sheet(editor, name, vertices):
    points = ['NAME:PolylinePoints']
    for x,y in list(vertices)+[vertices[0]]:
        points.append(['NAME:PLPoint', 'X:=', u(x), 'Y:=', u(y), 'Z:=', '0um'])
    segments = ['NAME:PolylineSegments']
    for i in range(len(vertices)):
        segments.append(['NAME:PLSegment', 'SegmentType:=', 'Line',
                         'StartIndex:=', i, 'NoOfPoints:=', 2])
    editor.CreatePolyline([
        'NAME:PolylineParameters', 'IsPolylineCovered:=', True,
        'IsPolylineClosed:=', True, points, segments,
        ['NAME:PolylineXSection', 'XSectionType:=', 'None',
         'XSectionOrient:=', 'Auto', 'XSectionWidth:=', '0um',
         'XSectionTopWidth:=', '0um', 'XSectionHeight:=', '0um',
         'XSectionNumSegments:=', '0', 'XSectionBendType:=', 'Corner']], attrs(name))


def box(editor, name, origin, size, material):
    editor.CreateBox(['NAME:BoxParameters',
        'XPosition:=',u(origin[0]), 'YPosition:=',u(origin[1]), 'ZPosition:=',u(origin[2]),
        'XSize:=',u(size[0]), 'YSize:=',u(size[1]), 'ZSize:=',u(size[2])],
        attrs(name,material,0.95))


def unite(editor, names):
    editor.Unite(['NAME:Selections','Selections:=',','.join(names)],
                 ['NAME:UniteParameters','KeepOriginals:=',False])


def main():
    desktop = oDesktop
    base = os.path.dirname(os.path.abspath(__file__))
    output = os.path.join(base,'run_'+time.strftime('%Y%m%d_%H%M%S'))
    os.makedirs(output)
    log = open(os.path.join(output,'build_log.txt'),'w')
    def stage(text):
        log.write(text+'\n')
        log.flush()
        desktop.AddMessage('','',0,text)
    try:
        for key,value in P.items():
            if value <= 0:
                raise ValueError('Parameter must be positive: '+key)
        if P['slot_D'] <= P['slot_W']+P['det_gap']:
            raise ValueError('Slot spacing is too small for the port.')
        if P['slot_L'] <= P['feed_W'] or P['slot_L']/2 >= P['chip_half_y']:
            raise ValueError('Invalid slot length.')
        chip_left,cuts,strips = geometry(P)
        stage('Starting NEW model. No solve will run.')
        project = desktop.NewProject()
        project.InsertDesign('HFSS','Fig2d_approx_2021','DrivenModal','')
        design = project.SetActiveDesign('Fig2d_approx_2021')
        editor = design.SetActiveEditor('3D Modeler')
        editor.SetModelUnits(['NAME:Units Parameter','Units:=','um','Rescale:=',False])
        manager = project.GetDefinitionManager()
        manager.AddMaterial(['NAME:Si_100ohm_cm_approx',
            'CoordinateSystemType:=','Cartesian','BulkOrSurfaceType:=',1,
            ['NAME:PhysicsTypes','set:=',['Electromagnetic']],
            'permittivity:=',str(P['epsilon_si']),
            'conductivity:=',str(P['sigma_si']),'dielectric_loss_tangent:=','0'])
        x0 = chip_left-P['margin']
        y0 = -P['chip_half_y']-P['margin']
        dx = P['chip_right']-chip_left+2*P['margin']
        dy = 2*(P['chip_half_y']+P['margin'])
        box(editor,'AirDomain',[x0,y0,0],[dx,dy,P['air_H']],'vacuum')
        box(editor,'SiliconHalfSpaceApprox',[x0,y0,-P['si_H']],
            [dx,dy,P['si_H']],'Si_100ohm_cm_approx')
        sheet(editor,'Ground',rectangle(chip_left,-P['chip_half_y'],
                                        P['chip_right'],P['chip_half_y']))
        for name,vertices in cuts:
            sheet(editor,name,vertices)
            editor.Subtract(['NAME:Selections','Blank Parts:=','Ground','Tool Parts:=',name],
                            ['NAME:SubtractParameters','KeepOriginals:=',False])
        for name,vertices in strips:
            sheet(editor,name,vertices)
        unite(editor,['Ground','FeedRight'])
        unite(editor,[name for name,vertices in strips if name != 'FeedRight'])
        boundary = design.GetModule('BoundarySetup')
        boundary.AssignPerfectE(['NAME:Metal_PEC','Objects:=',['Ground','Lead'],
                                'InfGroundPlane:=',False])
        stage('PEC geometry created.')
        sheet(editor,'GraphenePort',rectangle(-P['det_gap']/2,-P['feed_W']/2,
                                              P['det_gap']/2,P['feed_W']/2))
        # Explicit numerical coordinates WITH units: no variable expressions.
        start = [u(-P['det_gap']/2),'0um','0um']
        end = [u(P['det_gap']/2),'0um','0um']
        impedance = ('%.15g' % P['port_ohm'])+'ohm'
        boundary.AssignLumpedPort(['NAME:Graphene','Objects:=',['GraphenePort'],
            'RenormalizeAllTerminals:=',True,'DoDeembed:=',False,
            ['NAME:Modes',['NAME:Mode1','ModeNum:=',1,'UseIntLine:=',True,
                ['NAME:IntLine','Start:=',start,'End:=',end],
                'AlignmentGroup:=',0,'CharImp:=','Zpi','RenormImp:=',impedance]],
            'ShowReporterFilter:=',False,'ReporterFilter:=',[True],'Impedance:=',impedance])
        stage('Port assigned: '+str(start)+' -> '+str(end))
        faces = []
        for name in ('AirDomain','SiliconHalfSpaceApprox'):
            for face in editor.GetFaceIDs(name):
                if abs(float(editor.GetFaceCenter(int(face))[2])) > 1e-8:
                    faces.append(int(face))
        if len(faces) != 10:
            raise RuntimeError('Expected ten exterior faces; got '+str(len(faces)))
        boundary.AssignRadiation(['NAME:OuterRadiation','Faces:=',faces,
                                 'IsFssReference:=',False,'IsForPML:=',False])
        mesh = design.GetModule('MeshSetup')
        for name,objects,length in [('MetalEdges',['Ground','Lead'],'12um'),
                                    ('PortMesh',['GraphenePort'],'2um')]:
            mesh.AssignLengthOp(['NAME:'+name,'RefineInside:=',False,'Enabled:=',True,
                'Objects:=',objects,'RestrictElem:=',False,'NumMaxElem:=','1000',
                'RestrictLength:=',True,'MaxLength:=',length])
        analysis = design.GetModule('AnalysisSetup')
        analysis.InsertSetup('HfssDriven',['NAME:Setup220','Frequency:=','220GHz',
            'PortsOnly:=',False,'MaxDeltaS:=',0.02,'UseMatrixConv:=',False,
            'MaximumPasses:=',15,'MinimumPasses:=',3,'MinimumConvergedPasses:=',2,
            'PercentRefinement:=',30,'IsEnabled:=',True,'BasisOrder:=',1,
            'DoLambdaRefine:=',True,'DoMaterialLambda:=',True,'SetLambdaTarget:=',False,
            'Target:=',0.3333,'UseMaxTetIncrease:=',False,'PortAccuracy:=',2,
            'UseABCOnPort:=',False,'SetPortMinMaxTri:=',False])
        for name,kind,count in [('Sweep100_220','Interpolating',241),
                                ('CheckDiscrete','Discrete',13)]:
            settings = ['NAME:'+name,'IsEnabled:=',True,'RangeType:=','LinearCount',
                'RangeStart:=','100GHz','RangeEnd:=','220GHz','RangeCount:=',count,
                'Type:=',kind,'SaveFields:=',False,'SaveRadFields:=',False]
            if kind == 'Interpolating':
                settings += ['InterpTolerance:=',0.3,'InterpMaxSolns:=',150,
                    'InterpMinSolns:=',0,'InterpMinSubranges:=',1,
                    'InterpUseS:=',True,'InterpUsePortImped:=',False,'InterpUsePropConst:=',True]
            analysis.InsertFrequencySweep('Setup220',settings)
        path = os.path.join(output,'Graphene_Fig2d_2021.aedt')
        project.SaveAs(path,True)
        stage('Saved: '+path)
        valid = design.ValidateDesign(os.path.join(output,'validation.log'))
        if valid != 1:
            raise RuntimeError('Validation failed; inspect validation.log.')
        editor.FitAll()
        stage('BUILD COMPLETE. No solve has run.')
    except Exception:
        detail = traceback.format_exc()
        log.write(detail)
        desktop.AddMessage('','',2,'Build failed. See '+output+'\n'+detail)
        raise
    finally:
        log.close()


ScriptEnv.Initialize('Ansoft.ElectronicsDesktop')
main()
