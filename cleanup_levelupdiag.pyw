# cleanup_levelupdiag.pyw
# Nettoyage ciblé des fichiers/répertoires indésirables dans LevelUpDiag.
# À placer à la racine du repo, puis double-cliquer.
#
# Le script NE SORT PAS du dossier où il se trouve.
# Il demande confirmation avant toute suppression.

from pathlib import Path
import shutil
import tkinter as tk
from tkinter import messagebox, scrolledtext
import traceback

ROOT = Path(__file__).resolve().parent

# Cibles explicites connues
EXACT_RELATIVE_TARGETS = [
    Path(".levelupdiag-pack-backups"),
    Path("docs/KONNAXION_EXISTING_TOOL_MAPPING.md"),
    Path("docs/KONNAXION_MEGAPACK_ARCHITECTURE.md"),
    Path("konnaxion_diag"),
    Path("scripts/run_konnaxion.py"),
    Path("tests/test_megapack_imports.py"),
    Path("tests/test_source_audit.py"),
]

# Motifs ciblés
NAME_PATTERNS = (
    "konnaxion",
    "megapack",
)

CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

CACHE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def is_inside_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(ROOT.resolve())
        return True
    except Exception:
        return False


def collect_targets():
    targets = set()

    # Cibles exactes
    for rel in EXACT_RELATIVE_TARGETS:
        p = ROOT / rel
        if p.exists() or p.is_symlink():
            targets.add(p)

    # Scan récursif du repo
    for p in ROOT.rglob("*"):
        if not is_inside_root(p):
            continue

        name_lower = p.name.lower()

        # Caches Python / test / lint
        if p.is_dir() and p.name in CACHE_DIR_NAMES:
            targets.add(p)
            continue

        if p.is_file() and p.suffix.lower() in CACHE_FILE_SUFFIXES:
            targets.add(p)
            continue

        # Launchers KX-*.bat
        if p.is_file() and p.name.lower().startswith("kx-") and p.suffix.lower() == ".bat":
            targets.add(p)
            continue

        # Fichiers/répertoires avec noms explicitement contaminés
        if any(pattern in name_lower for pattern in NAME_PATTERNS):
            targets.add(p)

    # Évite de supprimer deux fois les enfants d'un dossier déjà ciblé.
    ordered = sorted(targets, key=lambda x: (len(x.parts), str(x).lower()))
    filtered = []

    for p in ordered:
        if any(parent == p or parent in p.parents for parent in filtered):
            continue
        filtered.append(p)

    return filtered


def display_path(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except Exception:
        return str(p)


def delete_path(p: Path):
    if not is_inside_root(p):
        raise RuntimeError(f"Refus de supprimer hors du dossier racine : {p}")

    if p.is_symlink() or p.is_file():
        p.unlink(missing_ok=True)
    elif p.is_dir():
        shutil.rmtree(p)


def run_cleanup():
    targets = collect_targets()

    if not targets:
        messagebox.showinfo(
            "LevelUpDiag Cleanup",
            "Aucun fichier ciblé n'a été trouvé.\n\nLe dossier semble déjà propre."
        )
        refresh_preview()
        return

    preview = "\n".join(display_path(p) for p in targets)

    answer = messagebox.askyesno(
        "Confirmer le nettoyage",
        "Les éléments suivants vont être supprimés définitivement :\n\n"
        f"{preview}\n\n"
        "Continuer ?"
    )

    if not answer:
        return

    deleted = []
    errors = []

    for p in targets:
        try:
            delete_path(p)
            deleted.append(display_path(p))
        except Exception as exc:
            errors.append(f"{display_path(p)} : {exc}")

    log_path = ROOT / "cleanup_levelupdiag.log"
    try:
        with log_path.open("w", encoding="utf-8") as f:
            f.write("LevelUpDiag cleanup\n")
            f.write(f"Racine : {ROOT}\n\n")
            f.write("Supprimé :\n")
            for item in deleted:
                f.write(f"  - {item}\n")
            if errors:
                f.write("\nErreurs :\n")
                for item in errors:
                    f.write(f"  - {item}\n")
    except Exception:
        pass

    refresh_preview()

    if errors:
        messagebox.showwarning(
            "Nettoyage terminé avec erreurs",
            f"{len(deleted)} élément(s) supprimé(s).\n"
            f"{len(errors)} erreur(s).\n\n"
            f"Voir : {log_path.name}"
        )
    else:
        messagebox.showinfo(
            "Nettoyage terminé",
            f"{len(deleted)} élément(s) supprimé(s).\n\n"
            f"Journal : {log_path.name}"
        )


def refresh_preview():
    text.configure(state="normal")
    text.delete("1.0", tk.END)

    targets = collect_targets()

    text.insert(tk.END, f"Racine analysée :\n{ROOT}\n\n")

    if not targets:
        text.insert(tk.END, "Aucune cible trouvée.\n")
    else:
        text.insert(tk.END, f"{len(targets)} cible(s) trouvée(s) :\n\n")
        for p in targets:
            kind = "DOSSIER" if p.is_dir() else "FICHIER"
            text.insert(tk.END, f"[{kind}] {display_path(p)}\n")

    text.configure(state="disabled")


def main():
    global root, text

    root = tk.Tk()
    root.title("LevelUpDiag - Nettoyage ciblé")
    root.geometry("850x600")
    root.minsize(700, 450)

    header = tk.Label(
        root,
        text="Nettoyage ciblé LevelUpDiag",
        font=("Segoe UI", 14, "bold"),
        anchor="w"
    )
    header.pack(fill="x", padx=12, pady=(12, 4))

    info = tk.Label(
        root,
        text=(
            "Supprime uniquement les traces Konnaxion/Megapack/KX et les caches "
            "Python connus dans ce dossier."
        ),
        font=("Segoe UI", 9),
        anchor="w",
        justify="left",
        wraplength=800
    )
    info.pack(fill="x", padx=12, pady=(0, 8))

    text = scrolledtext.ScrolledText(
        root,
        wrap="none",
        font=("Consolas", 10)
    )
    text.pack(fill="both", expand=True, padx=12, pady=8)

    buttons = tk.Frame(root)
    buttons.pack(fill="x", padx=12, pady=(0, 12))

    tk.Button(
        buttons,
        text="Réanalyser",
        command=refresh_preview,
        width=16
    ).pack(side="left")

    tk.Button(
        buttons,
        text="SUPPRIMER LES CIBLES",
        command=run_cleanup,
        width=24
    ).pack(side="right")

    refresh_preview()
    root.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        try:
            messagebox.showerror("Erreur", err)
        except Exception:
            pass
