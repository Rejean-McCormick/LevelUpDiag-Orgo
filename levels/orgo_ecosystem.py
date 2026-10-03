"""Focused local ecosystem E2E: Konvergence seed -> Orgo -> Kor -> Android."""
from __future__ import annotations

import base64
import hashlib
import http.cookiejar
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from levelupdiag_core.commands import run_command
from levelupdiag_core.util import read_dotenv

EXPECTED_CASES = 5
EXPECTED_TASKS = 19
KOR_PORT = 8080
KOR_TENANT = "local"
KOR_SUBJECT = "alice"
KOR_PACKAGE = "org.koali.kor"
ACCOUNT_HASH = hashlib.sha256(b"5:local5:alice").hexdigest()
ANDROID_DB = f"kor-{ACCOUNT_HASH}.db"

SEED = {
    "contract": "koa-orgo-sim/v1",
    "cases": [
        {"case_id":"CASE-DANCE-RED-001","title":"Résonance danse / texte manuscrit","origin_world":"amusement-kreative","origin_topic":"red_mask_video","status":"open","mandate":"Examiner une corrélation apparente entre deux œuvres créées en parallèle sans la transformer en certitude.","tasks":[{"task":"Documenter les deux sources et la chronologie","owner":"actor_jeremie"},{"task":"Tester correspondances, non-correspondances et contrôles","owner":"actor_simon"},{"task":"Formuler l’hypothèse de résonance de Pi","owner":"actor_elias"},{"task":"Formaliser le mécanisme abstrait de superposition","owner":"actor_gustave"},{"task":"Vérifier la limite entre interprétation et affirmation","owner":"actor_aida"}],"media_ref":"https://www.youtube.com/watch?v=MllMQLphUxc"},
        {"case_id":"CASE-DANCE-TWO-002","title":"Deux vidéos d’incarnation Réjean / King Klown","origin_world":"amusement-kreative","origin_topic":"two_dance_videos","status":"planned","mandate":"Produire deux performances distinctes puis conserver provenance, intention et réactions.","tasks":[{"task":"Concevoir les deux chorégraphies","owner":"actor_jeremie"},{"task":"Préparer publication et traçabilité","owner":"actor_simon"},{"task":"Cadre éthique et explicitation fictionnelle","owner":"actor_aida"},{"task":"Analyser réception et apprentissage","owner":"actor_elias"}]},
        {"case_id":"CASE-ALERT-LOCAL-001","title":"Alerte publique contextuelle","origin_world":"orgo-events","origin_topic":"context_alert","status":"simulation","mandate":"Tester un avis ciblé par contexte/géographie plutôt qu’une interruption générale.","tasks":[{"task":"Définir la population concernée","owner":"actor_aida"},{"task":"Configurer le routage local","owner":"actor_simon"},{"task":"Préparer message compréhensible","owner":"actor_jeremie"},{"task":"Évaluer compréhension et faux positifs","owner":"actor_elias"}]},
        {"case_id":"CASE-KF-GOV-001","title":"Pacte de gouvernance Kristal Farms","origin_world":"kristal-farms","origin_topic":"kf_governance","status":"open","mandate":"Définir vannes, consentement, droits de pause, réversibilité et responsabilités.","tasks":[{"task":"Rédiger garde-fous","owner":"actor_aida"},{"task":"Cartographier dépendances opérationnelles","owner":"actor_simon"},{"task":"Cartographier financement et risques de capture","owner":"actor_thomas_antoine"}]},
        {"case_id":"CASE-DESJARDINS-FUND-001","title":"Fonds commun kOA","origin_world":"desjardins","origin_topic":"common_fund","status":"open","mandate":"Simuler un mécanisme de financement coopératif transparent des projets communs.","tasks":[{"task":"Proposer mécanisme financier","owner":"actor_thomas_antoine"},{"task":"Définir limites et conflits","owner":"actor_aida"},{"task":"Créer workflow de décision/exécution","owner":"actor_simon"}]},
    ],
}


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _unwrap(value):
    if isinstance(value, dict) and value.get("ok") is True and "data" in value:
        return value["data"]
    return value


def _json_request(opener, method, url, *, body=None, headers=None, accepted=None, timeout=15):
    data = None
    h = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with opener.open(req, timeout=timeout) as response:
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")
            rh = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
        rh = dict(exc.headers.items())
    except OSError as exc:
        raise RuntimeError(f"{method} {url}: {exc}") from exc
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw[:1000]}
    ok = (200 <= status < 300) if accepted is None else status in accepted
    if not ok:
        raise RuntimeError(f"{method} {url} -> HTTP {status}: {json.dumps(payload, ensure_ascii=False)[:1500]}")
    return status, payload, rh


