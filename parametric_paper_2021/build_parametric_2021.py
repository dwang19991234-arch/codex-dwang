# -*- coding: utf-8 -*-
# Run inside HFSS 2021 R1: Tools > Run Script.
# Structure-check model traced from paper Fig. 1a, NOT a verified Fig. 2d reproduction.
# Builds a NEW parameterized model, three independent sweeps, no solve.
# Keeps nominal geometry equal to the preceding finite-GSG baseline.
import os
import time
import traceback
import ScriptEnv

P = {
    'slot_L': 260.0, 'slot_W': 12.0, 'slot_D': 125.0, 'slot_shift': 0.0,
    'feed_W': 12.0, 'gap': 6.0, 'det_gap': 6.0,
    'choke_L': 120.0, 'low_W': 110.0, 'high_W': 12.0,
    'taper_L': 130.0, 'lead_L': 250.0,
    'lead_W': 60.0, 'lead_gap': 31.0,
    'chip_right': 350.0, 'chip_half_y': 600.0,
    'margin': 900.0, 'air_H': 1000.0, 'si_H': 1000.0,
    'oxide_t': 0.3, 'epsilon_oxide': 3.9,
    'pad_extension': 400.0, 'pad_flat_L': 370.0,
    'signal_pad_half_y': 80.0, 'ground_pad_inner_y': 155.0,
    'ground_pad_outer_y': 545.0, 'ground_neck_half_y': 265.0,
    'antenna_plate_back': 350.0, 'antenna_plate_half_y': 350.0,
    'epsilon_si': 11.7, 'sigma_si': 1.0, 'port_ohm': 1000.0
}


def u(value):
    return value if isinstance(value, str) else ('%.15g' % float(value)) + 'um'


