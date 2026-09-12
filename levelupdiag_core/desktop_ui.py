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
from .test_runtime import TestRuntime

COLORS = {'PASS':'#178054', 'WARN':'#a16b08', 'FAIL':'#c0353e', 'BLOCKED':'#96630f',
          'ERROR':'#c0353e', 'INFRA_ERROR':'#c0353e', 'CONFIG_ERROR':'#c0353e', 'PARTIAL':'#96630f'}

class App(tk.Tk):
    def __init__(self, tool):
        super().__init__()
        self.tool = tool
        self.session = Session(tool)
        self.runtime = TestRuntime(tool)
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
        runtime_bar = ttk.Frame(outer); runtime_bar.pack(fill='x', pady=(10,0))
        self.prepare_database_button = ttk.Button(runtime_bar, text='Prepare PostgreSQL test', command=self.prepare_test_database)
        self.prepare_database_button.pack(side='left')
        self.start_runtime = ttk.Button(runtime_bar, text='Start Orgo test', command=self.start_test_runtime)
        self.start_runtime.pack(side='left', padx=(8,0))
        self.stop_runtime = ttk.Button(runtime_bar, text='Stop Orgo test', command=self.stop_test_runtime)
        self.stop_runtime.pack(side='left', padx=8)
        ttk.Button(runtime_bar, text='Runtime logs', command=self.open_runtime_logs).pack(side='left')
        self.runtime_status = tk.StringVar(value='Managed test PostgreSQL: existing orgo-test-postgres container. Prepare DB for deep/database; start runtime for browser.')
        ttk.Label(outer, textvariable=self.runtime_status, wraplength=1000).pack(anchor='w', pady=4)
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
        self.browser_tab = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.browser_tab, text='Browser settings')
        self.browser_url = tk.StringVar(value='http://127.0.0.1:3000')
        self.browser_org = tk.StringVar(value='orgo-e2e')
        self.browser_email = tk.StringVar(value='e2e@example.test')
        self.browser_password = tk.StringVar()
        self.browser_writes = tk.BooleanVar(value=False)
        self.browser_widgets = []
        self.browser_tab.columnconfigure(1, weight=1)
        for row, (label, variable) in enumerate([
            ('Local Orgo URL', self.browser_url), ('Test organization', self.browser_org),
            ('Test email', self.browser_email), ('Test password', self.browser_password),
        ]):
            ttk.Label(self.browser_tab, text=label).grid(row=row, column=0, sticky='w', padx=(0,12), pady=5)
            field = ttk.Entry(self.browser_tab, textvariable=variable,
                              show='•' if variable is self.browser_password else '')
            field.grid(row=row, column=1, sticky='ew', pady=5)
            self.browser_widgets.append(field)
        confirm = ttk.Checkbutton(self.browser_tab,
            text='This is a disposable test instance. Allow browser tests to create records.',
            variable=self.browser_writes)
        confirm.grid(row=4, column=0, columnspan=2, sticky='w', pady=10)
        self.browser_widgets.append(confirm)
        ttk.Label(self.browser_tab, wraplength=760, text=(
            'Install the Playwright overlay and Chromium first. PostgreSQL, the API and the frontend '
            'must already be running with the test database. These fields stay in memory and are '
            'passed only to the browser campaign. Failure traces can contain test credentials; keep them private.'
        )).grid(row=5, column=0, columnspan=2, sticky='w')
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
            'For database, deep or acceptance, use a dedicated database such as orgo_test. '
            'If your validated Docker container orgo-test-postgres exists, click Prepare PostgreSQL test; '
            'LevelUpDiag starts it, verifies its fixed test-only configuration and fills this field automatically.\n\n'
            'You may instead enter your own test URL, for example: '
            'postgresql://USER:PASSWORD@localhost:5432/orgo_test?connection_limit=5\n\n'
            'The URL stays in memory only. LevelUpDiag never falls back to DATABASE_URL.')

    def describe(self):
        self.description.set(self.manifest['campaigns'][self.campaign.get()].get('description',''))
        if self.campaign.get() == 'browser': self.tabs.select(self.browser_tab)

    def save(self):
        try:
            cfg = save_settings(self.tool,self.target.get(),self.mutation.get(),self.network.get())
            self.control = Path(cfg['_control_root']); self.status.set('Settings saved. The test database URL stays in memory only.')
            self.refresh(); return True
        except Exception as error:
            messagebox.showerror('Configuration',redact(str(error))); return False

    def run(self):
        if self.runtime.busy:
            messagebox.showinfo('Orgo startup', 'Wait for automatic startup or shutdown to finish.'); return
        if self.runtime.processes and self.campaign.get() in {'database', 'deep', 'acceptance'}:
            messagebox.showinfo('Native PostgreSQL validation',
                'Stop the Orgo API/web test runtime before running database/deep/acceptance on the same database.')
            return
        if self.session.running or not self.save(): return
        try:
            settings = dict(url=self.browser_url.get(), organization=self.browser_org.get(),
                            email=self.browser_email.get(), password=self.browser_password.get(),
                            allow_writes=self.browser_writes.get())
            self.session.start(self.campaign.get(),self.target.get(),self.database.get(), browser=settings)
            self.busy(True); self.status.set('Campaign running… Commands may take several minutes.')
            self.put(self.log,'\nCampaign: '+self.campaign.get()+'\n')
        except Exception as error: messagebox.showerror('Execution',redact(str(error)))

    def busy(self, active):
        for widget in (self.path_entry,self.browse,self.mutation_box,self.network_box,self.database_entry,self.save_button,self.run_button,self.prepare_database_button):
            widget.configure(state='disabled' if active else 'normal')
        self.combo.configure(state='disabled' if active else 'readonly')
        for widget in self.browser_widgets: widget.configure(state='disabled' if active else 'normal')
        if active: self.progress.start(15)
        else: self.progress.stop()

    def poll(self):
        try:
            while True:
                kind, value = self.runtime.events.get_nowait()
                if kind == 'database-ready':
                    self.database.set(value)
                    self.runtime_status.set('PostgreSQL test is ready; TEST_DATABASE_URL field filled for database/deep campaigns.')
                else:
                    if value: self.runtime_status.set(value)
                    if kind == 'error': messagebox.showerror('Orgo test runtime', value)
                    if kind == 'ready': self.browser_url.set('http://127.0.0.1:3000')
        except queue.Empty: pass
        running = self.session.running
        self.prepare_database_button.configure(state='disabled' if running or self.runtime.busy or self.runtime.processes else 'normal')
        self.start_runtime.configure(state='disabled' if running or self.runtime.busy or self.runtime.processes else 'normal')
        self.stop_runtime.configure(state='disabled' if running or not (self.runtime.busy or self.runtime.processes) else 'normal')
        if self.runtime.ready and any(p.poll() is not None for p in self.runtime.processes):
            self.runtime.ready = False
            self.runtime_status.set('An Orgo process exited. Check Runtime logs, then stop and restart Orgo test.')
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

    def prepare_test_database(self):
        if self.session.running: return
        try:
            self.runtime.prepare_database()
            self.runtime_status.set('Preparing PostgreSQL test…')
        except Exception as error:
            messagebox.showerror('PostgreSQL test', str(error))

    def start_test_runtime(self):
        if self.session.running: return
        try:
            self.runtime.start(self.target.get())
            self.runtime_status.set('Starting Orgo test…')
        except Exception as error: messagebox.showerror('Orgo test runtime', str(error))

    def stop_test_runtime(self):
        if self.session.running: return
        self.runtime_status.set('Stopping Orgo test…')
        self.runtime.stop()

    def open_runtime_logs(self):
        directory = self.runtime.log_dir
        if directory is None:
            messagebox.showinfo('Runtime logs', 'Start Orgo test first.'); return
        try:
            if os.name == 'nt': os.startfile(str(directory))
            else: subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', str(directory)])
        except OSError as error: messagebox.showerror('Runtime logs', str(error))

    def close(self):
        if self.session.running:
            messagebox.showinfo('Campaign running','Wait for the campaign to finish before closing the console.'); return
        if self.runtime.busy or self.runtime.processes:
            messagebox.showinfo('Orgo test runtime', 'Click Stop Orgo test and wait for shutdown before closing the console. PostgreSQL will remain available.'); return
        self.database.set(''); self.browser_password.set(''); self.destroy()

def main(tool):
    App(tool).mainloop()
