"""The arithmetic the decks share: interpolation along sweeps, crossings, grids, thinning, Goertzel.

Standard library only, because it runs inside the simulator images, which have no numpy. Everything
takes plain lists; a value that cannot be read is None, never an exception, so that one unreadable
number costs one output and not the whole measurement.
"""

import math

LN10 = 2.302585092994046
K_B = 1.380649e-23
Q_E = 1.602176634e-19
T_K = 298.15
VT_25 = K_B * T_K / Q_E              # 25.69 mV
DECADE_MV_25 = VT_25 * LN10          # 59.16 mV per decade of current, for an ideality factor of one


def n(x):
    """A number as the netlists write it: nine significant figures, the same text in every run."""
    return f"{x:.9g}"


def si(x, unit):
    """A condition as an output key spells it: 1e-3 A → 1mA, 0.5 V → 500mV, 1e5 Hz → 100kHz."""
    if x == 0:
        return f"0{unit}"
    prefixes = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")]
    ax = abs(x)
    for scale, p in prefixes:
        if ax >= scale * 0.9999:
            m = x / scale
            txt = f"{m:.3g}"
            if "e" in txt:
                txt = f"{m:.0f}"
            return f"{txt}{p}{unit}"
    return f"{x:.3g}{unit}"


def interp(xs, ys, x):
    """ys at x, linear, xs increasing; None outside the range."""
    for a in range(len(xs) - 1):
        x0, x1 = xs[a], xs[a + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return ys[a]
            w = (x - x0) / (x1 - x0)
            return ys[a] + w * (ys[a + 1] - ys[a])
    return None


def log_interp(xs, ys, x):
    """ys at x, interpolated in log x; xs increasing and positive; None outside the range."""
    if x <= 0:
        return None
    for a in range(len(xs) - 1):
        x0, x1 = xs[a], xs[a + 1]
        if x0 > 0 and x1 > 0 and x0 <= x <= x1:
            w = (math.log(x) - math.log(x0)) / (math.log(x1) - math.log(x0)) if x1 != x0 else 0
            return ys[a] + w * (ys[a + 1] - ys[a])
    return None


def loglog_interp(xs, ys, x):
    """ys at x with both axes logarithmic; None outside the range or where y is not positive."""
    pts = [(a, b) for a, b in zip(xs, ys) if a > 0 and b is not None and b > 0]
    if len(pts) < 2:
        return None
    v = log_interp([p[0] for p in pts], [math.log(p[1]) for p in pts], x)
    return math.exp(v) if v is not None else None


def monotone(xs, ys):
    """The points sorted by x, with x strictly increasing (a sweep that turned back loses the turn)."""
    pts = sorted((a, b) for a, b in zip(xs, ys) if a is not None and b is not None)
    out = []
    for a, b in pts:
        if out and a <= out[-1][0]:
            continue
        out.append((a, b))
    return [p[0] for p in out], [p[1] for p in out]


def until_peak(ys, tol=0.01):
    """How many points of a sweep to keep: up to and including the maximum of ys when the sweep then falls
    below it by more than `tol` of it (a collector current with a ceiling: NK > 1), else all of them."""
    if not ys:
        return 0
    kp = max(range(len(ys)), key=lambda j: ys[j])
    if kp < len(ys) - 1 and ys[kp] > 0 and min(ys[kp + 1:]) < ys[kp] * (1 - tol):
        return kp + 1
    return len(ys)


def crossing(t, y, level, after, rising):
    """The first time after `after` at which y crosses level in the given direction, interpolated."""
    for k in range(1, len(t)):
        if t[k] <= after:
            continue
        a, b = y[k - 1], y[k]
        if (rising and a < level <= b) or (not rising and a > level >= b):
            return t[k - 1] + (level - a) / (b - a) * (t[k] - t[k - 1]) if b != a else t[k]
    return None


def at_x(xs, ys, x, log=True):
    """ys at the sample nearest x (log distance by default)."""
    if not xs:
        return None
    if log and x > 0:
        k = min(range(len(xs)), key=lambda j: abs(math.log10(xs[j] / x)) if xs[j] > 0 else float("inf"))
    else:
        k = min(range(len(xs)), key=lambda j: abs(xs[j] - x))
    return ys[k]


def grid_points(grid):
    """The x values of a catalogue grid: an explicit list, or from/to by step or per decade."""
    if "values" in grid:
        return list(grid["values"])
    lo, hi = float(grid["from"]), float(grid["to"])
    if "per_decade" in grid:
        k = int(grid["per_decade"])
        a, b = round(math.log10(lo) * k), round(math.log10(hi) * k)
        return [10 ** (i / k) for i in range(a, b + 1)]
    step = float(grid["step"])
    count = int(round((hi - lo) / step)) + 1
    return [lo + i * step for i in range(count)]


def on_grid(xs, ys, grid, log_x=True, log_y=False):
    """ys sampled at the grid's x values: the published form of a curve (None where the sweep did not reach)."""
    xs2, ys2 = monotone(xs, ys)
    out = []
    for g in grid_points(grid):
        if log_y:
            v = loglog_interp(xs2, ys2, g) if log_x else None
            if not log_x:
                pts = [(a, math.log(b)) for a, b in zip(xs2, ys2) if b is not None and b > 0]
                v = interp([p[0] for p in pts], [p[1] for p in pts], g)
                v = math.exp(v) if v is not None else None
        else:
            v = log_interp(xs2, ys2, g) if log_x else interp(xs2, ys2, g)
        out.append(v)
    return out


def thin(xs, ys, keep=60):
    """At most `keep` (x, y) pairs that follow the curve: Ramer–Douglas–Peucker on axes scaled to the
    curve's own span, for transients whose interesting part is a few nanoseconds of several microseconds."""
    pts = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pts) <= keep:
        return [[a, b] for a, b in pts]
    sx = (pts[-1][0] - pts[0][0]) or 1.0
    sy = (max(p[1] for p in pts) - min(p[1] for p in pts)) or 1.0
    chosen = {0, len(pts) - 1}

    def farthest(i, j):
        (x0, y0), (x1, y1) = pts[i], pts[j]
        best, bi = -1.0, None
        dx, dy = (x1 - x0) / sx, (y1 - y0) / sy
        norm = math.hypot(dx, dy) or 1.0
        for k in range(i + 1, j):
            px, py = (pts[k][0] - x0) / sx, (pts[k][1] - y0) / sy
            d = abs(px * dy - py * dx) / norm
            if d > best:
                best, bi = d, k
        return best, bi

    segments = [(0, len(pts) - 1)]
    while len(chosen) < keep and segments:
        best = max(((farthest(i, j), i, j) for i, j in segments if j - i > 1), default=None)
        if best is None or best[0][1] is None:
            break
        (_, k), i, j = best
        chosen.add(k)
        segments.remove((i, j))
        segments += [(i, k), (k, j)]
    return [[pts[k][0], pts[k][1]] for k in sorted(chosen)]


def resample(t, y, t0, t1, count):
    """y on `count` evenly spaced times from t0 to t1 (t1 excluded), linear between samples."""
    out = []
    k = 0
    for i in range(count):
        ti = t0 + (t1 - t0) * i / count
        while k < len(t) - 2 and t[k + 1] < ti:
            k += 1
        a, b = t[k], t[k + 1]
        w = (ti - a) / (b - a) if b != a else 0.0
        out.append(y[k] + w * (y[k + 1] - y[k]))
    return out


def goertzel(samples, k):
    """The amplitude of the k-th bin of a real sequence (2|X_k|/N), without a full transform."""
    count = len(samples)
    w = 2 * math.pi * k / count
    c = 2 * math.cos(w)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + c * s1 - s2
        s2, s1 = s1, s0
    re = s1 - s2 * math.cos(w)
    im = s2 * math.sin(w)
    return 2 * math.hypot(re, im) / count


def linfit(xs, ys):
    """Least-squares slope and intercept of y against x; None with fewer than two points."""
    m = len(xs)
    if m < 2:
        return None, None
    mx, my = sum(xs) / m, sum(ys) / m
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return None, None
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    return slope, my - slope * mx