class OrgoClient:
    def __init__(self, base, organization, email, password):
        self.base = base.rstrip("/")
        self.organization = organization
        self.email = email
        self.password = password
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies), urllib.request.ProxyHandler({}))
        self.token = None

    def request(self, method, path, *, body=None, idem=None, accepted=None, timeout=15):
        headers = {}
        if self.token:
            headers["Authorization"] = "Bearer " + self.token
        if idem:
            headers["Idempotency-Key"] = idem
        status, payload, rh = _json_request(self.opener, method, self.base + path, body=body, headers=headers, accepted=accepted, timeout=timeout)
        return status, _unwrap(payload), rh

    def ready(self):
        try:
            status, payload, _ = self.request("GET", "/health/ready", timeout=3)
            return status == 200 and isinstance(payload, dict) and payload.get("status") == "ready"
        except Exception:
            return False

    def login(self):
        if self.password:
            try:
                _, data, _ = self.request("POST", "/api/v3/auth/login", body={"organization":self.organization,"email":self.email,"password":self.password})
                if isinstance(data, dict) and data.get("token"):
                    self.token = str(data["token"])
                    return "password"
            except Exception:
                pass
        try:
            self.request("POST", "/api/v3/auth/local-auto-login", body={})
            self.request("GET", "/api/v3/auth/me")
            return "local-auto-login"
        except Exception as exc:
            raise RuntimeError("Orgo est prêt, mais aucun login admin local n'a fonctionné (.env ou ORGO_LOCAL_AUTO_LOGIN).") from exc


def _slug(text):
    return re.sub(r"[^A-Za-z0-9._:-]+", "-", text).strip("-")[:120] or "item"


def _rows(client, kind, search):
    q = urllib.parse.urlencode({"search": search, "limit": 100, "offset": 0})
    _, data, _ = client.request("GET", f"/api/v3/{kind}?{q}")
    if isinstance(data, dict):
        values = data.get("items", [])
    elif isinstance(data, list):
        values = data
    else:
        values = []
    return [x for x in values if isinstance(x, dict)]


def _start_orgo(target, client):
    if client.ready():
        return True, "already-ready"
    if not shutil.which("docker"):
        return False, "Docker est requis pour démarrer Orgo localement."
    result = run_command(["docker","compose","up","-d","--build"], cwd=target, timeout_seconds=2400, capture_limit_kb=256)
    if result["timed_out"] or result["exit_code"] != 0:
        return False, "docker compose up a échoué: " + (result.get("stderr_tail") or result.get("stdout_tail") or "")[-1800:]
    seed = run_command(["docker","compose","--profile","setup","run","--rm","seed"], cwd=target, timeout_seconds=600, capture_limit_kb=128)
    if seed["timed_out"] or seed["exit_code"] != 0:
        return False, "Le seed administrateur Orgo a échoué: " + (seed.get("stderr_tail") or seed.get("stdout_tail") or "")[-1800:]
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        if client.ready():
            return True, "started"
        time.sleep(2)
    return False, "Orgo a démarré mais /health/ready n'est pas devenu READY."


