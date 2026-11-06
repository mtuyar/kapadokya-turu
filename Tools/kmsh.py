"""KMSH: Python/Blender uretimi aglari Unreal'a tasiyan basit ikili bicim.

Tum degerler Unreal uzayinda: santimetre, Z yukari, sol el koordinat sistemi.
Yazim sirasi C++ tarafi (KapadokyaBuildLib.cpp) ile birebir ayni olmalidir.
"""
import struct
import numpy as np

MAGIC = b"KMS1"


def write(path, pos, normal, uv, color, tris, mat=None, uv2=None):
    """pos/normal Nx3 float, uv Nx2, color Nx4 uint8, tris Tx3 uint32, mat T uint8."""
    pos = np.asarray(pos, np.float32)
    n = len(pos)
    tris = np.asarray(tris, np.uint32)
    mat = np.zeros(len(tris), np.uint8) if mat is None else np.asarray(mat, np.uint8)
    uv2 = np.zeros((n, 2), np.float32) if uv2 is None else np.asarray(uv2, np.float32)
    with open(path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<II", n, len(tris)))
        f.write(pos.tobytes())
        f.write(np.asarray(normal, np.float32).tobytes())
        f.write(np.asarray(uv, np.float32).tobytes())
        f.write(uv2.tobytes())
        f.write(np.asarray(color, np.uint8).tobytes())
        f.write(tris.tobytes())
        f.write(mat.tobytes())
