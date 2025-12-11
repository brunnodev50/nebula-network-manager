# -*- coding: utf-8 -*-
import customtkinter as ctk
import sqlite3
import subprocess
import socket
import threading
import uuid
import platform
import math
from datetime import datetime
from tkinter import filedialog, messagebox

# --- CONFIGURAÇÃO DE AMBIENTE ---
# Tentativa de importação de bibliotecas opcionais
try:
    import pandas as pd
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
except ImportError:
    pd = None

try:
    import speedtest
except ImportError:
    speedtest = None

# --- PALETA DE CORES "NEBULA" (Deep Space Theme) ---
C = {
    "bg_main":     "#09090b",  # Zinc 950 (Fundo Absoluto)
    "bg_side":     "#121215",  # Zinc 925 (Menu)
    "card_surf":   "#1d1e24",  # Surface (Cards)
    "card_hvr":    "#27272f",  # Surface Hover
    "primary":     "#6366f1",  # Indigo 500 (Destaque Principal)
    "secondary":   "#8b5cf6",  # Violet 500 (Gradiente Visual)
    "success":     "#10b981",  # Emerald 500
    "danger":      "#ef4444",  # Red 500
    "text_high":   "#ffffff",  # Texto Principal
    "text_med":    "#a1a1aa",  # Texto Secundário
    "border":      "#2e2e36",  # Borda Sutil
}

