import customtkinter as ctk
import sqlite3
import datetime
import os
import requests
import threading
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLOR_BG = "#1A1A1A"
COLOR_PANEL = "#2B2B2B"
COLOR_PRIMARY = "#0A84FF"
COLOR_ACCENT = "#FF375F"
COLOR_TEXT = "#FFFFFF"
COLOR_SUCCESS = "#30D158"

USER_NAME = "ZEHRAOUI MOHAMED"
USER_TITLE = "VIDEO EDITOR"
USER_PHONE = "0675904170"
USER_EMAIL = "zehraoui.mohamed.oul.hocine@gmail.com"
USER_LOC = "Tizi Ouzou, Algérie"

# --- CONFIGURATION CLOUD ---
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwunRc6J-wNNEXfHNUWI5iBGjtkYzR88m3Ee6rI8sC-m1OcNoBqPiose7a50SyZBf86/exec"

def envoyer_vers_drive(data_dict):
    try:
        requests.post(GOOGLE_SCRIPT_URL, json=data_dict)
        print("☁️ Cloud: Envoi réussi !")
    except Exception as e:
        print(f"☁️ Cloud: Erreur ({e})")

def sync_from_cloud():
    try:
        response = requests.get(GOOGLE_SCRIPT_URL)
        data = response.json()
        conn = sqlite3.connect("mz_manager.db")
        cursor = conn.cursor()
        count = 0
        for row in data:
            nom = row.get('Projet')
            is_paye = 1 if row.get('Paye') == "OUI" else 0
            is_livre = 1 if row.get('Livre') == "OUI" else 0
            cursor.execute("UPDATE projets SET est_paye=?, est_livre=? WHERE nom_projet=?", (is_paye, is_livre, nom))
            count += 1
        conn.commit()
        conn.close()
        print(f"✅ Synchro terminée : {count}")
        return True
    except Exception as e:
        print(f"❌ Erreur Sync: {e}")
        return False

