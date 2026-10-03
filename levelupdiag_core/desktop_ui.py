"""OrgoDiag desktop console optimized for low-friction validation."""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .config import load_config
from .manifest import load_manifest
from .util import read_json, redact
from .desktop import Session, save_settings, history, report_path, browser_defaults_from_config
from .test_runtime import TestRuntime

COLORS = {
    'PASS':'#177a52','WARN':'#9a6700','FAIL':'#c13640','BLOCKED':'#9a6700',
    'ERROR':'#c13640','INFRA_ERROR':'#c13640','CONFIG_ERROR':'#c13640','PARTIAL':'#9a6700',
}

class App(tk.Tk):
    def __init__(self, tool):
        super().__init__()
        self.tool = Path(tool)
        self.session = Session(self.tool)
        self.runtime = TestRuntime(self.tool)
        self.manifest = load_manifest(self.tool)
        self.control = None
        self.selected = None
        self.summaries = []
        self.active_campaign = None

        self.title('OrgoDiag')
        self.geometry('1180x820')
        self.minsize(900, 650)
        self.configure(background='#eef2f6')
        self._style()

        self.target = tk.StringVar(value=r'C:\mycode\Orgo\Orgo')
        self.mutation = tk.BooleanVar(value=False)
        self.network = tk.BooleanVar(value=False)
        self.database = tk.StringVar()
        self.campaign = tk.StringVar(value='quick')
        self.physical = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Prêt.')
        self.runtime_status = tk.StringVar(value='')
        self.latest_verdict = tk.StringVar(value='—')
        self.latest_label = tk.StringVar(value='Aucune validation exécutée')
        self.kpi_pass = tk.StringVar(value='0')
        self.kpi_warn = tk.StringVar(value='0')
        self.kpi_fail = tk.StringVar(value='0')
        self.browser_url = tk.StringVar(value='http://127.0.0.1:3000')
        self.browser_org = tk.StringVar(value='orgo')
        self.browser_email = tk.StringVar(value='admin@example.test')
        self.browser_password = tk.StringVar()
        self.browser_writes = tk.BooleanVar(value=True)
        self.browser_env_target = None

        self._build()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self._load_initial()
        self.after(200, self.poll)

    def _style(self):
        style = ttk.Style(self)
        try: style.theme_use('clam')
        except tk.TclError: pass
        style.configure('TFrame', background='#eef2f6')
        style.configure('TLabel', background='#eef2f6', font=('Segoe UI',10))
        style.configure('TButton', padding=(12,8), font=('Segoe UI',10))
        style.configure('Hero.TLabel', font=('Segoe UI',24,'bold'), foreground='#172740')
        style.configure('Subtitle.TLabel', font=('Segoe UI',11), foreground='#4b5c70')
        style.configure('Verdict.TLabel', font=('Segoe UI',30,'bold'))
        style.configure('Primary.TButton', font=('Segoe UI',12,'bold'), padding=(18,14))
        style.configure('Treeview', rowheight=28, font=('Segoe UI',10))
        style.configure('Treeview.Heading', font=('Segoe UI',9,'bold'))

    def _build(self):
        outer = ttk.Frame(self, padding=18)
        outer.pack(fill='both', expand=True)

        head = ttk.Frame(outer)
        head.pack(fill='x')
        title = ttk.Frame(head); title.pack(side='left', fill='x', expand=True)
        ttk.Label(title, text='OrgoDiag', style='Hero.TLabel').pack(anchor='w')
        ttk.Label(title, text='Un verdict clair pour Orgo et son écosystème', style='Subtitle.TLabel').pack(anchor='w')
        ttk.Button(head, text='Rapports', command=self.open_reports).pack(side='right', padx=(8,0))

        action = ttk.LabelFrame(outer, text='Validation', padding=14)
        action.pack(fill='x', pady=(14,10))
        left = ttk.Frame(action); left.pack(side='left', fill='x', expand=True)
        self.orgo_button = ttk.Button(left, text='✓  VALIDER ORGO', style='Primary.TButton', command=lambda:self.run_primary('quick'))
        self.orgo_button.pack(side='left', fill='x', expand=True, padx=(0,8))
        self.eco_button = ttk.Button(left, text='◎  VALIDER ÉCOSYSTÈME', style='Primary.TButton', command=lambda:self.run_primary('ecosystem'))
        self.eco_button.pack(side='left', fill='x', expand=True, padx=(0,12))
        mode = ttk.Frame(action); mode.pack(side='right')
        ttk.Checkbutton(mode, text='Smartphone physique', variable=self.physical).pack(anchor='w')
        ttk.Label(mode, text='Décoché = émulateur Android').pack(anchor='w')

        summary = ttk.Frame(outer)
        summary.pack(fill='x', pady=(0,10))
        verdict_box = ttk.LabelFrame(summary, text='Dernier verdict', padding=(16,10))
        verdict_box.pack(side='left', fill='both', expand=True, padx=(0,8))
        self.verdict_label = ttk.Label(verdict_box, textvariable=self.latest_verdict, style='Verdict.TLabel')
        self.verdict_label.pack(anchor='w')
        ttk.Label(verdict_box, textvariable=self.latest_label, wraplength=520).pack(anchor='w')
        counts = ttk.LabelFrame(summary, text='Résumé', padding=(16,10))
        counts.pack(side='right', fill='both')
        ttk.Label(counts, text='PASS').grid(row=0,column=0,padx=10)
        ttk.Label(counts, text='WARN').grid(row=0,column=1,padx=10)
        ttk.Label(counts, text='FAIL').grid(row=0,column=2,padx=10)
        ttk.Label(counts, textvariable=self.kpi_pass, font=('Segoe UI',16,'bold')).grid(row=1,column=0,padx=10)
        ttk.Label(counts, textvariable=self.kpi_warn, font=('Segoe UI',16,'bold')).grid(row=1,column=1,padx=10)
        ttk.Label(counts, textvariable=self.kpi_fail, font=('Segoe UI',16,'bold')).grid(row=1,column=2,padx=10)

        self.progress = ttk.Progressbar(outer, mode='indeterminate')
        self.progress.pack(fill='x')
        ttk.Label(outer, textvariable=self.status, wraplength=1080).pack(anchor='w', pady=(6,8))

        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill='both', expand=True)
        self.summary_tab = ttk.Frame(self.tabs, padding=10)
        self.detail_tab = ttk.Frame(self.tabs, padding=10)
        self.log_tab = ttk.Frame(self.tabs, padding=10)
        self.advanced_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.summary_tab, text='Résumé')
        self.tabs.add(self.detail_tab, text='Détails')
        self.tabs.add(self.log_tab, text='Journal')
        self.tabs.add(self.advanced_tab, text='Avancé')

        self._build_summary_tab()
        self._build_detail_tab()
        self._build_log_tab()
        self._build_advanced_tab()

    def _build_summary_tab(self):
        top = ttk.Frame(self.summary_tab); top.pack(fill='x')
        ttk.Label(top, text='Exécution').pack(side='left', padx=(0,8))
        self.run_choice = ttk.Combobox(top, state='readonly')
        self.run_choice.pack(side='left', fill='x', expand=True)
        self.run_choice.bind('<<ComboboxSelected>>', self.select_run)
        self.summary_tree = ttk.Treeview(self.summary_tab, columns=('verdict','check','message'), show='headings', height=11)
        for col,label,width in [('verdict','Verdict',95),('check','Étape',250),('message','Résultat',650)]:
            self.summary_tree.heading(col,text=label); self.summary_tree.column(col,width=width,stretch=col=='message')
        for verdict,color in COLORS.items(): self.summary_tree.tag_configure(verdict, foreground=color)
        self.summary_tree.pack(fill='both', expand=True, pady=(10,0))
        self.summary_tree.bind('<Double-1>', lambda _e:self.tabs.select(self.detail_tab))

    def _build_detail_tab(self):
        self.level_tree = ttk.Treeview(self.detail_tab, columns=('level','verdict','name'), show='headings', height=7)
        for col,label,width in [('level','Niveau',70),('verdict','Verdict',100),('name','Contrôle',650)]:
            self.level_tree.heading(col,text=label); self.level_tree.column(col,width=width,stretch=col=='name')
        for verdict,color in COLORS.items(): self.level_tree.tag_configure(verdict, foreground=color)
        self.level_tree.pack(fill='x')
        self.level_tree.bind('<<TreeviewSelect>>', self.details)
        self.detail = self.textbox(self.detail_tab)

    def _build_log_tab(self):
        self.log = self.textbox(self.log_tab)

    def _build_advanced_tab(self):
        repo = ttk.LabelFrame(self.advanced_tab, text='Cible et permissions', padding=10)
        repo.pack(fill='x')
        repo.columnconfigure(1,weight=1)
        ttk.Label(repo,text='Orgo').grid(row=0,column=0,sticky='w',padx=(0,10),pady=4)
        self.path_entry=ttk.Entry(repo,textvariable=self.target); self.path_entry.grid(row=0,column=1,sticky='ew',pady=4)
        self.browse=ttk.Button(repo,text='Parcourir…',command=self.choose); self.browse.grid(row=0,column=2,padx=(8,0))
        self.mutation_box=ttk.Checkbutton(repo,text='Autoriser génération, tests et builds',variable=self.mutation); self.mutation_box.grid(row=1,column=1,sticky='w')
        self.network_box=ttk.Checkbutton(repo,text='Autoriser PostgreSQL natif / réseau',variable=self.network); self.network_box.grid(row=2,column=1,sticky='w')
        ttk.Label(repo,text='TEST_DATABASE_URL').grid(row=3,column=0,sticky='w',pady=4)
        self.database_entry=ttk.Entry(repo,textvariable=self.database,show='•'); self.database_entry.grid(row=3,column=1,sticky='ew',pady=4)
        self.save_button=ttk.Button(repo,text='Enregistrer',command=self.save); self.save_button.grid(row=3,column=2,padx=(8,0))

        runtime = ttk.LabelFrame(self.advanced_tab,text='Runtime de test',padding=10); runtime.pack(fill='x',pady=(10,0))
        self.prepare_database_button=ttk.Button(runtime,text='Préparer PostgreSQL test',command=self.prepare_test_database); self.prepare_database_button.pack(side='left')
        self.start_runtime=ttk.Button(runtime,text='Démarrer Orgo test',command=self.start_test_runtime); self.start_runtime.pack(side='left',padx=6)
        self.stop_runtime=ttk.Button(runtime,text='Arrêter Orgo test',command=self.stop_test_runtime); self.stop_runtime.pack(side='left')
        ttk.Button(runtime,text='Logs runtime',command=self.open_runtime_logs).pack(side='left',padx=6)
        ttk.Label(runtime,textvariable=self.runtime_status).pack(side='left',padx=12)

        manual = ttk.LabelFrame(self.advanced_tab,text='Campagnes manuelles',padding=10); manual.pack(fill='x',pady=(10,0))
        ttk.Label(manual,text='Campagne').pack(side='left')
        self.combo=ttk.Combobox(manual,textvariable=self.campaign,values=list(self.manifest['campaigns']),state='readonly',width=24); self.combo.pack(side='left',padx=8)
        self.run_button=ttk.Button(manual,text='Lancer',command=self.run); self.run_button.pack(side='left')

        browser=ttk.LabelFrame(self.advanced_tab,text='Compte navigateur (chargé depuis Orgo .env)',padding=10); browser.pack(fill='x',pady=(10,0)); browser.columnconfigure(1,weight=1)
        for row,(label,var) in enumerate([('URL',self.browser_url),('Organisation',self.browser_org),('Email',self.browser_email),('Mot de passe',self.browser_password)]):
            ttk.Label(browser,text=label).grid(row=row,column=0,sticky='w',pady=3,padx=(0,10))
            ttk.Entry(browser,textvariable=var,show='•' if var is self.browser_password else '').grid(row=row,column=1,sticky='ew',pady=3)

    def textbox(self,parent):
        frame=ttk.Frame(parent); frame.pack(fill='both',expand=True,pady=(8,0))
        text=tk.Text(frame,wrap='word',font=('Consolas',10),background='white',relief='flat',state='disabled')
        scroll=ttk.Scrollbar(frame,command=text.yview); text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); text.pack(fill='both',expand=True)
        return text

    def put(self,widget,text,clear=False):
        widget.configure(state='normal')
        if clear: widget.delete('1.0','end')
        widget.insert('end',redact(str(text)))
        if not str(text).endswith('\n'): widget.insert('end','\n')
        if int(widget.index('end-1c').split('.')[0])>1800: widget.delete('1.0','300.0')
        widget.see('end'); widget.configure(state='disabled')

    def _load_initial(self):
        try:
            cfg=load_config(self.tool)
            self.target.set(cfg['_target_root'])
            self.mutation.set(cfg['execution'].get('allow_target_mutation',False))
            self.network.set(cfg['execution'].get('allow_network',False))
            self.database.set(str(cfg.get('database',{}).get('test_database_url','') or ''))
            self.apply_browser_env_defaults(cfg,force=True)
            self.control=Path(cfg['_control_root'])
            self.refresh()
        except Exception as exc:
            self.status.set('Configuration à vérifier: '+redact(str(exc)))

    def apply_browser_env_defaults(self,cfg,force=False):
        target=str(cfg.get('_target_root','') or '')
        defaults=browser_defaults_from_config(cfg)
        if force or target!=self.browser_env_target:
            self.browser_org.set(defaults['organization']); self.browser_email.set(defaults['email']); self.browser_password.set(defaults['password']); self.browser_env_target=target
        elif not self.browser_password.get() and defaults['password']:
            self.browser_password.set(defaults['password'])

    def choose(self):
        folder=filedialog.askdirectory(title='Orgo repository root',initialdir=self.target.get() or str(self.tool.parent))
        if folder: self.target.set(folder)

    def save(self):
        try:
            cfg=save_settings(self.tool,self.target.get(),self.mutation.get(),self.network.get())
            self.apply_browser_env_defaults(cfg)
            if not self.database.get().strip(): self.database.set(str(cfg.get('database',{}).get('test_database_url','') or ''))
            self.control=Path(cfg['_control_root']); self.refresh(); return True
        except Exception as exc:
            messagebox.showerror('Configuration',redact(str(exc))); return False

    def _browser_settings(self,force_writes=False):
        return dict(url=self.browser_url.get(),organization=self.browser_org.get(),email=self.browser_email.get(),password=self.browser_password.get() or 'local-auto-login',allow_writes=True if force_writes else self.browser_writes.get())

    def run_primary(self,campaign):
        self.campaign.set(campaign)
        # The primary action itself is explicit consent for local validation work.
        # Quick needs generation/tests/build permission; ecosystem carries its own
        # focused one-run approval through Session without exposing extra toggles.
        if campaign == 'quick':
            self.mutation.set(True)
        self.run(campaign_override=campaign, primary=True)

    def run(self,campaign_override=None,primary=False):
        campaign=campaign_override or self.campaign.get()
        if self.runtime.busy:
            self.status.set('Le runtime est occupé; réessaie quand il a terminé.'); return
        if self.session.running: return
        if not self.save(): return
        try:
            ecosystem={'physical':self.physical.get(),'kor_root':self.manifest.get('ecosystem_kor_root')}
            self.session.start(campaign,self.target.get(),self.database.get(),browser=self._browser_settings(force_writes=campaign=='ecosystem'),ecosystem=ecosystem)
            self.active_campaign=campaign
            self.busy(True)
            self.status.set('Validation Écosystème en cours…' if campaign=='ecosystem' else f'Validation {campaign} en cours…')
            self.put(self.log,f'\n=== {campaign.upper()} ===\n')
            if primary: self.tabs.select(self.summary_tab)
        except Exception as exc:
            self.busy(False); self.status.set('Impossible de lancer: '+redact(str(exc)))

    def busy(self,active):
        state='disabled' if active else 'normal'
        for w in (self.orgo_button,self.eco_button,self.path_entry,self.browse,self.mutation_box,self.network_box,self.database_entry,self.save_button,self.run_button,self.prepare_database_button):
            try: w.configure(state=state)
            except tk.TclError: pass
        self.combo.configure(state='disabled' if active else 'readonly')
        if active: self.progress.start(12)
        else: self.progress.stop()

    def poll(self):
        try:
            while True:
                kind,value=self.runtime.events.get_nowait()
                if kind=='database-ready': self.database.set(value)
                if value: self.runtime_status.set(str(value))
        except queue.Empty: pass
        try:
            while True:
                kind,value=self.session.events.get_nowait()
                if kind=='log': self.put(self.log,value)
                else:
                    self.busy(False); self.refresh()
                    if kind=='done':
                        self.status.set('Validation terminée. Le verdict ci-dessus est la réponse.')
                        self.tabs.select(self.summary_tab)
                    else: self.status.set('Erreur: '+str(value))
                    self.active_campaign=None
        except queue.Empty: pass
        self.after(200,self.poll)

    def refresh(self):
        if not self.control: return
        self.summaries=history(self.control)
        self.run_choice['values']=[f"{s['run_id']} · {s.get('selection','')} · {s.get('verdict','')}" for s in self.summaries]
        if self.summaries:
            self.run_choice.current(0); self.select_run()
        else:
            self.latest_verdict.set('—'); self.latest_label.set('Aucune validation exécutée')

    def _set_verdict_color(self,verdict):
        color=COLORS.get(verdict,'#172740')
        ttk.Style(self).configure('Verdict.TLabel',foreground=color,font=('Segoe UI',30,'bold'))

    def select_run(self,event=None):
        idx=self.run_choice.current()
        if idx<0: return
        self.selected=self.summaries[idx]
        verdict=self.selected.get('verdict','—')
        self.latest_verdict.set(verdict); self._set_verdict_color(verdict)
        self.latest_label.set(f"{self.selected.get('selection','')} · {self.selected.get('run_id','')}")
        counts=self.selected.get('counts',{})
        self.kpi_pass.set(str(counts.get('PASS',0)))
        self.kpi_warn.set(str(sum(counts.get(x,0) for x in ('WARN','BLOCKED','PARTIAL','SKIP'))))
        self.kpi_fail.set(str(sum(counts.get(x,0) for x in ('FAIL','ERROR','INFRA_ERROR','CONFIG_ERROR'))))
        self.level_tree.delete(*self.level_tree.get_children())
        self.summary_tree.delete(*self.summary_tree.get_children())
        for i,row in enumerate(self.selected.get('levels',[])):
            self.level_tree.insert('', 'end', iid=str(i), values=(row['id'],row['verdict'],row.get('name','')), tags=(row['verdict'],))
        # Prefer finding-level summary for the ecosystem run; otherwise show levels.
        ecosystem_row=next((r for r in self.selected.get('levels',[]) if r.get('id')=='N16'),None)
        if ecosystem_row:
            try:
                data=read_json(report_path(self.control,self.selected['run_id'],ecosystem_row['result']))
                for i,f in enumerate(data.get('findings',[])):
                    v=f.get('verdict',''); self.summary_tree.insert('', 'end', iid=f'f{i}', values=(v,self._friendly_step(f.get('id','')),f.get('message','')),tags=(v,))
            except Exception: pass
        if not self.summary_tree.get_children():
            for i,row in enumerate(self.selected.get('levels',[])):
                v=row.get('verdict',''); self.summary_tree.insert('', 'end', iid=f'l{i}',values=(v,row.get('id',''),row.get('name','')),tags=(v,))
        self.put(self.detail,'Sélectionne un niveau pour voir les preuves détaillées.',clear=True)

    def _friendly_step(self,fid):
        mapping={
            'ecosystem.orgo.runtime':'Orgo runtime','ecosystem.orgo.data':'Konvergence → Orgo',
            'ecosystem.orgo.ui':'Orgo UI / Playwright','ecosystem.kor.runtime':'Kor Service',
            'ecosystem.kor.projection':'Orgo → Kor','ecosystem.android':'Android',
            'ecosystem.correlation':'Corrélation E2E','ecosystem.approval':'Autorisation',
        }
        return mapping.get(fid,fid)

    def details(self,event=None):
        sel=self.level_tree.selection()
        if not sel or not self.selected: return
        try:
            row=self.selected['levels'][int(sel[0])]
            data=read_json(report_path(self.control,self.selected['run_id'],row['result']))
            self.put(self.detail,json.dumps(data,ensure_ascii=False,indent=2),clear=True)
        except Exception as exc: self.put(self.detail,str(exc),clear=True)

    def open_reports(self):
        if not self.control or not self.control.exists():
            self.status.set('Aucun rapport disponible.'); return
        try:
            if os.name=='nt': os.startfile(str(self.control))
            else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(self.control)])
        except OSError as exc: self.status.set(str(exc))

    def prepare_test_database(self):
        if self.session.running: return
        try: self.runtime.prepare_database(); self.runtime_status.set('Préparation PostgreSQL test…')
        except Exception as exc: self.runtime_status.set(str(exc))

    def start_test_runtime(self):
        if self.session.running: return
        try: self.runtime.start(self.target.get()); self.runtime_status.set('Démarrage Orgo test…')
        except Exception as exc: self.runtime_status.set(str(exc))

    def stop_test_runtime(self):
        if self.session.running: return
        self.runtime_status.set('Arrêt Orgo test…'); self.runtime.stop()

    def open_runtime_logs(self):
        directory=self.runtime.log_dir
        if directory is None: self.runtime_status.set('Aucun runtime de test démarré.'); return
        try:
            if os.name=='nt': os.startfile(str(directory))
            else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(directory)])
        except OSError as exc: self.runtime_status.set(str(exc))

    def close(self):
        if self.session.running:
            self.status.set('Une validation est en cours; attends son verdict avant de fermer.'); return
        if self.runtime.busy or self.runtime.processes:
            self.runtime.stop()
        self.database.set(''); self.browser_password.set(''); self.destroy()


def main(tool):
    App(tool).mainloop()