# Configuração Global
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- BACKEND ROBUSTO ---
class DatabaseEngine:
    def __init__(self, db_name="nebula_logs.db"):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("PRAGMA encoding = 'UTF-8';")
            conn.execute('''CREATE TABLE IF NOT EXISTS logs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            action_type TEXT, details TEXT,
                            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    def log(self, type_, details):
        threading.Thread(target=self._log_async, args=(type_, details)).start()

    def _log_async(self, type_, details):
        try:
            with sqlite3.connect(self.db_name) as conn:
                conn.execute("INSERT INTO logs (action_type, details) VALUES (?, ?)", (type_, details))
        except: pass

    def get_dataframe(self):
        if not pd: return None
        with sqlite3.connect(self.db_name) as conn:
            return pd.read_sql_query("SELECT * FROM logs ORDER BY id DESC", conn)

class NetworkCore:
    @staticmethod
    def get_info():
        try:
            host = socket.gethostname()
            return {
                "host": host,
                "ip": socket.gethostbyname(host),
                "mac": ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0,12,2)][::-1]).upper(),
                "os": f"{platform.system()} {platform.release()}"
            }
        except: return {"host": "?", "ip": "?", "mac": "?", "os": "?"}

    @staticmethod
    def run_cmd(cmd):
        try:
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # 'cp850' é o encoding padrão do CMD Windows PT-BR. 'replace' evita crash.
            out = subprocess.check_output(cmd, startupinfo=startup, shell=True, stderr=subprocess.STDOUT)
            return out.decode('cp850', errors='replace')
        except subprocess.CalledProcessError as e:
            return e.output.decode('cp850', errors='replace')
        except Exception as e: return str(e)

# --- UI COMPONENTS MODERNOS ---

class NebulaCard(ctk.CTkFrame):
    """Card com Design Glassmorphism e Ícone em Cápsula"""
    def __init__(self, parent, title, value, icon="🔹", icon_color=C["primary"]):
        super().__init__(parent, fg_color=C["card_surf"], corner_radius=16, 
                         border_width=1, border_color=C["border"])
        
        # Grid layout interno do card
        self.grid_columnconfigure(0, weight=0) # Ícone
        self.grid_columnconfigure(1, weight=1) # Texto
        
        # 1. Cápsula do Ícone (Um frame colorido arredondado)
        icon_frame = ctk.CTkFrame(self, width=50, height=50, corner_radius=12, fg_color=icon_color)
        icon_frame.grid(row=0, column=0, rowspan=2, padx=(15, 10), pady=15)
        icon_frame.grid_propagate(False) # Mantém tamanho fixo
        
        # Fonte segura para ícone
        font_icon = ("Segoe UI Emoji", 24) if platform.system() == "Windows" else ("Arial", 24)
        ctk.CTkLabel(icon_frame, text=icon, font=font_icon, text_color="#FFF").place(relx=0.5, rely=0.5, anchor="center")

        # 2. Textos
        ctk.CTkLabel(self, text=title.upper(), font=("Roboto Medium", 11), text_color=C["text_med"]).grid(row=0, column=1, sticky="sw", pady=(15, 0))
        
        # Tratamento de tamanho de fonte para valores longos
        val_font = ("Roboto", 18, "bold") if len(value) < 18 else ("Roboto", 14, "bold")
        ctk.CTkLabel(self, text=value, font=val_font, text_color=C["text_high"]).grid(row=1, column=1, sticky="nw", pady=(0, 15))

class NavButton(ctk.CTkButton):
    """Botão de Menu com indicador lateral"""
    def __init__(self, parent, text, icon, command, is_active=False):
        color = C["bg_side"] if not is_active else C["card_surf"]
        text_col = C["text_med"] if not is_active else C["primary"]
        font_icon = ("Segoe UI Emoji", 16) if platform.system() == "Windows" else ("Arial", 16)
        
        super().__init__(parent, text=f"  {icon}    {text}", command=command,
                         fg_color=color, hover_color=C["card_hvr"],
                         text_color=text_col, anchor="w",
                         font=("Roboto Medium", 14), height=48, corner_radius=8)
        self.configure(font=ctk.CTkFont(family="Roboto Medium", size=14)) # Hack para misturar icon/text se precisar

# --- APLICAÇÃO PRINCIPAL ---
class NebulaApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.db = DatabaseEngine()
        self.title("N E B U L A  |  Network Command Center")
        self.geometry("1100x720")
        self.configure(fg_color=C["bg_main"])
        
        # Layout Principal (Sidebar Fixa + Conteúdo Fluido)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.current_frame = None
        self._init_ui()
        self.navigate("dashboard")

    def _init_ui(self):
        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=C["bg_side"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Logo Area
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(40, 40))
        ctk.CTkLabel(logo_frame, text="⚡ NEBULA", font=("Montserrat", 26, "bold"), text_color=C["text_high"]).pack()
        # CORREÇÃO: Removido o argumento 'spacing' que causava o erro
        ctk.CTkLabel(logo_frame, text="NETWORK COMMAND", font=("Roboto", 10, "bold"), text_color=C["primary"]).pack()

        # Navigation
        self.nav_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.nav_container.pack(fill="x", padx=15)
        
        self.nav_buttons = {}
        opts = [("dashboard", "Dashboard", "📊"), 
                ("tools", "Rede & DNS", "🛠️"), 
                ("speed", "Speedtest", "🚀"), 
                ("logs", "Dados & Logs", "💾")]
        
        for key, name, icon in opts:
            btn = NavButton(self.nav_container, name, icon, lambda k=key: self.navigate(k))
            btn.pack(pady=4, fill="x")
            self.nav_buttons[key] = btn

        # Footer Version
        ctk.CTkLabel(self.sidebar, text="v4.5 Stable Release", font=("Consolas", 10), text_color=C["text_med"]).pack(side="bottom", pady=20)

        # --- MAIN AREA ---
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)
        self.main_area.grid_rowconfigure(1, weight=1) # Conteúdo expande
        self.main_area.grid_columnconfigure(0, weight=1)

        # Header Dinâmico
        self.lbl_title = ctk.CTkLabel(self.main_area, text="", font=("Roboto", 32, "bold"), text_color=C["text_high"])
        self.lbl_title.grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Content PlaceHolder
        self.content = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew")

    def navigate(self, page_key):
        # Atualiza estilo dos botões (Active State)
        for key, btn in self.nav_buttons.items():
            is_active = (key == page_key)
            btn.configure(fg_color=C["card_surf"] if is_active else "transparent",
                          text_color=C["primary"] if is_active else C["text_med"])

        # Troca Tela
        self.lbl_title.configure(text=page_key.capitalize())
        for widget in self.content.winfo_children(): widget.destroy()
        
        if page_key == "dashboard": self.view_dashboard()
        elif page_key == "tools": self.view_tools()
        elif page_key == "speed": self.view_speed()
        elif page_key == "logs": self.view_logs()

    # --- VIEWS (Páginas) ---

    def view_dashboard(self):
        self.lbl_title.configure(text="Visão Geral do Sistema")
        info = NetworkCore.get_info()
        self.db.log("NAV", "Dashboard visitado")

        # Configurar Grid Responsivo (2 colunas)
        self.content.grid_columnconfigure((0, 1), weight=1)
        
        # Cards
        NebulaCard(self.content, "Hostname", info['host'], "🖥️", "#3b82f6").grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        NebulaCard(self.content, "Sistema Operacional", info['os'], "⚙️", "#8b5cf6").grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        NebulaCard(self.content, "IPv4 Local", info['ip'], "📡", "#10b981").grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        NebulaCard(self.content, "Endereço MAC", info['mac'], "🔒", "#f59e0b").grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Banner Status
        banner = ctk.CTkFrame(self.content, fg_color="transparent", border_color=C["success"], border_width=1, corner_radius=12)
        banner.grid(row=2, column=0, columnspan=2, pady=30, sticky="ew")
        ctk.CTkLabel(banner, text="STATUS OPERACIONAL: ONLINE", font=("Roboto", 14, "bold"), text_color=C["success"]).pack(pady=15)

    def view_tools(self):
        self.lbl_title.configure(text="Ferramentas de Rede")
        
        # Grid de Comandos
        grid = ctk.CTkFrame(self.content, fg_color="transparent")
        grid.pack(fill="x", pady=(0, 20))
        grid.grid_columnconfigure((0,1,2), weight=1)
        
        cmds = [
            ("Flush DNS", "ipconfig /flushdns", "🧹"),
            ("Reg. DNS", "ipconfig /registerdns", "📝"),
            ("Release IP", "ipconfig /release", "🔌"),
            ("Renew IP", "ipconfig /renew", "🔋"),
            ("Ping Google", "ping 8.8.8.8", "🌐"),
            ("Ping Cloudflare", "ping 1.1.1.1", "☁️")
        ]

        for i, (name, cmd, icon) in enumerate(cmds):
            # Botão Estilizado
            font_emoji = ("Segoe UI Emoji", 14) if platform.system() == "Windows" else ("Arial", 14)
            btn = ctk.CTkButton(grid, text=f"{icon}  {name}", command=lambda c=cmd, n=name: self.exec_tool(c, n),
                                fg_color=C["card_surf"], hover_color=C["primary"], 
                                height=50, font=("Roboto Medium", 13), corner_radius=10)
            btn.grid(row=i//3, column=i%3, padx=6, pady=6, sticky="ew")

        # Terminal "Matrix" Style
        term_frame = ctk.CTkFrame(self.content, fg_color=C["bg_main"], corner_radius=12, border_width=1, border_color=C["border"])
        term_frame.pack(fill="both", expand=True)
        
        ctk.CTkLabel(term_frame, text=" TERMINAL OUTPUT", font=("Consolas", 11, "bold"), text_color=C["text_med"]).pack(anchor="w", padx=10, pady=5)
        
        self.terminal = ctk.CTkTextbox(term_frame, fg_color="#000000", text_color="#33ff33", 
                                     font=("Consolas", 12), activate_scrollbars=True)
        self.terminal.pack(fill="both", expand=True, padx=2, pady=2)
        self.terminal.insert("0.0", "> Pronto para execução...\n")

    def exec_tool(self, cmd, name):
        self.terminal.delete("0.0", "end")
        self.terminal.insert("0.0", f"> Executando: {name}...\n> {cmd}\n\n")
        
        def task():
            res = NetworkCore.run_cmd(cmd)
            self.terminal.insert("end", res)
            self.terminal.see("end")
            self.db.log("CMD", name)
        threading.Thread(target=task).start()

    def view_speed(self):
        self.lbl_title.configure(text="Diagnóstico de Velocidade")
        
        # Botão Central "Hero"
        hero = ctk.CTkFrame(self.content, fg_color="transparent")
        hero.pack(pady=20, fill="x")
        
        self.btn_speed = ctk.CTkButton(hero, text="INICIAR TESTE", font=("Roboto", 16, "bold"),
                                       height=60, width=240, corner_radius=30, 
                                       fg_color=C["primary"], hover_color=C["secondary"],
                                       command=self.run_speed_test)
        self.btn_speed.pack()
        self.lbl_speed_status = ctk.CTkLabel(hero, text="Aguardando início...", text_color=C["text_med"])
        self.lbl_speed_status.pack(pady=10)

        # Resultados em Grid
        res_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        res_frame.pack(fill="x", pady=20)
        res_frame.grid_columnconfigure((0,1,2), weight=1)

        self.d_val = self._make_metric(res_frame, 0, "DOWNLOAD", "Mbps")
        self.u_val = self._make_metric(res_frame, 1, "UPLOAD", "Mbps")
        self.p_val = self._make_metric(res_frame, 2, "LATÊNCIA", "ms")

        # Barra
        self.progress = ctk.CTkProgressBar(self.content, height=15, corner_radius=5, progress_color=C["success"])
        self.progress.set(0)

    def _make_metric(self, parent, col, title, unit):
        f = ctk.CTkFrame(parent, fg_color=C["card_surf"], corner_radius=16, border_width=1, border_color=C["border"])
        f.grid(row=0, column=col, padx=10, sticky="ew")
        ctk.CTkLabel(f, text=title, font=("Roboto", 10, "bold"), text_color=C["text_med"]).pack(pady=(20,5))
        lbl = ctk.CTkLabel(f, text="--", font=("Roboto", 32, "bold"), text_color=C["text_high"])
        lbl.pack()
        ctk.CTkLabel(f, text=unit, font=("Roboto", 11), text_color=C["text_med"]).pack(pady=(0,20))
        return lbl

    def run_speed_test(self):
        if not speedtest:
            messagebox.showerror("Erro", "Instale: pip install speedtest-cli")
            return
        
        self.btn_speed.configure(state="disabled", text="TESTANDO...")
        self.progress.pack(pady=20, fill="x", padx=40)
        self.progress.start()
        
        def task():
            try:
                self.lbl_speed_status.configure(text="Conectando ao servidor...")
                st = speedtest.Speedtest()
                st.get_best_server()
                
                self.lbl_speed_status.configure(text="Medindo Download...")
                d = st.download() / 1_000_000
                self.d_val.configure(text=f"{d:.1f}")
                
                self.lbl_speed_status.configure(text="Medindo Upload...")
                u = st.upload() / 1_000_000
                self.u_val.configure(text=f"{u:.1f}")
                
                p = st.results.ping
                self.p_val.configure(text=f"{p:.0f}")
                
                self.db.log("SPEEDTEST", f"D:{d:.1f} U:{u:.1f} P:{p}")
                self.lbl_speed_status.configure(text="Teste Finalizado.")
                
            except Exception as e:
                self.lbl_speed_status.configure(text=f"Erro: {str(e)}")
            finally:
                self.progress.stop()
                self.progress.pack_forget()
                self.btn_speed.configure(state="normal", text="INICIAR NOVO TESTE")
        
        threading.Thread(target=task).start()

    def view_logs(self):
        self.lbl_title.configure(text="Registro de Atividades")
        
        # Toolbar
        bar = ctk.CTkFrame(self.content, fg_color="transparent")
        bar.pack(fill="x", pady=(0, 15))
        
        # Botões de Exportação Modernos
        b_style = {"width": 100, "height": 35, "font": ("Roboto", 12, "bold")}
        ctk.CTkButton(bar, text="PDF", command=self.exp_pdf, fg_color=C["danger"], **b_style).pack(side="right", padx=5)
        ctk.CTkButton(bar, text="Excel", command=self.exp_excel, fg_color=C["success"], **b_style).pack(side="right", padx=5)
        ctk.CTkButton(bar, text="TXT", command=self.exp_txt, fg_color=C["card_surf"], **b_style).pack(side="right", padx=5)

        # Log View (Tabela estilizada via Textbox)
        log_box = ctk.CTkTextbox(self.content, fg_color=C["bg_side"], text_color=C["text_med"], 
                               font=("Consolas", 12), corner_radius=10)
        log_box.pack(fill="both", expand=True)
        
        df = self.db.get_dataframe()
        if df is not None and not df.empty:
            log_box.insert("0.0", df.to_string(index=False))
        else:
            log_box.insert("0.0", "Sem registros ou biblioteca Pandas ausente.")

    # --- EXPORTAÇÃO ---
    def exp_txt(self):
        df = self.db.get_dataframe()
        f = filedialog.asksaveasfilename(defaultextension=".txt")
        if f and df is not None: 
            with open(f, 'w', encoding='utf-8') as file: file.write(df.to_string())
            messagebox.showinfo("Nebula", "TXT Salvo!")

    def exp_excel(self):
        df = self.db.get_dataframe()
        f = filedialog.asksaveasfilename(defaultextension=".xlsx")
        if f and df is not None: 
            df.to_excel(f, index=False)
            messagebox.showinfo("Nebula", "Excel Salvo!")

    def exp_pdf(self):
        df = self.db.get_dataframe()
        f = filedialog.asksaveasfilename(defaultextension=".pdf")
        if f and df is not None:
            doc = SimpleDocTemplate(f, pagesize=A4)
            data = [df.columns.to_list()] + df.values.tolist()
            # Estilização Profissional da Tabela PDF
            style = TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor(C["bg_side"])),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f1f5f9")),
                ('GRID', (0,0), (-1,-1), 1, colors.grey)
            ])
            t = Table(data)
            t.setStyle(style)
            doc.build([t])
            messagebox.showinfo("Nebula", "PDF Salvo!")

if __name__ == "__main__":
    app = NebulaApp()
    app.mainloop()