def _inject(client):
    resolved = []
    tasks_count = 0
    for ci, source in enumerate(SEED["cases"]):
        matches = [r for r in _rows(client, "cases", source["title"])
                   if isinstance(r.get("metadata"), dict) and r["metadata"].get("source_case_id") == source["case_id"]]
        if len(matches) > 1:
            raise RuntimeError(f"Doublons Orgo pour {source['case_id']}")
        if matches:
            case = matches[0]
        else:
            metadata = {"seed_pack":"konvergence-koali","seed_version":"1.0.0","seed_source":"embedded:orgo/examples/cases.json","seed_contract":SEED["contract"],"source_case_id":source["case_id"],"origin_world":source["origin_world"],"origin_topic":source["origin_topic"],"source_status":source["status"]}
            if source.get("media_ref"):
                metadata["media_ref"] = source["media_ref"]
            _, case, _ = client.request("POST", "/api/v3/cases", body={"title":source["title"],"description":source["mandate"],"label":"1.11","severity":"MODERATE","source":"api","metadata":metadata,"visibility":"INTERNAL"}, idem=f"orgodiag-konvergence-case-{_slug(source['case_id'])}-v1")
        case_id = str(case.get("case_id") or case.get("id") or "")
        if not case_id:
            raise RuntimeError(f"Case sans case_id: {source['case_id']}")
        task_rows = []
        for ti, source_task in enumerate(source["tasks"]):
            tm = [r for r in _rows(client, "tasks", source_task["task"])
                  if isinstance(r.get("metadata"), dict)
                  and r["metadata"].get("source_case_id") == source["case_id"]
                  and r["metadata"].get("source_task_index") == ti]
            if len(tm) > 1:
                raise RuntimeError(f"Doublons Task pour {source['case_id']} #{ti+1}")
            if tm:
                task = tm[0]
            else:
                _, task, _ = client.request("POST", "/api/v3/tasks", body={"title":source_task["task"],"description":f"Tâche importée du seed Konvergence {source['case_id']}.","label":"1.11","severity":"MODERATE","source":"api","metadata":{"seed_pack":"konvergence-koali","seed_version":"1.0.0","source_case_id":source["case_id"],"origin_world":source["origin_world"],"origin_topic":source["origin_topic"],"source_task_index":ti,"konvergence_owner_ref":source_task.get("owner")},"visibility":"INTERNAL","type":"konvergence_seed","category":"request","case_id":case_id,"priority":"MEDIUM"}, idem=f"orgodiag-konvergence-task-{_slug(source['case_id'])}-{ti+1:02d}-v1")
            task_rows.append(task)
            tasks_count += 1
        resolved.append({"source":source,"case":case,"tasks":task_rows,"case_index":ci})
    if len(resolved) != EXPECTED_CASES or tasks_count != EXPECTED_TASKS:
        raise RuntimeError(f"Injection incomplète: {len(resolved)} Cases / {tasks_count} Tasks")
    # fresh API verification
    vc = vt = 0
    for item in resolved:
        source = item["source"]
        if len([r for r in _rows(client,"cases",source["title"]) if isinstance(r.get("metadata"),dict) and r["metadata"].get("source_case_id") == source["case_id"]]) == 1:
            vc += 1
        for ti, st in enumerate(source["tasks"]):
            if len([r for r in _rows(client,"tasks",st["task"]) if isinstance(r.get("metadata"),dict) and r["metadata"].get("source_case_id") == source["case_id"] and r["metadata"].get("source_task_index") == ti]) == 1:
                vt += 1
    if (vc, vt) != (EXPECTED_CASES, EXPECTED_TASKS):
        raise RuntimeError(f"Vérification API: {vc}/{EXPECTED_CASES} Cases, {vt}/{EXPECTED_TASKS} Tasks")
    return resolved


def _ensure_playwright(tool, report):
    browser = tool / "browser"
    cli = browser / "node_modules" / "@playwright" / "test" / "cli.js"
    if cli.is_file():
        return cli
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError("Node.js/npm est requis pour la preuve UI Playwright.")
    install = run_command([npm,"install","--no-audit","--no-fund"], cwd=browser, timeout_seconds=1200, capture_limit_kb=256)
    if install["timed_out"] or install["exit_code"] != 0 or not cli.is_file():
        raise RuntimeError("Installation Playwright échouée: " + (install.get("stderr_tail") or install.get("stdout_tail") or "")[-1600:])
    chromium = run_command([node,str(cli),"install","chromium"], cwd=browser, timeout_seconds=1200, capture_limit_kb=256)
    if chromium["timed_out"] or chromium["exit_code"] != 0:
        raise RuntimeError("Installation Chromium Playwright échouée: " + (chromium.get("stderr_tail") or chromium.get("stdout_tail") or "")[-1600:])
    return cli


def _playwright(tool, cfg, report, web_url, run_artifact):
    cli = _ensure_playwright(tool, report)
    out = run_artifact / "playwright"
    out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({
        "ORGO_E2E_URL": web_url,
        "ORGO_E2E_ORGANIZATION": str(cfg.get("_target_env_browser_organization") or "orgo"),
        "ORGO_E2E_EMAIL": str(cfg.get("_target_env_browser_email") or "admin@example.test"),
        "ORGO_E2E_PASSWORD": str(cfg.get("_target_env_browser_password") or "local-auto-login"),
        "ORGO_E2E_ALLOW_WRITES": "test-instance",
        "ORGO_E2E_JSON": str(out / "results.json"),
        "ORGO_E2E_HTML": str(out / "html"),
        "ORGO_E2E_RESULTS": str(out / "artifacts"),
        "ORGO_ECOSYSTEM_SCREENSHOT": str(out / "orgo-cases.png"),
    })
    result = run_command(["node",str(cli),"test","ecosystem.spec.ts","--project=chromium"], cwd=tool / "browser", timeout_seconds=420, capture_limit_kb=256, env=env)
    report.artifact("ecosystem-playwright-html", out / "html" / "index.html", "Focused Orgo ecosystem UI proof")
    shot = out / "orgo-cases.png"
    if shot.is_file(): report.artifact("ecosystem-orgo-screenshot", shot, "Orgo Cases after Konvergence injection")
    if result["timed_out"] or result["exit_code"] != 0:
        raise RuntimeError("Playwright Orgo UI a échoué: " + (result.get("stderr_tail") or result.get("stdout_tail") or "")[-2200:])


