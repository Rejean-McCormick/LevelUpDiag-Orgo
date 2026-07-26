# -*- coding: utf-8 -*-
"""LevelUpDiag Wrapper GUI.

Reads levelupdiag_manifest.json + levelupdiag.config.local.json.
Lists levels and launches the selected .pyw as a separate process.
It does not import levels/*.pyw.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from levelupdiag_wrapper_common import (
    APP_NAME, APP_VERSION, control_dir, detect_diag_root, launch_level,
    load_config, load_manifest, open_path, config_path,
)

class Wrapper(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.diag_root = detect_diag_root()
        self.levels = load_manifest(self.diag_root)
        self.config = load_config(self.diag_root)
        self.selected = tk.StringVar(value=self.levels[0].id if self.levels else "")
        self.console_var = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Prêt")
        self.title(f"{APP_NAME} {APP_VERSION}")
        self.geometry("1120x720")
        self.minsize(960, 600)
        self._build()
        self._refresh_details()
        self.log(f"Root: {self.diag_root}")
        self.log(f"Config: {config_path(self.diag_root)}")

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        outer = ttk.Frame(self, padding=12)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(2, weight=1)
        ttk.Label(outer, text="LevelUpDiag", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        subtitle = f"{self.config.get('app_name', 'App')} — niveaux .pyw autonomes, config centrale"
        ttk.Label(outer, text=subtitle, foreground="#666666").grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 10))

        left = ttk.Frame(outer)
        left.grid(row=2, column=0, sticky="nsw", padx=(0, 10))
        left.rowconfigure(0, weight=1)
        self.listbox = tk.Listbox(left, width=38, exportselection=False)
        self.listbox.grid(row=0, column=0, sticky="ns")
        for lv in self.levels:
            self.listbox.insert("end", lv.display_title)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)
        if self.levels:
            self.listbox.selection_set(0)

        right = ttk.Frame(outer)
        right.grid(row=2, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)
        self.detail = tk.Text(right, height=8, wrap="word", font=("Consolas", 10))
        self.detail.grid(row=0, column=0, sticky="ew")
        self.detail.configure(state="disabled")
        bar = ttk.Frame(right)
        bar.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Button(bar, text="Lancer niveau", command=self.run_selected).pack(side="left")
        ttk.Checkbutton(bar, text="console", variable=self.console_var).pack(side="left", padx=8)
        ttk.Button(bar, text="Ouvrir config", command=self.open_config).pack(side="left", padx=4)
        ttk.Button(bar, text="Ouvrir artefacts", command=lambda: open_path(control_dir(self.diag_root) / "diagnostics")).pack(side="left", padx=4)
        ttk.Button(bar, text="Recharger", command=self.reload).pack(side="left", padx=4)
        ttk.Label(right, textvariable=self.status).grid(row=2, column=0, sticky="w")
        log_frame = ttk.LabelFrame(right, text="Log wrapper")
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, wrap="word", font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scroll.set)

    def _on_select(self, _event=None) -> None:
        idxs = self.listbox.curselection()
        if idxs:
            self.selected.set(self.levels[idxs[0]].id)
            self._refresh_details()

    def _current_level(self):
        for lv in self.levels:
            if lv.id == self.selected.get():
                return lv
        return self.levels[0] if self.levels else None

    def _refresh_details(self) -> None:
        lv = self._current_level()
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if lv:
            text = (
                f"{lv.display_title}\n"
                f"Fichier: {lv.file}\n"
                f"But: {lv.purpose}\n"
                f"Pré-requis: {lv.requirements_label()}\n"
                f"Bloquant release: {'oui' if lv.blocking_for_release else 'non'}\n"
            )
            self.detail.insert("end", text)
        self.detail.configure(state="disabled")

    def run_selected(self) -> None:
        lv = self._current_level()
        if not lv:
            return
        try:
            proc = launch_level(self.diag_root, lv, console=self.console_var.get())
            self.log(f"Launched {lv.id}: PID {proc.pid} — {lv.file}")
            self.status.set(f"Lancé: {lv.id}")
        except Exception as exc:
            self.log(f"FAIL launch {lv.id}: {exc}")
            messagebox.showerror(APP_NAME, str(exc))

    def open_config(self) -> None:
        path = config_path(self.diag_root)
        if not path.exists():
            messagebox.showwarning(APP_NAME, f"Config introuvable: {path}")
            return
        if __import__('os').name == 'nt':
            __import__('os').startfile(str(path))  # type: ignore[attr-defined]
        else:
            open_path(path.parent)

    def reload(self) -> None:
        self.levels = load_manifest(self.diag_root)
        self.config = load_config(self.diag_root)
        self.listbox.delete(0, "end")
        for lv in self.levels:
            self.listbox.insert("end", lv.display_title)
        if self.levels:
            self.listbox.selection_set(0)
            self.selected.set(self.levels[0].id)
        self._refresh_details()
        self.log("Manifest/config rechargés")

    def log(self, message: str) -> None:
        import time
        self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see("end")

if __name__ == "__main__":
    Wrapper().mainloop()
