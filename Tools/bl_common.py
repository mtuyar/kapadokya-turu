"""Blender betikleri icin: KMSH cikisi ve geometri yardimcilari."""
import math
import os
import struct
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KMSH = os.path.join(ROOT, "RawAssets", "kmsh")


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, rgba=(0.5, 0.5, 0.5, 1), rough=0.5, metal=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def assign(obj, material):
    obj.data.materials.clear()
    obj.data.materials.append(material)
    return obj


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def from_pydata(name, verts, faces, material=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    if smooth:
        me.shade_smooth()
    o = link(bpy.data.objects.new(name, me))
    if material:
        assign(o, material)
    return o


def tube(name, points, radius, material, sides=24, res=12, radius_end=None, scale_y=None, scale_z=None):
    """Egri boyunca boru: radius sayi veya her nokta icin liste olabilir."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = res
    cu.bevel_depth = 1.0
    cu.bevel_resolution = max(1, sides // 4 - 1)
    cu.use_fill_caps = True
    sp = cu.splines.new("BEZIER" if len(points) > 2 else "POLY")
    if len(points) > 2:
        sp.bezier_points.add(len(points) - 1)
        for i, p in enumerate(points):
            bp = sp.bezier_points[i]
            bp.co = p
            bp.handle_left_type = bp.handle_right_type = "AUTO"
            bp.radius = radius[i] if isinstance(radius, (list, tuple)) else radius
    else:
        sp.points.add(len(points) - 1)
        for i, p in enumerate(points):
            sp.points[i].co = (*p, 1)
            sp.points[i].radius = radius[i] if isinstance(radius, (list, tuple)) else radius
    o = link(bpy.data.objects.new(name, cu))
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.view_layer.objects.active
    o.select_set(False)
    o.data.shade_smooth()
    assign(o, material)
    return o


def cylinder(name, a, b, r, material, sides=16, r2=None):
    """a'dan b'ye silindir (kapakli)."""
    a, b = Vector(a), Vector(b)
    d = b - a
    q = d.to_track_quat("Z", "Y")
    r2 = r if r2 is None else r2
    verts, faces = [], []
    for k in range(sides):
        t = 2 * math.pi * k / sides
        c = Vector((math.cos(t), math.sin(t), 0))
        verts.append(tuple(a + q @ (c * r)))
        verts.append(tuple(b + q @ (c * r2)))
    for k in range(sides):
        n = (k + 1) % sides
        faces.append((2 * k, 2 * n, 2 * n + 1, 2 * k + 1))
    faces.append(tuple(2 * k for k in reversed(range(sides))))
    faces.append(tuple(2 * k + 1 for k in range(sides)))
    return from_pydata(name, verts, faces, material)


def lathe(name, profile, material, axis_center=(0, 0, 0), segments=96, axis="Y"):
    """profile: (yaricap, eksen) noktalari. Y ekseni etrafinda doner."""
    verts, faces = [], []
    n = len(profile)
    for s in range(segments):
        t = 2 * math.pi * s / segments
        for r, y in profile:
            verts.append((axis_center[0] + r * math.cos(t), axis_center[1] + y, axis_center[2] + r * math.sin(t)))
    for s in range(segments):
        s2 = (s + 1) % segments
        for i in range(n - 1):
            faces.append((s * n + i, s * n + i + 1, s2 * n + i + 1, s2 * n + i))
    return from_pydata(name, verts, faces, material)


def box(name, center, size, material, rot=(0, 0, 0)):
    sx, sy, sz = (size[0] / 2, size[1] / 2, size[2] / 2)
    v = [(-sx, -sy, -sz), (sx, -sy, -sz), (sx, sy, -sz), (-sx, sy, -sz), (-sx, -sy, sz), (sx, -sy, sz), (sx, sy, sz), (-sx, sy, sz)]
    f = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    o = from_pydata(name, v, f, material, smooth=False)
    o.location = center
    o.rotation_euler = rot
    return o


def export_kmsh(objects, filename, slots, origin=(0, 0, 0), uv_scale=None):
    """objects: bpy nesneleri. slots: materyal adi -> slot indeksi. Blender metre/sag el -> UE cm/sol el."""
    bpy.context.view_layer.update()
    deps = bpy.context.evaluated_depsgraph_get()
    P, N, UV, C, T, M = [], [], [], [], [], []
    base = 0
    org = Vector(origin)
    for obj in objects:
        ev = obj.evaluated_get(deps)
        me = ev.to_mesh()
        me.calc_loop_triangles()
        mw = obj.matrix_world
        nm = mw.to_3x3().inverted().transposed()
        nloops = len(me.loops)
        cn = me.corner_normals
        uv_layer = me.uv_layers.active
        col_attr = me.color_attributes.active_color if me.color_attributes else None
        pos = np.zeros((nloops, 3), np.float32)
        nor = np.zeros((nloops, 3), np.float32)
        uv = np.zeros((nloops, 2), np.float32)
        col = np.full((nloops, 4), 255, np.uint8)
        for i, lp in enumerate(me.loops):
            w = mw @ me.vertices[lp.vertex_index].co - org
            pos[i] = (w.x * 100, -w.y * 100, w.z * 100)
            n = (nm @ cn[i].vector).normalized()
            nor[i] = (n.x, -n.y, n.z)
            if uv_layer:
                u = uv_layer.uv[i].vector
                uv[i] = (u.x, 1 - u.y)
        if col_attr is not None:
            data = np.zeros(len(col_attr.data) * 4, np.float32)
            col_attr.data.foreach_get("color", data)
            data = data.reshape(-1, 4)
            if col_attr.domain == "CORNER":
                col = (np.clip(data, 0, 1) * 255).astype(np.uint8)
            else:
                vidx = np.array([lp.vertex_index for lp in me.loops])
                col = (np.clip(data[vidx], 0, 1) * 255).astype(np.uint8)
        tris = np.zeros((len(me.loop_triangles), 3), np.uint32)
        mats = np.zeros(len(me.loop_triangles), np.uint8)
        for i, t in enumerate(me.loop_triangles):
            tris[i] = t.loops
            name = me.materials[t.material_index].name if me.materials else ""
            mats[i] = slots.get(name, 0)
        P.append(pos), N.append(nor), UV.append(uv), C.append(col)
        T.append(tris + base), M.append(mats)
        base += nloops
        ev.to_mesh_clear()
    pos = np.concatenate(P)
    os.makedirs(KMSH, exist_ok=True)
    path = os.path.join(KMSH, filename)
    with open(path, "wb") as f:
        f.write(b"KMS1")
        tris = np.concatenate(T)
        f.write(struct.pack("<II", len(pos), len(tris)))
        f.write(pos.tobytes())
        f.write(np.concatenate(N).tobytes())
        uv = np.concatenate(UV)
        f.write(uv.tobytes())
        f.write(np.zeros_like(uv).tobytes())
        f.write(np.concatenate(C).tobytes())
        f.write(tris.astype(np.uint32).tobytes())
        f.write(np.concatenate(M).tobytes())
    print(f"KMSH {filename}: {len(pos)} kose, {len(tris)} ucgen")


def preview(path, target=(0, 0, 0.55), distance=2.4, azim=-45, elev=14, res=(1100, 700)):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderEngine.bl_rna.properties] else "CYCLES"
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 48
        scene.cycles.device = "CPU"
    except Exception:
        pass
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.filepath = path
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.8, 0.82, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9
    scene.world = world
    cam = bpy.data.cameras.new("c")
    co = bpy.data.objects.new("c", cam)
    scene.collection.objects.link(co)
    a, e = math.radians(azim), math.radians(elev)
    t = Vector(target)
    co.location = t + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * distance
    co.rotation_euler = (t - co.location).to_track_quat("-Z", "Y").to_euler()
    cam.lens = 50
    scene.camera = co
    sun = bpy.data.lights.new("s", "SUN")
    sun.energy = 4
    so = bpy.data.objects.new("s", sun)
    scene.collection.objects.link(so)
    so.rotation_euler = (math.radians(50), math.radians(15), math.radians(-30))
    bpy.ops.render.render(write_still=True)
