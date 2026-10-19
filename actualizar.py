import json, sys, urllib.request
from datetime import datetime, timedelta, timezone

B = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
NORM = {"NY": "NYK", "SA": "SAS", "GS": "GSW", "NO": "NOP", "UTAH": "UTA", "WSH": "WAS"}
PRIME = {"Prime Video"}
ESPN = {"ESPN", "ESPN2", "ABC", "ESPN Deportes", "ESPN+"}
NBC = {"NBC", "Peacock", "NBCSN"}
MODO = sys.argv[1] if len(sys.argv) > 1 else "rapido"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Encoding": "identity"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def cargar(nombre, defecto):
    try:
        return json.load(open(nombre, encoding="utf-8"))
    except Exception:
        return defecto


def n(abrev):
    return NORM.get(abrev, abrev)


viejo = cargar("data.json", {})
over = cargar("plataformas.json", {})
partidos = {p["id"]: p for p in viejo.get("partidos", [])}
logos = dict(viejo.get("logos", {}))
ahora = datetime.now(timezone.utc)
hoy = (ahora - timedelta(hours=3)).date()
dias = range(-1, 2) if MODO == "rapido" else range(-2, 15)


def plataforma(canales, clave):
    if clave in over:
        return over[clave]
    s = set(canales)
    if s & PRIME:
        return "prime"
    if s & ESPN:
        return "disney"
    if s & NBC:
        return "hbo"
    return "none"


for i in dias:
    d = (hoy + timedelta(days=i)).strftime("%Y%m%d")
    try:
        data = get(f"{B}/scoreboard?dates={d}")
    except Exception as ex:
        print("Fallo el dia", d, ex)
        continue
    for e in data.get("events", []):
        try:
            c = e["competitions"][0]
            eq = {x["homeAway"]: x for x in c["competitors"]}
            a = n(eq["away"]["team"]["abbreviation"])
            h = n(eq["home"]["team"]["abbreviation"])
            for x in (eq["away"], eq["home"]):
                raw = x["team"]["abbreviation"]
                logos[n(raw)] = x["team"].get("logo") or f"https://a.espncdn.com/i/teamlogos/nba/500/{raw.lower()}.png"
            t = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            canales = [nm for b in c.get("broadcasts", []) for nm in b.get("names", [])]
            clave = f"{a}-{h}-{(t - timedelta(hours=3)).strftime('%Y%m%d')}"
            tipo = (e.get("status") or c.get("status") or {}).get("type", {})
            estado = {"pre": "sched", "in": "live", "post": "final"}.get(tipo.get("state"), "sched")
            p = {"id": e["id"], "t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "a": a, "h": h,
                 "p": plataforma(canales, clave), "st": estado}
            if estado != "sched":
                p["sa"] = int(eq["away"].get("score") or 0)
                p["sh"] = int(eq["home"].get("score") or 0)
            if estado == "live":
                p["clk"] = tipo.get("shortDetail") or tipo.get("detail") or "En vivo"
            partidos[p["id"]] = p
        except Exception as ex:
            print("Partido salteado", ex)

posiciones = viejo.get("posiciones", {})
try:
    s = get("https://site.api.espn.com/apis/v2/sports/basketball/nba/standings")
    nuevo_pos = {}
    for ch in s.get("children", []):
        k = "E" if "East" in ch.get("name", "") else "W"
        filas = []
        for en in ch["standings"]["entries"]:
            st = {x["name"]: x.get("value") for x in en.get("stats", [])}
            filas.append({"a": n(en["team"]["abbreviation"]), "w": int(st.get("wins") or 0),
                          "l": int(st.get("losses") or 0), "seed": st.get("playoffSeed") or 99})
        filas.sort(key=lambda f: (f["seed"], -f["w"], f["l"]))
        nuevo_pos[k] = [{"a": f["a"], "w": f["w"], "l": f["l"]} for f in filas]
    if nuevo_pos:
        posiciones = nuevo_pos
except Exception as ex:
    print("Fallaron las posiciones", ex)

base = {k: v for k, v in viejo.items() if k != "actualizado"}
nuevo = {"logos": logos, "partidos": sorted(partidos.values(), key=lambda p: p["t"]), "posiciones": posiciones}
if nuevo == base:
    print("Sin cambios")
    sys.exit(0)
nuevo["actualizado"] = ahora.strftime("%Y-%m-%dT%H:%M:%SZ")
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(nuevo, f, ensure_ascii=False, separators=(",", ":"))
print("data.json actualizado:", len(nuevo["partidos"]), "partidos")