def rectangle(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def core_geometry(p):
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


def paper_outline(p):
    throat = -p['slot_D']/2-p['slot_W']/2-p['taper_L']-10*p['choke_L']
    left = throat-p['lead_L']-p['pad_extension']
    knee = left+p['pad_flat_L']
    h = p['ground_pad_outer_y']
    n = p['ground_neck_half_y']
    a = -p['antenna_plate_back']
    ah = p['antenna_plate_half_y']
    outline = [(left,h),(knee,h),(throat,n),(a,n),(a,ah),
               (p['chip_right'],ah),(p['chip_right'],-ah),(a,-ah),
               (a,-n),(throat,-n),(knee,-h),(left,-h)]
    return left,knee,throat,outline


def geometry(p):
    unused,cuts,strips = core_geometry(p)
    left,knee,throat,outline = paper_outline(p)
    inner = p['ground_pad_inner_y']
    outer = p['low_W']/2+p['gap']
    cuts[0] = ('LeadClearance',[(left-1,inner),(knee,inner),
               (throat,outer),(throat,-outer),(knee,-inner),(left-1,-inner)])
    sy = p['signal_pad_half_y']
    narrow = p['high_W']/2
    strips[0] = ('Lead',[(left,-sy),(knee,-sy),(throat,-narrow),
                        (throat,narrow),(knee,sy),(left,sy)])
    return left,cuts,strips


# Keep pad/choke/platform anchors fixed during local antenna sweeps.
ANCHOR_SLOT_D = 125.0


def parametric_geometry(p):
    anchor = dict(p)
    anchor['slot_D'] = ANCHOR_SLOT_D
    left,cuts,strips = geometry(anchor)
    neg = '(slot_shift-slot_D/2)'
    pos = '(slot_shift+slot_D/2)'
    le = neg+'-'+u(p['slot_W']/2)
    re = pos+'+'+u(p['slot_W']/2)
    taper = -ANCHOR_SLOT_D/2-p['slot_W']/2-p['taper_L']
    outer = p['low_W']/2+p['gap']
    inner = p['feed_W']/2+p['gap']
    cut_replacements = {
        'TaperClearance': [(taper,-outer),(le,-inner),(le,inner),(taper,outer)],
        'FeedClearance': rectangle(le,-inner,re,inner),
        'SlotNeg_upper': rectangle(neg+'-'+u(p['slot_W']/2),p['feed_W']/2,
                                  neg+'+'+u(p['slot_W']/2),'slot_L/2'),
        'SlotNeg_lower': rectangle(neg+'-'+u(p['slot_W']/2),'-slot_L/2',
                                  neg+'+'+u(p['slot_W']/2),-p['feed_W']/2),
        'SlotPos_upper': rectangle(pos+'-'+u(p['slot_W']/2),p['feed_W']/2,
                                  pos+'+'+u(p['slot_W']/2),'slot_L/2'),
        'SlotPos_lower': rectangle(pos+'-'+u(p['slot_W']/2),'-slot_L/2',
                                  pos+'+'+u(p['slot_W']/2),-p['feed_W']/2)
    }
    strip_replacements = {
        'SignalTaper': [(taper,-p['low_W']/2),(le,-p['feed_W']/2),
                        (le,p['feed_W']/2),(taper,p['low_W']/2)],
        'FeedLeft': rectangle(le,-p['feed_W']/2,-p['det_gap']/2,p['feed_W']/2),
        'FeedRight': rectangle(p['det_gap']/2,-p['feed_W']/2,re,p['feed_W']/2)
    }
    return left,[(n,cut_replacements.get(n,v)) for n,v in cuts], [
                (n,strip_replacements.get(n,v)) for n,v in strips]


def check_local_parameters(p):
    if p['slot_L'] <= p['feed_W'] or p['slot_L']/2 >= p['antenna_plate_half_y']:
        raise ValueError('Slot length exceeds its metal platform or is too small.')
    left_center = p['slot_shift']-p['slot_D']/2
    right_center = p['slot_shift']+p['slot_D']/2
    if left_center+p['slot_W']/2 >= -p['det_gap']/2:
        raise ValueError('Left slot would overlap the fixed port.')
    if right_center-p['slot_W']/2 <= p['det_gap']/2:
        raise ValueError('Right slot would overlap the fixed port.')
    taper = -ANCHOR_SLOT_D/2-p['slot_W']/2-p['taper_L']
    if left_center-p['slot_W']/2 <= taper:
        raise ValueError('Taper length would vanish or reverse.')
    if left_center-p['slot_W']/2 <= -p['antenna_plate_back'] or right_center+p['slot_W']/2 >= p['chip_right']:
        raise ValueError('Slot would leave the fixed antenna metal platform.')


def add_parametric_setups(design,p):
    optimetrics = design.GetModule('Optimetrics')
    sweeps = [
        ('SlotLengthSweep','slot_L','LIN 260um 420um 40um'),
        ('SlotDistanceSweep','slot_D','100um 125um 150um 175um 200um'),
        ('SlotShiftSweep','slot_shift','-20um -10um 0um 10um 20um')
    ]
    for name,variable,values in sweeps:
        starting = ['NAME:StartingPoint']
        for other in ('slot_L','slot_D','slot_shift'):
            starting += [other+':=',u(p[other])]
        optimetrics.InsertSetup('OptiParametric',[
            'NAME:'+name,'IsEnabled:=',True,
            ['NAME:ProdOptiSetupDataV2','SaveFields:=',False,
             'CopyMesh:=',False,'SolveWithCopiedMeshOnly:=',False],
            starting,'Sim. Setups:=',['Setup220'],
            ['NAME:Sweeps',['NAME:SweepDefinition','Variable:=',variable,
                'Data:=',values,'OffsetF1:=',False,'Synchronize:=',0]],
            ['NAME:Sweep Operations'],['NAME:Goals']])


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
            if key != 'slot_shift' and value <= 0:
                raise ValueError('Parameter must be positive: '+key)
        if P['slot_D'] <= P['slot_W']+P['det_gap']:
            raise ValueError('Slot spacing is too small for the port.')
        if P['slot_L'] <= P['feed_W'] or P['slot_L']/2 >= P['chip_half_y']:
            raise ValueError('Invalid slot length.')
        check_local_parameters(P)
        chip_left,cuts,strips = parametric_geometry(P)
        stage('PAPER STRUCTURE CHECK: estimated dimensions, not reproduced data. No solve will run.')
        project = desktop.NewProject()
        project.InsertDesign('HFSS','Fig2d_parametric_2021','DrivenModal','')
        design = project.SetActiveDesign('Fig2d_parametric_2021')
        editor = design.SetActiveEditor('3D Modeler')
        editor.SetModelUnits(['NAME:Units Parameter','Units:=','um','Rescale:=',False])
        properties = ['NAME:NewProps']
        for name in ('slot_L','slot_D','slot_shift'):
            properties.append(['NAME:'+name,'PropType:=','VariableProp',
                               'UserDef:=',True,'Value:=',u(P[name])])
        design.ChangeProperty(['NAME:AllTabs',['NAME:LocalVariableTab',
            ['NAME:PropServers','LocalVariables'],properties]])
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
        manager.AddMaterial(['NAME:SiO2_approx',
            'CoordinateSystemType:=','Cartesian','BulkOrSurfaceType:=',1,
            ['NAME:PhysicsTypes','set:=',['Electromagnetic']],
            'permittivity:=',str(P['epsilon_oxide']),
            'conductivity:=','0','dielectric_loss_tangent:=','0'])
        box(editor,'OxideLayer',[x0,y0,-P['oxide_t']],
            [dx,dy,P['oxide_t']],'SiO2_approx')
        box(editor,'SiliconHalfSpaceApprox',[x0,y0,-P['si_H']-P['oxide_t']],
            [dx,dy,P['si_H']],'Si_100ohm_cm_approx')
        anchor = dict(P)
        anchor['slot_D'] = ANCHOR_SLOT_D
        sheet(editor,'Ground',paper_outline(anchor)[3])
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
        for name in ('AirDomain','OxideLayer','SiliconHalfSpaceApprox'):
            for face in editor.GetFaceIDs(name):
                z = float(editor.GetFaceCenter(int(face))[2])
                if abs(z) > 1e-8 and abs(z+P['oxide_t']) > 1e-8:
                    faces.append(int(face))
        if len(faces) != 14:
            raise RuntimeError('Expected fourteen exterior faces; got '+str(len(faces)))
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
        # Two saved-field samples for nominal runs; separate from the broad sweep.
        analysis.InsertFrequencySweep('Setup220',[
            'NAME:FieldCheck','IsEnabled:=',True,'RangeType:=','LinearCount',
            'RangeStart:=','130GHz','RangeEnd:=','171GHz','RangeCount:=',2,
            'Type:=','Discrete','SaveFields:=',True,'SaveRadFields:=',False])
        # Save the core model first even if an older Optimetrics API rejects a setting.
        path = os.path.join(output,'Graphene_Parametric_2021.aedt')
        project.SaveAs(path,True)
        add_parametric_setups(design,P)
        project.SaveAs(path,True)
        stage('Saved: '+path)
        valid = design.ValidateDesign(os.path.join(output,'validation.log'))
        if valid != 1:
            raise RuntimeError('Validation failed; inspect validation.log.')
        editor.FitAll()
        stage('PARAMETRIC BUILD COMPLETE. No solve has run.')
        stage('Run Setup220 nominal first. Then analyze SlotLengthSweep only.')
        stage('slot_L/slot_D/slot_shift change local antenna geometry; port stays fixed.')
        stage('PEC, open IF end, image-estimated geometry remain model assumptions.')
    except Exception:
        detail = traceback.format_exc()
        log.write(detail)
        desktop.AddMessage('','',2,'Build failed. See '+output+'\n'+detail)
        raise
    finally:
        log.close()


ScriptEnv.Initialize('Ansoft.ElectronicsDesktop')
main()
