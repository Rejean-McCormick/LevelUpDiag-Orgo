"""Native desktop console inspired by the supplied LevelUpDiag configuration UI."""
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
from .desktop import Session, save_settings, history, report_path

COLORS = {'PASS':'#178054', 'WARN':'#a16b08', 'FAIL':'#c0353e', 'BLOCKED':'#96630f',
          'ERROR':'#c0353e', 'INFRA_ERROR':'#c0353e', 'CONFIG_ERROR':'#c0353e', 'PARTIAL':'#96630f'}

class App(tk.Tk):
    def __init__(self, tool):
        super().__init__()
        self.tool = tool
        self.session = Session(tool)
        self.manifest = load_manifest(tool)
        self.control = None
        self.selected = None
        self.summaries = []
        self.title('LevelUpDiag · Orgo')
        self.geometry('1120x800'); self.minsize(850, 640)
        self.configure(background='#edf1f7')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background='#edf1f7')
        style.configure('TLabel', background='#edf1f7', font=('Segoe UI', 10))
        style.configure('TButton', padding=(12, 7), font=('Segoe UI', 10))
        style.configure('Title.TLabel', font=('Segoe UI', 23, 'bold'), foreground='#172740')
        style.configure('Treeview', rowheight=29, font=('Segoe UI', 10))
        self.target = tk.StringVar(value=r'C:\mycode\Orgo\Orgo')
        self.mutation = tk.BooleanVar(value=False); self.network = tk.BooleanVar(value=False)
        self.database = tk.StringVar(); self.campaign = tk.StringVar(value='quick')
        self.status = tk.StringVar(value='Select the Orgo repository to get started.')
        self.description = tk.StringVar()
        outer = ttk.Frame(self, padding=22); outer.pack(fill='both', expand=True)
        ttk.Label(outer, text='LevelUpDiag / Orgo', style='Title.TLabel').pack(anchor='w')
        ttk.Label(outer, text='Configure · Run · Review results').pack(anchor='w', pady=(2,16))
        config = ttk.LabelFrame(outer, text='Repository and execution', padding=12); config.pack(fill='x')
        config.columnconfigure(1, weight=1)
        ttk.Label(config, text='Orgo repository').grid(row=0,column=0,sticky='w',padx=(0,12))
        self.path_entry = ttk.Entry(config, textvariable=self.target)
        self.path_entry.grid(row=0,column=1,sticky='ew')
        self.browse = ttk.Button(config,text='Browse…',command=self.choose)
        self.browse.grid(row=0,column=2,padx=(8,0))
        self.mutation_box = ttk.Checkbutton(config,text='Allow generation, tests and builds',variable=self.mutation)
        self.mutation_box.grid(row=1,column=1,sticky='w',pady=(8,0))
        self.network_box = ttk.Checkbutton(config,text='Allow native PostgreSQL / network audit',variable=self.network)
        self.network_box.grid(row=2,column=1,sticky='w')
        ttk.Label(config,text='Test database URL').grid(row=3,column=0,sticky='w',pady=8)
        self.database_entry = ttk.Entry(config,textvariable=self.database,show='•')
        self.database_entry.grid(row=3,column=1,sticky='ew',pady=8)
        ttk.Label(config,text='Leave empty for quick / embedded. Native PostgreSQL only; never use production.').grid(row=4,column=1,sticky='w')
        self.save_button = ttk.Button(config,text='Save settings',command=self.save)
        self.save_button.grid(row=3,column=2,padx=(8,0))
        ttk.Button(config,text='What is a test database?',command=self.database_help).grid(row=4,column=2,padx=(8,0))
        run = ttk.Frame(outer); run.pack(fill='x',pady=12)
        ttk.Label(run,text='Campaign').pack(side='left',padx=(0,10))
        self.combo = ttk.Combobox(run,textvariable=self.campaign,values=list(self.manifest['campaigns']),state='readonly',width=20)
        self.combo.pack(side='left'); self.combo.bind('<<ComboboxSelected>>',lambda _:self.describe())
        self.run_button = ttk.Button(run,text='▶ Run campaign',command=self.run)
        self.run_button.pack(side='left',padx=10)
        ttk.Button(run,text='Open reports',command=self.open_reports).pack(side='right')
        ttk.Label(outer,textvariable=self.description,wraplength=1000).pack(anchor='w',pady=(0,8))
        self.progress = ttk.Progressbar(outer,mode='indeterminate'); self.progress.pack(fill='x')
        ttk.Label(outer,textvariable=self.status,wraplength=1000).pack(anchor='w',pady=8)
        self.tabs = ttk.Notebook(outer); self.tabs.pack(fill='both',expand=True)
        result = ttk.Frame(self.tabs,padding=8); self.tabs.add(result,text='Results')
        self.run_choice = ttk.Combobox(result,state='readonly'); self.run_choice.pack(fill='x',pady=(0,8))
        self.run_choice.bind('<<ComboboxSelected>>',self.select_run)
        self.tree = ttk.Treeview(result,columns=('level','verdict','name'),show='headings',height=7)
        for col,label,width in [('level','Level',65),('verdict','Verdict',110),('name','Check',650)]:
            self.tree.heading(col,text=label); self.tree.column(col,width=width,stretch=col=='name')
        self.tree.pack(fill='x'); self.tree.bind('<<TreeviewSelect>>',self.details)
        for verdict,color in COLORS.items(): self.tree.tag_configure(verdict,foreground=color)
        self.detail = self.textbox(result)
        logs = ttk.Frame(self.tabs,padding=8); self.tabs.add(logs,text='Log')
        self.log = self.textbox(logs)
        ttk.Label(outer,text='Standalone application · Reports stay in LevelUpDiag · Final acceptance runs locally').pack(anchor='w',pady=(10,0))
        self.protocol('WM_DELETE_WINDOW',self.close)
        try:
            cfg = load_config(tool)
            self.target.set(cfg['_target_root'])
            self.mutation.set(cfg['execution'].get('allow_target_mutation',False))
            self.network.set(cfg['execution'].get('allow_network',False))
            self.control = Path(cfg['_control_root']); self.refresh()
        except (ValueError, RuntimeError, OSError): pass
        self.describe(); self.after(200,self.poll)

    def textbox(self, parent):
        box = ttk.Frame(parent); box.pack(fill='both',expand=True,pady=(8,0))
        text = tk.Text(box,wrap='word',height=8,font=('Consolas',10),background='#ffffff',relief='flat',state='disabled')
        scroll = ttk.Scrollbar(box,command=text.yview); text.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); text.pack(fill='both',expand=True)
        return text

    def put(self, widget, text, clear=False):
        widget.configure(state='normal')
        if clear: widget.delete('1.0','end')
        widget.insert('end',redact(text))
        if int(widget.index('end-1c').split('.')[0]) > 1500: widget.delete('1.0','300.0')
        widget.see('end'); widget.configure(state='disabled')

    def choose(self):
        folder = filedialog.askdirectory(title='Orgo repository root',initialdir=self.target.get() or str(self.tool.parent))
        if folder: self.target.set(folder)

    def database_help(self):
        messagebox.showinfo('Test database',
            'A separate, disposable PostgreSQL database used for migration and integration tests. '
            'It must not contain real or production data.\n\n'
            'Leave this field empty for quick and embedded. Embedded creates its own temporary database.\n\n'
            'For database, deep or acceptance, create a dedicated database such as orgo_test and enter its URL. '
            'Example: postgresql://USER:PASSWORD@localhost:5432/orgo_test?connection_limit=5\n\n'
            'Replace USER and PASSWORD with your test credentials. The console does not create a native '
            'PostgreSQL database. The URL is kept in memory only. If empty, TEST_DATABASE_URL is inherited.')

    def describe(self):
        self.description.set(self.manifest['campaigns'][self.campaign.get()].get('description',''))

    def save(self):
        try:
            cfg = save_settings(self.tool,self.target.get(),self.mutation.get(),self.network.get())
            self.control = Path(cfg['_control_root']); self.status.set('Settings saved. The test database URL stays in memory only.')
            self.refresh(); return True
        except Exception as error:
            messagebox.showerror('Configuration',redact(str(error))); return False

    def run(self):
        if self.session.running or not self.save(): return
        try:
            self.session.start(self.campaign.get(),self.target.get(),self.database.get())
            self.busy(True); self.status.set('Campaign running… Commands may take several minutes.')
            self.put(self.log,'\nCampaign: '+self.campaign.get()+'\n')
        except Exception as error: messagebox.showerror('Execution',redact(str(error)))

    def busy(self, active):
        for widget in (self.path_entry,self.browse,self.mutation_box,self.network_box,self.database_entry,self.save_button,self.run_button):
            widget.configure(state='disabled' if active else 'normal')
        self.combo.configure(state='disabled' if active else 'readonly')
        if active: self.progress.start(15)
        else: self.progress.stop()

    def poll(self):
        try:
            while True:
                kind,value = self.session.events.get_nowait()
                if kind == 'log': self.put(self.log,value)
                else:
                    self.busy(False); self.refresh()
                    self.status.set(('Campaign finished · exit code '+str(value)+' · review the verdicts') if kind=='done' else 'Error: '+str(value))
        except queue.Empty: pass
        self.after(200,self.poll)

    def refresh(self):
        if not self.control: return
        self.summaries = history(self.control)
        self.run_choice['values'] = [f"{s['run_id']} · {s.get('selection','')} · {s.get('verdict','')}" for s in self.summaries]
        if self.summaries: self.run_choice.current(0); self.select_run()

    def select_run(self, event=None):
        index = self.run_choice.current()
        if index < 0: return
        self.selected = self.summaries[index]
        self.tree.delete(*self.tree.get_children())
        for i,row in enumerate(self.selected.get('levels',[])):
            self.tree.insert('', 'end', iid=str(i),values=(row['id'],row['verdict'],row.get('name','')),tags=(row['verdict'],))
        self.put(self.detail,'Target: '+self.selected.get('target_repo_root','')+'\nSelect a level to view its evidence.',clear=True)

    def details(self, event=None):
        selection = self.tree.selection()
        if not selection or not self.selected: return
        try:
            row = self.selected['levels'][int(selection[0])]
            data = read_json(report_path(self.control,self.selected['run_id'],row['result']))
            self.put(self.detail,json.dumps(data,ensure_ascii=False,indent=2),clear=True)
        except Exception as error: self.put(self.detail,str(error),clear=True)

    def open_reports(self):
        if not self.control or not self.control.exists():
            messagebox.showinfo('Reports','No reports available. Save the target and run a campaign.'); return
        try:
            if os.name == 'nt': os.startfile(str(self.control))
            else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open',str(self.control)])
        except OSError as error: messagebox.showerror('Reports',str(error))

    def close(self):
        if self.session.running:
            messagebox.showinfo('Campaign running','Wait for the campaign to finish before closing the console.'); return
        self.database.set(''); self.destroy()

def main(tool):
    App(tool).mainloop()