class DBManager:
    def __init__(self, db_name="mz_manager.db"):
        self.db_name = db_name
        self.init_tables()

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def init_tables(self):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS photographes (id INTEGER PRIMARY KEY AUTOINCREMENT, nom TEXT NOT NULL, telephone TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS projets (id INTEGER PRIMARY KEY AUTOINCREMENT, photographe_id INTEGER, nom_projet TEXT, date_depot TEXT, date_creation TEXT, type_projet TEXT, prix REAL, est_paye INTEGER DEFAULT 0, est_livre INTEGER DEFAULT 0, FOREIGN KEY(photographe_id) REFERENCES photographes(id) ON DELETE CASCADE)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS historique (id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, details TEXT, date_heure TEXT)''')
        conn.commit()
        conn.close()

    def log_action(self, action, details):
        conn = self.get_connection()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn.execute("INSERT INTO historique (action, details, date_heure) VALUES (?, ?, ?)", (action, details, now))
        conn.commit()
        conn.close()

db = DBManager()

class DateEntry(ctk.CTkFrame):
    def __init__(self, master, default_date=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        if default_date is None: default_date = datetime.date.today()
        self.entry_day = ctk.CTkEntry(self, width=40); self.entry_day.pack(side="left", padx=2); self.entry_day.insert(0, str(default_date.day))
        ctk.CTkLabel(self, text="/").pack(side="left")
        self.entry_month = ctk.CTkEntry(self, width=40); self.entry_month.pack(side="left", padx=2); self.entry_month.insert(0, str(default_date.month))
        ctk.CTkLabel(self, text="/").pack(side="left")
        self.entry_year = ctk.CTkEntry(self, width=60); self.entry_year.pack(side="left", padx=2); self.entry_year.insert(0, str(default_date.year))
    def get_date_str(self):
        try: return datetime.date(int(self.entry_year.get()), int(self.entry_month.get()), int(self.entry_day.get())).strftime("%Y-%m-%d")
        except: return None

class AddClientDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent); self.callback = callback; self.title("Client")
        self.geometry("400x250")
        ctk.CTkLabel(self, text="Nouveau Client", font=("Arial", 18)).pack(pady=20)
        self.ent_name = ctk.CTkEntry(self, placeholder_text="Nom"); self.ent_name.pack(pady=10)
        self.ent_phone = ctk.CTkEntry(self, placeholder_text="Tél"); self.ent_phone.pack(pady=10)
        ctk.CTkButton(self, text="Valider", command=self.on_confirm).pack(pady=20)
    def on_confirm(self):
        if self.ent_name.get(): self.callback(self.ent_name.get(), self.ent_phone.get()); self.destroy()

class AddProjectDialog(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent); self.callback = callback; self.title("Projet")
        self.geometry("500x350")
        grid = ctk.CTkFrame(self, fg_color="transparent"); grid.pack(pady=10)
        self.cb_type = ctk.CTkComboBox(grid, values=["Mariage", "Pub", "Shooting"]); self.cb_type.pack(pady=5)
        self.date_depot = DateEntry(grid); self.date_depot.pack(pady=5)
        self.ent_prix = ctk.CTkEntry(grid, placeholder_text="Prix"); self.ent_prix.pack(pady=5)
        self.ent_proj = ctk.CTkEntry(self, placeholder_text="Nom Projet"); self.ent_proj.pack(pady=5)
        ctk.CTkButton(self, text="Ajouter", command=self.on_confirm).pack(pady=10)
    def on_confirm(self):
        try: self.callback(self.ent_proj.get(), self.cb_type.get(), self.date_depot.get_date_str(), float(self.ent_prix.get())); self.destroy()
        except: pass

class MZEditorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("MZ EDITOR"); self.geometry("1200x800")
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0); self.sidebar.grid(row=0, column=0, sticky="nsew")
        ctk.CTkButton(self.sidebar, text="Dashboard", command=lambda: self.show("Dash")).pack(pady=10)
        ctk.CTkButton(self.sidebar, text="Projets", command=lambda: self.show("Proj")).pack(pady=10)
        self.frames = {"Dash": DashboardView(self, self), "Proj": ProjectManagerView(self, self)}
        self.frames["Dash"].grid(row=0, column=1, sticky="nsew")
        self.frames["Proj"].grid(row=0, column=1, sticky="nsew")
        self.show("Dash")
    def show(self, name): self.frames[name].tkraise(); self.frames[name].update_view()

class DashboardView(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master)
        ctk.CTkButton(self, text="Actualiser", command=self.refresh).pack(pady=20)
        self.lbl = ctk.CTkLabel(self, text="Dashboard", font=("Arial", 24)); self.lbl.pack()
    def update_view(self): pass
    def refresh(self): threading.Thread(target=self._run_sync).start()
    def _run_sync(self): sync_from_cloud()

class ProjectManagerView(ctk.CTkFrame):
    def __init__(self, master, controller):
        super().__init__(master); self.controller = controller; self.cid = None
        self.grid_columnconfigure(1, weight=1); self.grid_rowconfigure(0, weight=1)
        self.left = ctk.CTkScrollableFrame(self, width=300); self.left.grid(row=0, column=0, sticky="nsew")
        ctk.CTkButton(self.left, text="+ Client", command=self.add_client).pack()
        self.right = ctk.CTkScrollableFrame(self); self.right.grid(row=0, column=1, sticky="nsew")
        ctk.CTkButton(self.right, text="+ Projet", command=self.add_proj).pack()
    
    def update_view(self): 
        for w in self.left.winfo_children(): 
            if isinstance(w, ctk.CTkButton) and w.cget("text") != "+ Client": w.destroy()
        conn = db.get_connection()
        for i, n in conn.execute("SELECT id, nom FROM photographes"):
            ctk.CTkButton(self.left, text=n, command=lambda x=i: self.load(x)).pack()
    
    def add_client(self): AddClientDialog(self, self.cb_add_client)
    def cb_add_client(self, n, t): 
        conn = db.get_connection(); conn.execute("INSERT INTO photographes (nom, telephone) VALUES (?,?)", (n,t)); conn.commit(); self.update_view()
    
    def add_proj(self): 
        if self.cid: AddProjectDialog(self, self.cb_add_proj)
    
    def cb_add_proj(self, n, t, d, p):
        conn = db.get_connection()
        conn.execute("INSERT INTO projets (photographe_id, nom_projet, date_depot, type_projet, prix) VALUES (?,?,?,?,?)", (self.cid, n, d, t, p))
        c_nom = conn.execute("SELECT nom FROM photographes WHERE id=?", (self.cid,)).fetchone()[0]
        conn.commit()
        data = {"action": "create", "client": c_nom, "projet": n, "type": t, "prix": p, "paye": "NON", "livre": "NON"}
        threading.Thread(target=envoyer_vers_drive, args=(data,)).start()
        self.load(self.cid)

    def load(self, cid):
        self.cid = cid
        for w in self.right.winfo_children(): 
            if isinstance(w, ctk.CTkFrame): w.destroy()
        conn = db.get_connection()
        for row in conn.execute("SELECT * FROM projets WHERE photographe_id=?", (cid,)):
            f = ctk.CTkFrame(self.right); f.pack(fill="x", pady=5)
            ctk.CTkLabel(f, text=row[2]).pack(side="left")
            ctk.CTkLabel(f, text=f"{row[6]} DA").pack(side="right")

if __name__ == "__main__":
    app = MZEditorApp()
    app.mainloop()