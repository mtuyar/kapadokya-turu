"""Tum sesleri sentezler (RawAssets/audio/*.wav, 44.1 kHz, 16 bit)."""
import os
import wave

import numpy as np
from scipy.signal import butter, lfilter, sosfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "RawAssets", "audio")
os.makedirs(OUT, exist_ok=True)
SR = 44100
rng = np.random.default_rng(1923)


def save(name, x, stereo=False):
    x = np.asarray(x, np.float64)
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    data = (x * 32767).astype(np.int16)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as f:
        f.setnchannels(2 if stereo else 1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())
    print(name, f"{len(x) / SR / (2 if stereo else 1):.1f}s")


def band(x, lo, hi, order=2):
    sos = butter(order, [lo, hi], "band", fs=SR, output="sos")
    return sosfilt(sos, x)


def low(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def high(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def loopify(x, fade=0.4):
    """Bas ve son carpraz gecisle kusursuz dongu."""
    n = int(fade * SR)
    r = np.linspace(0, 1, n)
    y = x[:-n].copy()
    y[:n] = y[:n] * r + x[-n:] * (1 - r)
    return y


def noise(sec):
    return rng.standard_normal(int(sec * SR))


# --- Lastik: asfaltta yuvarlanma sesi
n = noise(8)
save("S_Tyre", loopify(band(n, 250, 2600) * 0.6 + low(n, 160) * 2.5))

# --- Ruzgar: yavasca dalgalanan alcak gurultu
n = noise(10)
mod = 0.7 + 0.3 * np.sin(2 * np.pi * 0.23 * np.arange(len(n)) / SR) + 0.15 * np.sin(2 * np.pi * 0.71 * np.arange(len(n)) / SR)
save("S_Wind", loopify((low(n, 520, 3) + 0.25 * band(n, 800, 3200)) * mod))

# --- Serbest dise: hizla tik-tik (8 tik/saniye temel; UE pitch ile hizlanir)
sec = 4
y = np.zeros(sec * SR)
tick_rate = 22
click = np.exp(-np.arange(500) / 55.0) * np.sin(2 * np.pi * 4600 * np.arange(500) / SR)
click2 = np.exp(-np.arange(500) / 85.0) * np.sin(2 * np.pi * 7100 * np.arange(500) / SR)
for i in range(int(sec * tick_rate)):
    p = int(i * SR / tick_rate + rng.integers(-40, 40))
    if 0 <= p < len(y) - 500:
        a = 0.75 + 0.25 * rng.random()
        y[p:p + 500] += a * (click + 0.5 * click2)
save("S_Freewheel", loopify(y, 0.05))

# --- Zincir: hafif metalik vinlama ve dis gecisleri
sec = 6
t = np.arange(sec * SR) / SR
hum = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) * a for f, a in [(155, 0.5), (310, 0.3), (925, 0.22), (1860, 0.12)])
save("S_Chain", loopify(hum * 0.22 + band(noise(sec), 2000, 7000) * (0.5 + 0.5 * np.sin(2 * np.pi * 18 * t)) * 0.5))

# --- Arnavut kaldirimi: duzensiz tok vuruslar
sec = 6
y = np.zeros(sec * SR)
for i in range(int(sec * 34)):
    p = rng.integers(0, len(y) - 4000)
    L = rng.integers(900, 3200)
    f = rng.uniform(70, 210)
    env = np.exp(-np.arange(L) / (L * 0.2))
    y[p:p + L] += rng.uniform(0.3, 1.0) * env * np.sin(2 * np.pi * f * np.arange(L) / SR)
    y[p:p + 120] += rng.uniform(0.1, 0.35) * rng.standard_normal(120)
save("S_Cobble", loopify(y * 0.7 + band(noise(sec), 600, 2600) * 0.12))

# --- Nefes: iki faz
sec = 4
t = np.arange(sec * SR) / SR
env = np.maximum(0, np.sin(2 * np.pi * 0.5 * t)) ** 1.4 + 0.55 * np.maximum(0, np.sin(2 * np.pi * 0.5 * t + np.pi)) ** 1.8
save("S_Breath", loopify(band(noise(sec), 500, 3000) * env + 0.2 * band(noise(sec), 180, 500) * env))