def _python312_base():
    candidates = []
    if os.name == "nt" and shutil.which("py"):
        candidates.append([shutil.which("py"), "-3.12"])
    p = shutil.which("python3.12")
    if p: candidates.append([p])
    if sys.version_info[:2] == (3,12): candidates.append([sys.executable])
    for cmd in candidates:
        cp = subprocess.run(cmd + ["-c","import sys; assert sys.version_info[:2]==(3,12)"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if cp.returncode == 0: return cmd
    return None


def _kor_python(cfg, kor_root, report):
    candidates = [kor_root/".venv"/"Scripts"/"python.exe", kor_root/"venv"/"Scripts"/"python.exe"] if os.name == "nt" else [kor_root/".venv"/"bin"/"python", kor_root/"venv"/"bin"/"python"]
    for p in candidates:
        if p.is_file():
            cp = subprocess.run([str(p),"-c","import fastapi,uvicorn,cryptography,jsonschema"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if cp.returncode == 0: return str(p)
    managed = Path(cfg["_control_root"]) / "runtime" / "kor-python312"
    py = managed / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if py.is_file():
        cp = subprocess.run([str(py),"-c","import fastapi,uvicorn,cryptography,jsonschema"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if cp.returncode == 0: return str(py)
    base = _python312_base()
    if not base:
        raise RuntimeError("Python 3.12 est requis par Kor et n'a pas été trouvé.")
    managed.parent.mkdir(parents=True, exist_ok=True)
    cp = subprocess.run(base + ["-m","venv",str(managed)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if cp.returncode != 0: raise RuntimeError("Création du runtime Python 3.12 Kor échouée: " + cp.stdout[-1500:])
    pip = [str(py),"-m","pip","install","--disable-pip-version-check",str(kor_root)]
    cp = subprocess.run(pip, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=1200)
    if cp.returncode != 0: raise RuntimeError("Installation locale de Kor échouée: " + cp.stdout[-1800:])
    return str(py)


def _free_port(preferred=8080):
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred)); return preferred
        except OSError:
            pass
    with socket.socket() as s:
        s.bind(("127.0.0.1",0)); return int(s.getsockname()[1])


def _start_kor(cfg, report, run_artifact, kor_root):
    py = _kor_python(cfg, kor_root, report)
    runtime = run_artifact / "kor-local"
    runtime.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["KOR_CONTRACTS"] = str(kor_root)
    env["PYTHONPATH"] = str(kor_root/"src") + os.pathsep + env.get("PYTHONPATH","")
    init = subprocess.run([py,"-m","kor_service.cli","init-local","--directory",str(runtime)], cwd=str(kor_root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if init.returncode != 0:
        raise RuntimeError("Initialisation Kor locale échouée: " + init.stdout[-1800:])
    token = (runtime/"token.txt").read_text(encoding="utf-8").strip()
    env.update({"KOR_AUTH_FILE":str(runtime/"auth.json"),"KOR_ENCRYPTION_KEY_FILE":str(runtime/"data.key"),"KOR_DATABASE":str(runtime/"kor.sqlite3")})
    port = _free_port(KOR_PORT)
    flags = getattr(subprocess,"CREATE_NO_WINDOW",0) if os.name == "nt" else 0
    proc = subprocess.Popen([py,"-m","kor_service.cli","serve","--host","127.0.0.1","--port",str(port)], cwd=str(kor_root), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", creationflags=flags)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic()+35
    while time.monotonic()<deadline:
        if proc.poll() is not None:
            tail = proc.stdout.read()[-2000:] if proc.stdout else ""
            raise RuntimeError("Kor service s'est arrêté: " + tail)
        try:
            _, payload, _ = _json_request(opener,"GET",f"http://127.0.0.1:{port}/health/ready",timeout=2)
            if isinstance(payload,dict) and payload.get("status") == "ready":
                return proc, token, port
        except Exception:
            pass
        time.sleep(.5)
    proc.terminate()
    raise RuntimeError("Kor service n'est pas devenu READY.")


def _world_title(ref):
    return {"amusement-kreative":"Amusement Kreative","orgo-events":"Orgo Events","kristal-farms":"Kristal Farms","desjardins":"Desjardins"}.get(ref, ref.replace("-"," ").title())


def _surface(item, world_index):
    source, case, tasks = item["source"], item["case"], item["tasks"]
    case_id = str(case.get("case_id") or case.get("id"))
    sid = "orgo-case-" + source["case_id"].lower()
    entries=[]
    for i,(src,row) in enumerate(zip(source["tasks"],tasks)):
        task_id=str(row.get("task_id") or row.get("id") or f"{source['case_id']}-{i}")
        entries.append({"item_ref":f"orgo:task:{task_id}","title":src["task"],"meta":f"Owner source: {src.get('owner') or 'non assigné'}","revision":int(row.get("revision") or 0)})
    created=str(case.get("created_at") or _now()); updated=str(case.get("updated_at") or created)
    return {"surface_specversion":"kor.surface/1.2","surface_id":sid,"owner":{"system":"orgo","surface_ref":f"orgo:case:{case_id}"},"audience":{"subject_ref":KOR_SUBJECT,"locale":"fr-CA"},"world":{"world_ref":source["origin_world"],"title":_world_title(source["origin_world"])},"navigation":{"destination_ref":f"orgo:case:{case_id}","stable_key":_slug(source["case_id"]).lower(),"label":source["title"][:80],"icon":"work","group":"Konvergence","order":world_index,"primary":world_index==0,"primary_candidate":True,"parent_surface_ref":None},"presentation":{"title":source["title"],"announcement":source["mandate"],"body":f"Seed Konvergence · {source['case_id']} · topic={source['origin_topic']} · status={source['status']}"},"intent":"coordinate","revision":int(case.get("revision") or 0),"updated_at":updated,"freshness":{"policy":"informational","observed_at":updated,"stale_after":None,"expires_at":None},"attention":{"kind":"informational","priority_band":1,"required":False,"unread":True,"changed":True,"badge":str(len(entries)),"reason":"Données injectées depuis Konvergence"},"promotion":{"eligible":True,"placements":["home_primary"] if world_index==0 else ["section_attention"],"owner_weight":0,"reason":"Seed E2E Konvergence"},"stats":[{"label":"Statut source","value":str(source["status"])},{"label":"Tâches","value":str(len(entries))}],"items":entries,"blocks":[{"block_id":"tasks","kind":"list","title":"Tasks","revision":int(case.get("revision") or 0),"owner_ref":f"orgo:case:{case_id}","data":{"items":entries,"empty_text":"Aucune tâche"},"content_locale":"fr-CA"}],"created_at":created,"expires_at":None}


def _publish_surfaces(resolved, token, port):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({})); base=f"http://127.0.0.1:{port}"; expected=set(); counters={}
    for item in resolved:
        world=item["source"]["origin_world"]; wi=counters.get(world,0); counters[world]=wi+1
        surface=_surface(item,wi); sid=surface["surface_id"]; expected.add(sid)
        status, _old, rh = _json_request(opener,"GET",f"{base}/v1/mobile/surfaces/{urllib.parse.quote(sid)}",headers={"Authorization":"Bearer "+token},accepted=(200,404),timeout=5)
        rev = rh.get("ETag", rh.get("Etag", '"0"')).strip('"') if status==200 else "0"
        _json_request(opener,"PUT",f"{base}/v1/mobile/surfaces/{urllib.parse.quote(sid)}",body=surface,headers={"Authorization":"Bearer "+token,"If-Match":rev},timeout=10)
    _, page, _ = _json_request(opener,"GET",f"{base}/v1/sync/mobile-surfaces?cursor=0&limit=200",headers={"Authorization":"Bearer "+token},timeout=10)
    ids={str(x.get("surface_id")) for x in page.get("items",[]) if isinstance(x,dict) and not x.get("deleted")}
    missing=expected-ids
    if missing: raise RuntimeError("Surfaces absentes du sync Kor: "+", ".join(sorted(missing)))
    return expected


def _sdk_tool(name):
    direct=shutil.which(name)
    if direct: return direct
    suffix=".exe" if os.name=="nt" else ""
    for var in ("ANDROID_HOME","ANDROID_SDK_ROOT"):
        root=os.getenv(var)
        if root:
            candidates=[Path(root)/"platform-tools"/(name+suffix),Path(root)/"emulator"/(name+suffix)]
            for c in candidates:
                if c.is_file(): return str(c)
    if os.name=="nt":
        root=Path(os.getenv("LOCALAPPDATA",""))/"Android"/"Sdk"
        for c in (root/"platform-tools"/(name+suffix),root/"emulator"/(name+suffix)):
            if c.is_file(): return str(c)
    return None


def _adb_devices(adb):
    cp=subprocess.run([adb,"devices"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
    return [line.split()[0] for line in cp.stdout.splitlines()[1:] if len(line.split())>=2 and line.split()[1]=="device"]


def _android_device(mode, run_artifact):
    adb=_sdk_tool("adb")
    if not adb: raise RuntimeError("ADB introuvable. Android SDK Platform Tools est requis.")
    devices=_adb_devices(adb)
    if mode=="physical":
        physical=[x for x in devices if not x.startswith("emulator-")]
        if not physical: raise RuntimeError("Aucun smartphone physique autorisé en ADB.")
        return adb, physical[0], None
    emus=[x for x in devices if x.startswith("emulator-")]
    proc=None
    if not emus:
        emulator=_sdk_tool("emulator")
        if not emulator: raise RuntimeError("Android Emulator introuvable.")
        ls=subprocess.run([emulator,"-list-avds"],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding="utf-8",errors="replace")
        avds=[x.strip() for x in ls.stdout.splitlines() if x.strip()]
        if not avds: raise RuntimeError("Aucun AVD Android n'est configuré. Crée un émulateur une seule fois dans Android Studio Device Manager.")
        log=(run_artifact/"emulator.log").open("w",encoding="utf-8")
        proc=subprocess.Popen([emulator,"-avd",avds[0],"-no-snapshot-save"],stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0) if os.name=="nt" else 0)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline:
            emus=[x for x in _adb_devices(adb) if x.startswith("emulator-")]
            if emus: break
            time.sleep(2)
        if not emus: raise RuntimeError("L'émulateur Android ne s'est pas enregistré dans ADB.")
    serial=emus[0]
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        cp=subprocess.run([adb,"-s",serial,"shell","getprop","sys.boot_completed"],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8",errors="replace")
        if cp.stdout.strip()=="1": return adb,serial,proc
        time.sleep(2)
    raise RuntimeError("L'émulateur Android n'a pas terminé son démarrage.")


def _adb(adb,serial,*args,binary=False,timeout=30):
    return subprocess.run([adb,"-s",serial,*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=not binary,encoding=None if binary else "utf-8",errors=None if binary else "replace",timeout=timeout)


def _dump_ui(adb,serial,artifact):
    _adb(adb,serial,"shell","uiautomator","dump","/sdcard/orgodiag-ui.xml",timeout=20)
    cp=_adb(adb,serial,"shell","cat","/sdcard/orgodiag-ui.xml",timeout=20)
    text=cp.stdout if cp.returncode==0 else ""
    artifact.write_text(text,encoding="utf-8")
    return text


def _center(bounds):
    m=re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]",bounds or "")
    if not m: return None
    x1,y1,x2,y2=map(int,m.groups()); return (x1+x2)//2,(y1+y2)//2


def _tap_node(adb,serial,node):
    c=_center(node.attrib.get("bounds"));
    if not c: return False
    return _adb(adb,serial,"shell","input","tap",str(c[0]),str(c[1]),timeout=10).returncode==0


def _connect_android(adb,serial,mode,token,port,run_artifact):
    if mode=="physical":
        cp=_adb(adb,serial,"reverse",f"tcp:{port}",f"tcp:{port}",timeout=15)
        if cp.returncode!=0: raise RuntimeError("adb reverse a échoué: "+cp.stderr)
        base=f"http://127.0.0.1:{port}"
    else:
        base=f"http://10.0.2.2:{port}"
    time.sleep(2)
    xml=_dump_ui(adb,serial,run_artifact/"android-before.xml")
    if not xml: raise RuntimeError("Impossible de lire l'UI Android.")
    root=ET.fromstring(xml)
    edits=[n for n in root.iter() if n.attrib.get("class") in {"android.widget.EditText","android.widget.AutoCompleteTextView"}]
    # If sign-in is visible, fill development credentials. First field may already contain emulator default.
    if len(edits)>=2:
        _tap_node(adb,serial,edits[0])
        for _ in range(80): _adb(adb,serial,"shell","input","keyevent","67",timeout=5)
        _adb(adb,serial,"shell","input","text",base,timeout=15)
        _tap_node(adb,serial,edits[1]); _adb(adb,serial,"shell","input","text",token,timeout=15)
        time.sleep(.5)
        xml=_dump_ui(adb,serial,run_artifact/"android-login.xml"); root=ET.fromstring(xml)
        buttons=[n for n in root.iter() if n.attrib.get("clickable")=="true"]
        connect=next((n for n in buttons if any(k in ((n.attrib.get("text") or "")+" "+(n.attrib.get("content-desc") or "")).lower() for k in ("connect","se connecter"))),None)
        if connect is None:
            # Compose can expose text on a child; choose the last large clickable node in sign-in form.
            connect=buttons[-1] if buttons else None
        if not connect or not _tap_node(adb,serial,connect): raise RuntimeError("Bouton de connexion Kor Android introuvable.")
        time.sleep(4)
    return base


def _build_install_android(kor_root, adb, serial, base):
    gradle=kor_root/"android"/("gradlew.bat" if os.name=="nt" else "gradlew")
    if not gradle.is_file(): raise RuntimeError("Gradle wrapper Kor Android introuvable.")
    env=os.environ.copy(); env["KOR_SERVICE_BASE_URL"]=base
    result=run_command([str(gradle),":app:assembleDebug"],cwd=kor_root/"android",timeout_seconds=1800,capture_limit_kb=256,env=env)
    if result["timed_out"] or result["exit_code"]!=0: raise RuntimeError("Build Kor Android échoué: "+(result.get("stderr_tail") or result.get("stdout_tail") or "")[-2000:])
    apk=kor_root/"android"/"app"/"build"/"outputs"/"apk"/"debug"/"app-debug.apk"
    if not apk.is_file(): raise RuntimeError("APK debug Kor introuvable après build.")
    cp=_adb(adb,serial,"install","-r",str(apk),timeout=180)
    if cp.returncode!=0: raise RuntimeError("Installation APK Kor échouée: "+(cp.stderr or cp.stdout))
    # Clean-room mobile proof: stale Room rows from a prior E2E must never satisfy this run.
    _adb(adb,serial,"shell","pm","clear",KOR_PACKAGE,timeout=30)
    _adb(adb,serial,"shell","monkey","-p",KOR_PACKAGE,"-c","android.intent.category.LAUNCHER","1",timeout=20)


def _read_phone_ids(adb,serial):
    remote=f"databases/{ANDROID_DB}"
    cp=_adb(adb,serial,"exec-out","run-as",KOR_PACKAGE,"cat",remote,binary=True,timeout=20)
    if cp.returncode!=0 or not cp.stdout: return set()
    with tempfile.TemporaryDirectory(prefix="orgodiag-android-") as td:
        root=Path(td); db=root/ANDROID_DB; db.write_bytes(cp.stdout)
        for suffix in ("-wal","-shm"):
            part=_adb(adb,serial,"exec-out","run-as",KOR_PACKAGE,"cat",remote+suffix,binary=True,timeout=20)
            if part.returncode==0 and part.stdout: (root/(ANDROID_DB+suffix)).write_bytes(part.stdout)
        conn=sqlite3.connect(str(db))
        try:
            names={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            table="mobile_surfaces" if "mobile_surfaces" in names else next((x for x in names if "mobile" in x.lower() and "surface" in x.lower()),None)
            if not table: return set()
            return {str(r[0]) for r in conn.execute(f'SELECT id FROM "{table}"').fetchall()}
        finally: conn.close()


def _tap_sync(adb,serial,run_artifact):
    xml=_dump_ui(adb,serial,run_artifact/"android-sync.xml")
    if not xml: return False
    root=ET.fromstring(xml)
    for n in root.iter():
        text=((n.attrib.get("text") or "")+" "+(n.attrib.get("content-desc") or "")).lower()
        if any(x in text for x in ("synchroniser","synchronize","sync","refresh")) and n.attrib.get("clickable")=="true":
            return _tap_node(adb,serial,n)
    return False


def _android_verify(kor_root, expected, token, port, mode, run_artifact, report):
    adb,serial,_emu=_android_device(mode,run_artifact)
    base=f"http://127.0.0.1:{port}" if mode=="physical" else f"http://10.0.2.2:{port}"
    if mode=="physical": _adb(adb,serial,"reverse",f"tcp:{port}",f"tcp:{port}",timeout=15)
    _build_install_android(kor_root,adb,serial,base)
    _connect_android(adb,serial,mode,token,port,run_artifact)
    deadline=time.monotonic()+90; ids=set()
    while time.monotonic()<deadline:
        ids=_read_phone_ids(adb,serial)
        if expected.issubset(ids): break
        _tap_sync(adb,serial,run_artifact)
        time.sleep(4)
    shot=_adb(adb,serial,"exec-out","screencap","-p",binary=True,timeout=20)
    if shot.returncode==0 and shot.stdout:
        p=run_artifact/"android.png"; p.write_bytes(shot.stdout); report.artifact("ecosystem-android-screenshot",p,"Kor Android after mobile sync")
    xml=_dump_ui(adb,serial,run_artifact/"android-final.xml")
    report.artifact("ecosystem-android-ui",run_artifact/"android-final.xml","Android accessibility tree after sync")
    missing=expected-ids
    if missing: raise RuntimeError(f"Android n'a synchronisé que {len(expected)-len(missing)}/{len(expected)} surfaces; manquantes: {', '.join(sorted(missing))}")
    visible=sum(1 for case in SEED["cases"] if case["title"] in xml)
    if visible < 1: raise RuntimeError("Les surfaces sont dans Room, mais aucun Case Konvergence n'est rendu dans l'UI Android visible.")
    return serial, len(ids), visible


def run(cfg, report):
    if os.environ.get("ORGO_ECOSYSTEM_APPROVED") != "1":
        report.add("ecosystem.approval","BLOCKED","policy","La campagne Écosystème doit être lancée depuis l'action dédiée OrgoDiag.")
        return
    target=Path(cfg["_target_root"]); tool=Path(cfg["_tool_root"])
    eco=cfg.get("ecosystem",{}) if isinstance(cfg.get("ecosystem"),dict) else {}
    kor_root=Path(os.environ.get("ORGO_ECOSYSTEM_KOR_ROOT") or eco.get("kor_repo_root") or r"C:\mycode\Kor\kor")
    mode=os.environ.get("ORGO_ECOSYSTEM_ANDROID_MODE","emulator").strip().lower()
    mode="physical" if mode=="physical" else "emulator"
    api=str(eco.get("orgo_api_url") or "http://127.0.0.1:4000").rstrip("/")
    web=str(eco.get("orgo_web_url") or "http://127.0.0.1:3000").rstrip("/")
    organization=str(cfg.get("_target_env_browser_organization") or "orgo")
    email=str(cfg.get("_target_env_browser_email") or "admin@example.test")
    password=str(cfg.get("_target_env_browser_password") or "")
    run_artifact=Path(cfg["_control_root"])/"runs"/report.run_id/"ecosystem"
    run_artifact.mkdir(parents=True,exist_ok=True)
    report.metrics.update({"expected_cases":EXPECTED_CASES,"expected_tasks":EXPECTED_TASKS,"android_mode":mode,"kor_root":str(kor_root)})

    client=OrgoClient(api,organization,email,password)
    ok,state=_start_orgo(target,client)
    if not ok:
        report.add("ecosystem.orgo.runtime","BLOCKED","runtime",state); return
    report.add("ecosystem.orgo.runtime","PASS","runtime",f"Orgo API READY ({state}).",evidence={"api":api})
    try:
        auth=client.login()
        resolved=_inject(client)
    except Exception as exc:
        report.add("ecosystem.orgo.data","FAIL","orgo",str(exc)); return
    report.add("ecosystem.orgo.data","PASS","orgo",f"Konvergence est présent dans Orgo: {EXPECTED_CASES} Cases / {EXPECTED_TASKS} Tasks.",evidence={"cases":[x["source"]["case_id"] for x in resolved],"auth":auth})

    try:
        _playwright(tool,cfg,report,web,run_artifact)
        report.add("ecosystem.orgo.ui","PASS","browser","Playwright voit les 5 Cases et les 19 Tasks injectés dans l'UI Orgo.")
    except Exception as exc:
        report.add("ecosystem.orgo.ui","FAIL","browser",str(exc)); return

    if not kor_root.is_dir() or not (kor_root/"pyproject.toml").is_file():
        report.add("ecosystem.kor.runtime","BLOCKED","configuration",f"Repo Kor introuvable: {kor_root}"); return
    proc=None
    try:
        proc,token,port=_start_kor(cfg,report,run_artifact,kor_root)
        report.add("ecosystem.kor.runtime","PASS","runtime",f"Kor Service READY sur 127.0.0.1:{port}.")
        expected=_publish_surfaces(resolved,token,port)
        report.add("ecosystem.kor.projection","PASS","kor",f"{len(expected)} surfaces mobiles Orgo sont publiées et présentes dans /v1/sync/mobile-surfaces.",evidence={"surface_ids":sorted(expected)})
        try:
            serial,total,visible=_android_verify(kor_root,expected,token,port,mode,run_artifact,report)
            report.add("ecosystem.android","PASS","android",f"Kor Android a synchronisé {len(expected)}/{len(expected)} surfaces; rendu UI confirmé.",evidence={"device":serial,"cached_surfaces":total,"visible_expected_titles":visible,"mode":mode})
            report.add("ecosystem.correlation","PASS","e2e",f"Corrélation complète: {EXPECTED_CASES} Cases / {EXPECTED_TASKS} Tasks / {len(expected)} surfaces jusque dans Android.")
        except Exception as exc:
            report.add("ecosystem.android","FAIL","android",str(exc)); return
    except Exception as exc:
        report.add("ecosystem.kor.runtime","FAIL","kor",str(exc)); return
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try: proc.wait(timeout=5)
            except Exception: proc.kill()
