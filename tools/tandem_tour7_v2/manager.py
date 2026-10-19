"""Tandem Tour 7 / LevelUpDiag — guarded preview/install/verify/rollback.

No Docker, Orgo API, DB, VPS or network calls. Tests run against a disposable
copy of the archived source snapshot with the overlay applied.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import zipfile

PACK = Path(__file__).resolve().parent
BUNDLE = PACK / 'baseline_snapshot.zip'
MANIFEST = PACK / 'manifest.json'
PAYLOAD = PACK / 'payload'


def die(message):
    raise RuntimeError(message)


def digest(data: bytes):
    return hashlib.sha256(data).hexdigest()


def read_manifest():
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if m.get('format') != 'koa.tandem.levelupdiag-tour7.v2':
        die('Format de manifeste inconnu')
    if digest(BUNDLE.read_bytes()) != m.get('snapshot_sha256'):
        die('Archive de reference modifiee')
    return m


def safe_target(repo: Path, rel: str):
    p = PurePosixPath(rel)
    if not rel or p.is_absolute() or any(x in {'..', '.', ''} for x in p.parts) or '\\' in rel or ':' in rel:
        die('Chemin invalide: ' + rel)
    target = repo.joinpath(*p.parts)
    parent = repo
    for part in p.parts[:-1]:
        parent = parent / part
        if parent.is_symlink():
            die('Lien symbolique de repertoire interdit: ' + str(parent))
    if target.is_symlink() or not target.resolve(strict=False).is_relative_to(repo.resolve()):
        die('Chemin hors depot ou lien symbolique: ' + rel)
    return target


def root_check(repo: Path):
    if not repo.is_dir() or not all((repo / x).is_file() for x in ('levelupdiag.py','levelupdiag_manifest.json','levelupdiag_core/cli.py')):
        die('Mauvaise racine. Attendu: C:\\mycode\\Orgo\\LevelUpDiag-Orgo (contient levelupdiag.py)')


def inspect(repo: Path, m):
    state = {}
    for rel, meta in m['files'].items():
        target = safe_target(repo, rel)
        staged = PACK / 'payload' / rel
        if not staged.is_file() or digest(staged.read_bytes()) != meta['new_sha256']:
            die('Fichier livre manquant ou modifie: ' + rel)
        old = meta['old_sha256']
        if not target.exists():
            status = 'READY' if old is None else 'CONFLICT'
        elif not target.is_file():
            status = 'CONFLICT'
        else:
            current = digest(target.read_bytes())
            status = 'ALREADY_UPDATED' if current == meta['new_sha256'] else ('READY' if current == old else 'CONFLICT')
        state[rel] = status
        print(f'[{status}] {rel}')
    return state


def run_tests(m):
    print('[TEST] Suite Python complete dans une copie isolee du snapshot; sans Orgo, DB, Docker, VPS ni reseau ...', flush=True)
    with tempfile.TemporaryDirectory(prefix='levelup-tour7-check-') as temp:
        candidate = Path(temp) / 'repo'
        candidate.mkdir()
        with zipfile.ZipFile(BUNDLE) as z:
            for item in z.infolist():
                rel = item.filename
                if not rel or rel.endswith('/'):
                    continue
                p = PurePosixPath(rel)
                if p.is_absolute() or '..' in p.parts or '\\' in rel or ':' in rel:
                    die('Chemin dangereux dans archive de reference')
                target = candidate.joinpath(*p.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(item))
        for rel in m['files']:
            target = safe_target(candidate, rel)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(PAYLOAD / rel, target)
        commands = [
            [sys.executable, '-m', 'compileall', '-q', 'levelupdiag_core', 'tests'],
            [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'],
            [sys.executable, 'levelupdiag.py', 'list'],
        ]
        for cmd in commands:
            cp = subprocess.run(cmd, cwd=candidate, stdin=subprocess.DEVNULL, shell=False,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                errors='replace', timeout=90, check=False)
            if cp.returncode != 0:
                print(cp.stdout[-8000:])
                die(f'Echec de validation isolee: {cmd[1:]} (code {cp.returncode})')
            if 'unittest' in cmd:
                print(cp.stdout[-1200:].strip(), flush=True)
        print('[PASS] Tests Python, compilation et manifeste du diagnostic', flush=True)


def backup_root(repo: Path):
    return repo.parent / 'Tandem_Local' / 'levelupdiag_tour_p1_v2' / 'backups'


def installer(repo: Path, m, statuses):
    if all(v == 'ALREADY_UPDATED' for v in statuses.values()):
        print('[OK] Lot deja installe, aucune modification')
        run_tests(m)
        return
    if any(v != 'READY' for v in statuses.values()):
        die('Snapshot divergent ou installation partielle: aucun fichier modifie')
    run_tests(m)
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = backup_root(repo) / stamp
    if backup.exists():
        die('Nom de sauvegarde deja utilise')
    backup.mkdir(parents=True, exist_ok=False)
    saved = {}
    try:
        for rel, meta in m['files'].items():
            path = safe_target(repo, rel)
            if meta['old_sha256'] is not None:
                b = safe_target(backup, rel)
                b.parent.mkdir(parents=True, exist_ok=True)
                data = path.read_bytes()
                if digest(data) != meta['old_sha256']:
                    die('Fichier modifie pendant la sauvegarde: ' + rel)
                b.write_bytes(data)
                saved[rel] = True
            else:
                if path.exists():
                    die('Fichier ajoute par un tiers avant installation: ' + rel)
                saved[rel] = False
        (backup / 'rollback.json').write_text(json.dumps({'format':m['format'], 'files':m['files'], 'saved':saved},indent=2)+'\n',encoding='utf-8')
        written = []
        try:
            for rel, meta in m['files'].items():
                path = safe_target(repo, rel)
                if meta['old_sha256'] is not None and digest(path.read_bytes()) != meta['old_sha256']:
                    die('Modification concurrente: ' + rel)
                if meta['old_sha256'] is None and path.exists():
                    die('Modification concurrente: ' + rel)
                path.parent.mkdir(parents=True, exist_ok=True)
                stage = path.with_name(path.name + '.tandem7.tmp')
                if stage.exists():
                    die('Fichier temporaire preexistant: ' + str(stage))
                try:
                    stage.write_bytes((PAYLOAD / rel).read_bytes())
                    os.replace(stage, path)
                finally:
                    if stage.exists(): stage.unlink()
                written.append(rel)
            result = inspect(repo, m)
            if not all(s == 'ALREADY_UPDATED' for s in result.values()):
                die('Verification des empreintes installees echouee')
        except BaseException:
            # Rollback only the files we actually wrote; never overwrite a concurrent edit.
            for rel in reversed(written):
                target = safe_target(repo, rel)
                meta = m['files'][rel]
                if target.is_file() and digest(target.read_bytes()) == meta['new_sha256']:
                    if saved[rel]:
                        shutil.copyfile(safe_target(backup, rel), target)
                    else:
                        target.unlink()
            raise
    except BaseException:
        print('[REFUS] Installation interrompue; retour automatique des fichiers deja ecrits si les empreintes sont intactes')
        raise
    print('[OK] Tour 7/8 installe. Sauvegarde: ' + str(backup))
    print('[INFO] Aucune campagne Orgo, application, DB, environnement VPS ni donnees FakePlant touches')


def rollback(repo: Path, m):
    backups = sorted((x for x in backup_root(repo).glob('*') if (x / 'rollback.json').is_file()), reverse=True)
    if not backups:
        die('Aucune sauvegarde valide trouvee pour ce lot')
    backup = backups[0]
    info = json.loads((backup / 'rollback.json').read_text(encoding='utf-8'))
    if info.get('format') != m['format'] or info.get('files') != m['files']:
        die('Manifeste de rollback different du correctif')
    # Check every file before touching any file.
    for rel, meta in m['files'].items():
        target = safe_target(repo, rel)
        if not target.is_file() or digest(target.read_bytes()) != meta['new_sha256']:
            die('Refus rollback: fichier divergent: ' + rel)
        if info['saved'][rel]:
            b = safe_target(backup, rel)
            if not b.is_file() or digest(b.read_bytes()) != meta['old_sha256']:
                die('Refus rollback: sauvegarde corrompue: ' + rel)
    for rel in reversed(list(m['files'])):
        target = safe_target(repo, rel)
        if info['saved'][rel]:
            shutil.copyfile(safe_target(backup, rel), target)
        else:
            target.unlink()
    for rel, meta in m['files'].items():
        target = safe_target(repo, rel)
        if meta['old_sha256'] is None:
            if target.exists(): die('Rollback partiel: ' + rel)
        elif digest(target.read_bytes()) != meta['old_sha256']:
            die('Rollback non conforme: ' + rel)
    print('[OK] Retour arriere des fichiers du lot reussi. Sauvegarde preservee: ' + str(backup))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['preview','install','verify','rollback'])
    p.add_argument('--repo', type=Path, help='Override for offline installer validation only')
    args = p.parse_args()
    repo = (args.repo or PACK.parents[1]).resolve()
    print(f'=== LEVELUPDIAG-ORGO / TANDEM / TOUR 7 SUR 8 / {args.action.upper()} ===')
    print(f'[REPO] {repo}')
    print('[PORTEE] Code diagnostic local uniquement. Aucun PostgreSQL, Docker, Browser, service ou VPS touche')
    root_check(repo)
    m = read_manifest()
    if args.action == 'rollback':
        rollback(repo,m)
        return
    statuses = inspect(repo,m)
    if any(s == 'CONFLICT' for s in statuses.values()):
        die('Empreintes SHA-256 divergentes: refus fail-closed')
    if args.action == 'preview':
        print('[OK] Apercu lecture seule favorable')
    elif args.action == 'install':
        installer(repo,m,statuses)
    else:
        if not all(s == 'ALREADY_UPDATED' for s in statuses.values()):
            die('Correctif incomplet ou absent')
        run_tests(m)
        print('[OK] Sources et tests de diagnostic conformes; campagnes runtime Orgo non executees')


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, ValueError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        print('[ECHEC] ' + str(error), file=sys.stderr)
        sys.exit(1)