# --- Vites degisimi
L = int(0.14 * SR)
t = np.arange(L) / SR
y = np.exp(-t * 55) * np.sin(2 * np.pi * 2400 * t) + 0.8 * np.exp(-t * 38) * band(rng.standard_normal(L), 900, 5000)
y[int(0.05 * SR):] += 0.8 * (np.exp(-t[:L - int(0.05 * SR)] * 70) * np.sin(2 * np.pi * 3200 * t[:L - int(0.05 * SR)]))
save("S_Shift", y)

# --- Dusme
L = int(1.4 * SR)
t = np.arange(L) / SR
y = band(rng.standard_normal(L), 200, 5500) * np.exp(-t * 3.5)
for d, a in ((0.0, 1.0), (0.18, 0.8), (0.42, 0.55), (0.71, 0.3)):
    p = int(d * SR)
    K = L - p
    y[p:] += a * np.exp(-np.arange(K) / SR * 22) * np.sin(2 * np.pi * rng.uniform(80, 180) * np.arange(K) / SR) * 2.4
    y[p:p + 2000] += a * 0.8 * high(rng.standard_normal(2000), 2500) * np.exp(-np.arange(2000) / 500)
save("S_Crash", y)

# --- Geri sayim ve baslangic
L = int(0.25 * SR)
t = np.arange(L) / SR
save("S_Beep", np.sin(2 * np.pi * 880 * t) * np.exp(-t * 9) + 0.25 * np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 12))
L = int(0.9 * SR)
t = np.arange(L) / SR
save("S_Go", (np.sin(2 * np.pi * 1320 * t) + 0.4 * np.sin(2 * np.pi * 2640 * t)) * np.exp(-t * 3.2))

# --- Seyirci: katmanli ugultu, alkis, duzensiz cosku
sec = 14
t = np.arange(sec * SR) / SR
n = noise(sec)
base = band(n, 280, 2300) * (0.8 + 0.25 * np.sin(2 * np.pi * 0.11 * t) + 0.18 * np.sin(2 * np.pi * 0.37 * t))
clap = np.zeros(len(t))
for i in range(4200):
    p = rng.integers(0, len(t) - 800)
    clap[p:p + 800] += rng.uniform(0.2, 1.0) * np.exp(-np.arange(800) / 120) * rng.standard_normal(800)
save("S_Crowd", loopify(base + 0.25 * band(clap, 800, 8000), 0.8))


# --- Muzik: Hicaz makaminda ney + saz + def. 96 BPM, 32 olcu, dongu.
BPM = 76.0
beat = 60.0 / BPM
# Hicaz dizisi (Re koku yakini, Hz): D Eb(koma) F# G A Bb(koma) C D
root = 146.83
SCALE = [0, 1.13, 3.92, 5, 7, 8.13, 10, 12]  # yaklasik Hicaz araliklari (yarim ton)


def freq(deg, octv=0):
    d = deg % 7
    o = deg // 7
    return root * 2 ** ((SCALE[d] + 12 * (o + octv)) / 12)


def ney(f, dur, vib=1.0, attack=0.12):
    L = int(dur * SR)
    t = np.arange(L) / SR
    v = 1 + 0.006 * vib * np.sin(2 * np.pi * (4.6 + rng.random() * 0.6) * t) * np.minimum(1, t / 0.5)
    ph = 2 * np.pi * np.cumsum(f * v) / SR
    body = np.sin(ph) + 0.28 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph) + 0.05 * np.sin(4 * ph)
    breath = band(rng.standard_normal(L), max(f * 0.9, 200), min(f * 5, 9000)) * 0.18
    env = np.minimum(1, t / attack) * np.minimum(1, (dur - t) / 0.25)
    return (body + breath) * env


def pluck(f, dur):
    """Karplus-Strong saz teli."""
    L = int(dur * SR)
    N = int(SR / f)
    buf = rng.uniform(-1, 1, N)
    out = np.zeros(L)
    for i in range(L):
        out[i] = buf[i % N]
        buf[i % N] = 0.5 * (buf[i % N] + buf[(i + 1) % N]) * 0.9965
    return out


