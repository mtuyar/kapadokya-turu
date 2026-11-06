"""Yol bisikleti kaski: uzun kabuk, kabukta oyulmus havalandirma yariklari. Eski kutu cikintilar kalkti."""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bl_common as C
C.clear_scene()
m = {"Helmet": C.mat("Helmet"), "Vent": C.mat("Vent")}
seg, rings = 144, 48
verts, faces, is_vent = [], [], []


def vent(a, v):
    """Kabukta yarik deseni: on-arka uzanan 7 yarik, tepede kesilmez, altta biter."""
    if not 0.18 < v < 0.86:
        return False
    return abs(math.sin(a * 3.5 + math.pi / 2)) > 0.86 - 0.06 * v


for j in range(rings + 1):
    v = j / rings
    el = v * math.pi * 0.5
    for i in range(seg):
        a = 2 * math.pi * i / seg
        r = math.cos(el)
        x, y, z = r * math.cos(a), r * math.sin(a), math.sin(el)
        sx = 0.138 * (1.0 + 0.10 * max(0.0, -x))   # arka uzun
        sy = 0.104
        sz = 0.098
        inset = 0.992 if vent(a, v) else 1.0
        dip = 0.024 * max(0.0, -x) ** 2             # arka asagi iner
        verts.append((x * sx * inset, y * sy * inset, z * sz * inset + 0.040 - dip))
for j in range(rings):
    for i in range(seg):
        a = j * seg + i
        b = j * seg + (i + 1) % seg
        c = (j + 1) * seg + (i + 1) % seg
        d = (j + 1) * seg + i
        faces.append((a, b, c, d))
        is_vent.append(vent(2 * math.pi * (i + 0.5) / seg, (j + 0.5) / rings))
h = C.from_pydata("kask", verts, faces, m["Helmet"])
h.data.materials.append(m["Vent"])
for p, flag in zip(h.data.polygons, is_vent):
    p.material_index = 1 if flag else 0
C.export_kmsh([h], "Helmet.kmsh", {"Helmet": 0, "Vent": 1})
print("KASK TAMAM")
