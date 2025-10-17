import random
import logging
import json
import math
import os
from copy import deepcopy
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# 🔹 OTP GENERATION + EMAIL
# -------------------------------------------------------------------

def generate_otp():
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))

def send_otp_email(email, otp):
    """Send the OTP code to a user's email."""
    subject = "Your Login OTP Code"
    message = f"Your OTP code is {otp}. Do not share it with anyone."
    from_email = settings.DEFAULT_FROM_EMAIL

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f"OTP email sent successfully to {email}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        raise Exception(f"Failed to send OTP email: {str(e)}")


import json, math, os
from copy import deepcopy
from django.conf import settings

# -------------------------------------------------------------------
# 🔹 FLOOR CONFIGURATION (real image dimensions)
# -------------------------------------------------------------------
FLOOR_IMAGE_DIMS = {
    1: (2048, 1952),
    2: (2048, 1968),
    3: (2048, 1959),
    4: (2048, 1973),
    5: (2048, 1916),
}

# Define stairs/lifts connecting floors
STAIR_CONNECTIONS = [
    # (node_id_floor1, node_id_floor2)
    ("STAIR_NE_1", "STAIR_NE_2"),
    ("STAIR_NE_2", "STAIR_NE_3"),
    ("STAIR_NE_3", "STAIR_NE_4"),
    ("STAIR_NE_4", "STAIR_NE_5"),
    ("STAIR_W_1", "STAIR_W_2"),
    ("STAIR_W_2", "STAIR_W_3"),
    ("STAIR_W_3", "STAIR_W_4"),
    ("STAIR_W_4", "STAIR_W_5"),
    ("LIFT_1", "LIFT_2"),
    ("LIFT_2", "LIFT_3"),
    ("LIFT_3", "LIFT_4"),
    ("LIFT_4", "LIFT_5"),
]

# -------------------------------------------------------------------
# 🔹 FILE LOADER
# -------------------------------------------------------------------

def _read_static(rel_path: str):
    if settings.STATIC_ROOT:
        p = os.path.join(settings.STATIC_ROOT, rel_path)
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
    for base in getattr(settings, 'STATICFILES_DIRS', []):
        cand = os.path.join(base, rel_path)
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as f:
                return json.load(f)
    project_static = os.path.join(os.path.dirname(settings.BASE_DIR), "static", rel_path)
    if os.path.isfile(project_static):
        with open(project_static, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(rel_path)

# -------------------------------------------------------------------
# 🔹 GRAPH LOADING AND SCALING
# -------------------------------------------------------------------

def load_floor_graph(floor: int):
    rel = f"login/map/graph_floor_{floor}.json"
    data = _read_static(rel)
    meta = data.get("meta", {})
    baseW, baseH = int(meta.get("baseW", 3000)), int(meta.get("baseH", 1500))
    imgW, imgH = FLOOR_IMAGE_DIMS.get(floor, (baseW, baseH))
    sx, sy = imgW / baseW, imgH / baseH
    scaled = deepcopy(data)
    for n in scaled["nodes"].values():
        n["x"] = float(n["x"]) * sx
        n["y"] = float(n["y"]) * sy
    return scaled

# -------------------------------------------------------------------
# 🔹 CORE ALGORITHMS
# -------------------------------------------------------------------

def euclid(a, b):
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])

def _nearest(nodes, pt):
    best, d = None, float("inf")
    for nid, n in nodes.items():
        dist = euclid(n, pt)
        if dist < d:
            best, d = nid, dist
    return best

def _a_star(nodes, edges, start, goal):
    open_set = {start}
    came, g, f = {}, {}, {}
    for n in nodes: g[n] = f[n] = float("inf")
    g[start] = 0
    f[start] = euclid(nodes[start], nodes[goal])

    while open_set:
        cur = min(open_set, key=lambda x: f[x])
        if cur == goal:
            # reconstruct
            path = []
            while cur in came:
                path.append(cur)
                cur = came[cur]
            path.append(start)
            path.reverse()
            return path

        open_set.remove(cur)
        for nb in edges.get(cur, []):
            cand = g[cur] + euclid(nodes[cur], nodes[nb])
            if cand < g[nb]:
                came[nb] = cur
                g[nb] = cand
                f[nb] = cand + euclid(nodes[nb], nodes[goal])
                open_set.add(nb)
    return []

# -------------------------------------------------------------------
# 🔹 MULTI-FLOOR A*
# -------------------------------------------------------------------

def multi_floor_route(start_floor, start_xy, goal_floor, goal_xy):
    """
    Connect all floor graphs with stairs/lifts and find shortest route.
    """
    # Load all floors
    floors = {f: load_floor_graph(f) for f in range(1, 6)}

    # Build unified graph
    nodes, edges = {}, {}
    for f, g in floors.items():
        for nid, n in g["nodes"].items():
            fid = f"{nid}_{f}"
            nodes[fid] = {**n, "floor": f}
        for nid, conns in g["edges"].items():
            fid = f"{nid}_{f}"
            edges[fid] = [f"{c}_{f}" for c in conns]

    # Connect stairs/lifts between floors
    for a, b in STAIR_CONNECTIONS:
        if a in nodes and b in nodes:
            edges.setdefault(a, []).append(b)
            edges.setdefault(b, []).append(a)

    start_node = _nearest(nodes, {**start_xy, "floor": start_floor})
    goal_node = _nearest(nodes, {**goal_xy, "floor": goal_floor})
    if not start_node or not goal_node:
        return {"ok": False, "error": "Start or goal not found"}

    path_ids = _a_star(nodes, edges, start_node, goal_node)
    if not path_ids:
        return {"ok": False, "error": "No route found"}

    path = [
        {"id": nid, "x": nodes[nid]["x"], "y": nodes[nid]["y"], "floor": nodes[nid]["floor"], "name": nodes[nid].get("name", "")}
        for nid in path_ids
    ]
    distance = sum(euclid(nodes[a], nodes[b]) for a, b in zip(path_ids[:-1], path_ids[1:]))
    return {"ok": True, "path": path, "distance": distance}