def daf(accent=1.0):
    L = int(0.32 * SR)
    t = np.arange(L) / SR
    return accent * (np.exp(-t * 18) * np.sin(2 * np.pi * (72 + 90 * np.exp(-t * 40)) * t) + 0.3 * np.exp(-t * 40) * high(rng.standard_normal(L), 2200))


TOTAL = 32 * 4 * beat
Lout = int(TOTAL * SR) + SR * 3
left, right = np.zeros(Lout), np.zeros(Lout)


def put(buf_l, buf_r, x, at, pan=0.5, gain=1.0):
    p = int(at * SR)
    e = min(len(x), Lout - p)
    if e > 0:
        buf_l[p:p + e] += x[:e] * gain * np.cos(pan * np.pi / 2)
        buf_r[p:p + e] += x[:e] * gain * np.sin(pan * np.pi / 2)


# Ney ezgisi (derece, sure-vurus). Taksim havasinda.
PHRASES = [
    [(4, 3), (5, 1), (4, 2), (3, 2), (2, 3), (1, 1), (2, 4)],
    [(2, 2), (3, 2), (4, 2), (5, 1), (6, 1), (7, 4), (6, 2), (5, 2)],
    [(7, 2), (6, 1), (5, 1), (4, 2), (5, 2), (4, 2), (3, 1), (2, 1), (1, 4)],
    [(0, 3), (1, 1), (2, 2), (3, 2), (2, 2), (1, 2), (0, 4)],
]
order = [0, 1, 2, 3, 0, 2, 1, 3]
at = 0.0
for idx in order:
    for deg, b in PHRASES[idx]:
        d = b * beat
        put(left, right, ney(freq(deg, 1), d * 1.02), at, 0.42, 0.34)
        at += d
# Saz: tekrarlayan ostinato
for bar in range(32):
    pat = [(0, 0.0, 0.9), (4, 1.0, 0.5), (2, 1.5, 0.5), (4, 2.0, 0.6), (1, 3.0, 0.5), (2, 3.5, 0.5)]
    if bar % 8 >= 6:
        pat = [(4, 0.0, 0.8), (5, 1.0, 0.5), (4, 2.0, 0.6), (2, 3.0, 0.6)]
    for deg, off, a in pat:
        put(left, right, pluck(freq(deg, 0), 0.9), (bar * 4 + off) * beat, 0.65, 0.42 * a)
# Def: aksak his (3+2+3)
for bar in range(32):
    for off, a in ((0.0, 1.0), (1.5, 0.55), (2.5, 0.75), (3.5, 0.45)):
        put(left, right, daf(a), (bar * 4 + off) * beat, 0.5, 0.26)
# Hafif oda yankisi
for src, dst, delay, g in ((left, right, 0.031, 0.25), (right, left, 0.043, 0.25), (left, left, 0.083, 0.16), (right, right, 0.097, 0.16)):
    d = int(delay * SR)
    dst[d:] += low(src[:-d], 3200) * g
# Dongu: sonda kalan kuyrugu basa kat
end = int(TOTAL * SR)
tail = Lout - end
left[:tail] += left[end:]
right[:tail] += right[end:]
st = np.empty(end * 2)
st[0::2], st[1::2] = left[:end], right[:end]
save("S_Music", st, stereo=True)

# --- Bitis fanfari (saz ve def)
L = int(3.5 * SR)
fl, fr = np.zeros(L), np.zeros(L)
Lout = L
for i, deg in enumerate((0, 2, 4, 7)):
    put(fl, fr, pluck(freq(deg, 1), 2.8), i * 0.18, 0.4 + i * 0.07, 0.8)
    put(fl, fr, daf(1.0), i * 0.18, 0.5, 0.4)
put(fl, fr, ney(freq(7, 1), 2.5), 0.72, 0.5, 0.4)
st = np.empty(L * 2)
st[0::2], st[1::2] = fl, fr
save("S_Fanfare", st, stereo=True)
