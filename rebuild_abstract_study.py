# SPDX-License-Identifier: GPL-3.0-or-later
# Self-authored isolated bpy capability probe. Artwork/source data are not
# automatically relicensed by this script header. No client assets or network.
import bpy, math, json, time, hashlib, os, sys, struct
from pathlib import Path
from datetime import datetime, timezone
from mathutils import Vector

OUT = Path(__file__).resolve().parent/'local-output'
START = time.time()
OUT.mkdir(parents=True, exist_ok=True)
receipt = {"kind":"self_initiated_nonmedical_abstract_native_blender_probe", "started_utc":datetime.now(timezone.utc).isoformat(), "blender_version":bpy.app.version_string, "source_file":Path(__file__).name, "client_materials":False, "direct_cash_purchases":0, "model_tool_resource_currency":"Unquantified", "failures":[], "renders":[]}

def write_receipt():
    (OUT/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def clean_png_metadata(source):
    # Container-only removal: IDAT and color-space chunks remain bit-identical.
    data=source.read_bytes(); assert data[:8]==b'\x89PNG\r\n\x1a\n'
    keep={b'IHDR',b'PLTE',b'IDAT',b'IEND',b'sRGB',b'gAMA',b'cHRM',b'pHYs',b'tRNS'}
    parts=[]; original_idat=[]; offset=8
    while offset<len(data):
        length=struct.unpack('>I',data[offset:offset+4])[0]; end=offset+12+length
        assert end<=len(data)
        kind=data[offset+4:offset+8]; chunk=data[offset:end]
        if kind==b'IDAT': original_idat.append(chunk)
        if kind in keep: parts.append(chunk)
        offset=end
    assert offset==len(data)
    dest=OUT/'public-stills'/source.name; dest.parent.mkdir(exist_ok=True)
    clean=data[:8]+b''.join(parts); dest.write_bytes(clean)
    retained_idat=[c for c in parts if c[4:8]==b'IDAT']
    assert b''.join(original_idat)==b''.join(retained_idat)
    return {'path':'public-stills/'+dest.name,'bytes':len(clean),'sha256':digest(dest),'idat_preserved':True,'metadata_removed':['text','EXIF','offsets']}

def look_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def material(name, color, metallic, roughness):
    m=bpy.data.materials.new(name); m.use_nodes=True
    n=m.node_tree.nodes; links=m.node_tree.links
    bs=n.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*color,1)
    bs.inputs['Metallic'].default_value=metallic; bs.inputs['Roughness'].default_value=roughness
    if 'Coat Weight' in bs.inputs: bs.inputs['Coat Weight'].default_value=.22
    noise=n.new('ShaderNodeTexNoise'); noise.name='Editable_microfiber_surface'; noise.inputs['Scale'].default_value=120
    noise.inputs['Detail'].default_value=2
    bump=n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value=.13; bump.inputs['Distance'].default_value=.012
    links.new(noise.outputs['Fac'],bump.inputs['Height']); links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    return m

try:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for material_block in list(bpy.data.materials): bpy.data.materials.remove(material_block,do_unlink=True)
    scene=bpy.context.scene
    scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16
    scene.cycles.use_denoising=True; scene.cycles.max_bounces=5
    scene.render.threads_mode='FIXED'; scene.render.threads=8
    scene.render.resolution_x=640; scene.render.resolution_y=640; scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'; scene.render.image_settings.color_mode='RGBA'; scene.render.image_settings.color_depth='8'
    scene.render.film_transparent=False; scene.render.fps=24; scene.frame_start=1; scene.frame_end=97
    scene.render.filepath='//renders/frame_'
    bpy.context.preferences.filepaths.save_version=0
    scene.world.use_nodes=True; scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.014,.020,.027,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.26
    scene.view_settings.view_transform='AgX'; scene.view_settings.exposure=.25
    mats=[material('Ivory_fibers_editable',(.66,.56,.40),.28,.27), material('Cool_silk_fibers_editable',(.26,.40,.40),.40,.24), material('Warm_copper_accents_editable',(.48,.22,.075),.58,.25)]
    verts=[]; pulse=[]; faces=[]; face_mats=[]
    N,S,K=112,256,6
    for j in range(N):
        v=2*math.pi*j/N
        for i in range(S):
            u=2*math.pi*i/S
            major=1.23+.085*math.cos(3*u)+.035*math.sin(7*u)
            twist=v+.30*math.sin(3*u)+.11*math.sin(9*u)
            minor=.34+.045*math.sin(5*u+.4*v)+.018*math.cos(18*u+v)
            center=Vector(((major+minor*math.cos(twist))*math.cos(u),(major+minor*math.cos(twist))*math.sin(u),.145*math.sin(2*u)+.29*math.sin(twist)))
            radial=Vector((math.cos(twist)*math.cos(u),math.cos(twist)*math.sin(u),math.sin(twist)))
            tangent=Vector((-math.sin(u),math.cos(u),.08*math.cos(2*u))).normalized()
            across=tangent.cross(radial).normalized()
            thickness=.0074*(1+.13*math.sin(11*u+v))
            for k in range(K):
                a=2*math.pi*k/K
                p=center+thickness*(math.cos(a)*radial+math.sin(a)*across)
                verts.append(tuple(p))
                q=Vector((p.x*(1+.012*math.sin(3*u)),p.y*(1+.012*math.sin(3*u)),p.z+.047*math.sin(2*u+.35*v)))
                pulse.append(tuple(q))
        for i in range(S):
            for k in range(K):
                a=j*S*K+i*K+k; b=j*S*K+((i+1)%S)*K+k
                faces.append((a,b,j*S*K+((i+1)%S)*K+(k+1)%K,j*S*K+i*K+(k+1)%K))
                face_mats.append(2 if j%23==0 else (1 if j%7==0 else 0))
    mesh=bpy.data.meshes.new('Editable_individual_fiber_tubes'); mesh.from_pydata(verts,[],faces); mesh.update()
    obj=bpy.data.objects.new('Abstract_fiber_ring_editable',mesh); scene.collection.objects.link(obj)
    for m in mats:mesh.materials.append(m)
    for p,idx in zip(mesh.polygons,face_mats):p.use_smooth=True;p.material_index=idx
    obj['self_initiated']=True;obj['medical_accuracy_claim']=False;obj['fiber_count']=N;obj['loop_frames']=96
    base=obj.shape_key_add(name='Basis'); key=obj.shape_key_add(name='Subtle_organic_pulse')
    for v,p in zip(key.data,pulse):v.co=p
    drv=key.driver_add('value').driver; drv.type='SCRIPTED'; drv.expression='0.5-0.5*cos(2*pi*(frame-1)/96)'
    floor=material('Backdrop_matte',(.018,.027,.032),.05,.66)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.73));bpy.context.object.name='Backdrop';bpy.context.object.data.materials.append(floor)
    for name,loc,power,size,col in [('Warm_key',(-3,-4,5),1000,4.2,(1,.85,.65)),('Cool_rim',(3,2,3.5),1350,3.2,(.50,.79,1)),('Soft_fill',(-3,3,1.5),550,3,(1,.58,.31))]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size;light.color=col
        lo=bpy.data.objects.new(name,light);scene.collection.objects.link(lo);lo.location=loc;look_at(lo,(0,0,0))
    ca=bpy.data.cameras.new('Probe_camera'); cam=bpy.data.objects.new('Probe_camera',ca);scene.collection.objects.link(cam)
    cam.location=(3.7,-4.8,3.5);look_at(cam,(0,0,-.03));ca.type='ORTHO';ca.ortho_scale=4.30;scene.camera=cam
    scene['claim']='Original generic nonmedical abstract fiber material and pulse probe; no client reference or style acceptance.'
    scene.frame_set(25)
    blend=OUT/'abstract-pulse-native.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
    # Reopen the actual saved native file before observations or renders.
    bpy.ops.wm.open_mainfile(filepath=str(blend));scene=bpy.context.scene;obj=bpy.data.objects['Abstract_fiber_ring_editable']
    receipt['native_reopen']={'path':blend.name,'sha256':digest(blend),'bytes':blend.stat().st_size,'mesh_vertices':len(obj.data.vertices),'mesh_faces':len(obj.data.polygons),'shape_keys':[k.name for k in obj.data.shape_keys.key_blocks],'driver_expression':obj.data.shape_keys.animation_data.drivers[0].driver.expression,'materials':[m.name for m in obj.data.materials],'objects':[o.name for o in scene.objects],'camera':scene.camera.name,'render_engine':scene.render.engine,'samples':scene.cycles.samples,'resolution':[scene.render.resolution_x,scene.render.resolution_y],'render_threads':scene.render.threads,'external_images':[im.name for im in bpy.data.images if im.source=='FILE']}
    observations=[]
    for frame in [1,25,49,97]:
        scene.frame_set(frame);bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();eo=obj.evaluated_get(deps);em=eo.to_mesh()
        observations.append({'frame':frame,'pulse_value':obj.data.shape_keys.key_blocks['Subtle_organic_pulse'].value,'evaluated_vertex_0':list(em.vertices[0].co),'evaluated_vertex_18000':list(em.vertices[18000].co)});eo.to_mesh_clear()
    receipt['phase_observations']=observations;receipt['native_reopen_verified']=True;receipt['script_sha256']=digest(Path(__file__))
    write_receipt()
    for name,frame in [('still-midphase.png',25),('phase-001.png',1),('phase-025.png',25),('phase-049.png',49)]:
        if time.time()-START>600:receipt['stopped_due_time_cap']=True;break
        scene.frame_set(frame);scene.render.filepath=str(OUT/name);t=time.time();bpy.ops.render.render(write_still=True)
        p=OUT/name; public_copy=clean_png_metadata(p);receipt['renders'].append({'name':name,'frame':frame,'bytes':p.stat().st_size,'sha256':digest(p),'seconds':round(time.time()-t,3),'clean_copy':public_copy,'dimensions':[scene.render.resolution_x,scene.render.resolution_y]});write_receipt()
    receipt['complete']=len(receipt['renders'])==4
    receipt['elapsed_seconds']=round(time.time()-START,3)
    receipt['limitations']=['One original nonmedical abstract probe, not a buyer scene, full animation, medical model or style acceptance.','Three phase samples, not playback/temporal denoising/loop seam video acceptance.','CPU Cycles low-sample 640-square renders; production resolution and render cost not established.','Native mesh/shape-key/driver/material structure reopened in the same Blender version; cross-version/customer pipeline import untested.','Output use rights and bpy script licensing are distinct; no third-party assets or binaries distributed.']
    receipt['ended_utc']=datetime.now(timezone.utc).isoformat();write_receipt();print('HX_ABSTRACT_PROBE_COMPLETE',json.dumps({'complete':receipt['complete'],'elapsed_seconds':receipt['elapsed_seconds'],'renders':len(receipt['renders'])}))
except Exception as exc:
    receipt['failures'].append({'type':type(exc).__name__,'message':str(exc)});receipt['elapsed_seconds']=round(time.time()-START,3);write_receipt();raise
