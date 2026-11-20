#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard Graphique de Supervision & Sécurité Temps Réel (SOC)
Projet : Sécurité des Systèmes Embarqués Temps Réel (STM32 + FreeRTOS)
Responsabilité : Membre 2 (Ingénieur Logiciel PC & Supervision Télémétrie)

Ce tableau de bord fournit une interface graphique moderne (Tkinter, aucune dépendance externe) :
- Visualisation en temps réel de la courbe de charge CPU
- Indicateurs temps réel du Jitter et des Deadline Misses
- Détection d'attaques DoS et alerte visuelle instantanée
- Journal des incidents de sécurité (Forensic Logging)
- Compatible avec carte physique (COM3) et mode Simulation
"""

import os
import sys
import time
import json
import queue
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import serial
except ImportError:
    serial = None

from serial_alert_bridge import send_alert_email, log_alert_to_csv, load_config, init_alert_log
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
CONFIG_EXAMPLE = os.path.join(BASE_DIR, "config.json.example")
LOG_CSV_FILE = os.path.join(BASE_DIR, "alerts_history.csv")


class SecurityDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SOC Embarqué STM32 / FreeRTOS — Supervision & Sécurité")
        self.geometry("980x680")
        self.minsize(850, 580)
        self.configure(bg="#121820")

        # État
        self.config = load_config()
        init_alert_log()
        self.last_alert_time = 0
        self.cooldown = self.config.get("alert", {}).get("cooldown_seconds", 30)
        self.serial_port = None
        self.is_connected = False
        self.is_simulating = False
        self.worker_thread = None
        self.stop_event = threading.Event()
        self.data_queue = queue.Queue()

        # Historique pour le graphique (60 points)
        self.cpu_history = [0] * 60
        self.last_cpu = 0
        self.last_jitter = 0
        self.last_miss = 0
        self.alert_state = False
        self.alert_flash_count = 0

        self.setup_ui()
        self.check_queue()
        self.update_gui_loop()

    def setup_ui(self):
        # 1. En-tête
        header_frame = tk.Frame(self, bg="#1a222d", height=60)
        header_frame.pack(fill=tk.X, side=tk.TOP, padx=0, pady=0)

        title_lbl = tk.Label(
            header_frame,
            text="🛡️ SUPERVISION TEMPS RÉEL & DÉTECTION D'ATTAQUE (STM32)",
            font=("Segoe UI", 14, "bold"),
            fg="#61afef",
            bg="#1a222d"
        )
        title_lbl.pack(side=tk.LEFT, padx=18, pady=12)

        subtitle_lbl = tk.Label(
            header_frame,
            text="Passerelle PC — Membre 2",
            font=("Segoe UI", 10),
            fg="#abb2bf",
            bg="#1a222d"
        )
        subtitle_lbl.pack(side=tk.RIGHT, padx=18, pady=12)

        # 2. Barre de connexion / Contrôles
        ctrl_frame = tk.Frame(self, bg="#161f28", padx=15, pady=8)
        ctrl_frame.pack(fill=tk.X, padx=12, pady=(10, 5))

        tk.Label(ctrl_frame, text="Port :", font=("Segoe UI", 10, "bold"), fg="#ffffff", bg="#161f28").pack(side=tk.LEFT, padx=(0, 4))
        self.port_entry = tk.Entry(ctrl_frame, width=8, font=("Segoe UI", 10))
        self.port_entry.insert(0, "COM3")
        self.port_entry.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_connect = tk.Button(
            ctrl_frame, text="🔌 Connecter Carte", font=("Segoe UI", 9, "bold"),
            bg="#2da44e", fg="#ffffff", activebackground="#2c974b",
            relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self.toggle_serial
        )
        self.btn_connect.pack(side=tk.LEFT, padx=(0, 8))

        self.btn_sim = tk.Button(
            ctrl_frame, text="🧪 Mode Démo / Simulation", font=("Segoe UI", 9, "bold"),
            bg="#3178c6", fg="#ffffff", activebackground="#2b6cb0",
            relief=tk.FLAT, padx=10, pady=3, cursor="hand2", command=self.toggle_simulation
        )
        self.btn_sim.pack(side=tk.LEFT, padx=(0, 8))

        self.status_badge = tk.Label(
            ctrl_frame, text="● DÉCONNECTÉ", font=("Segoe UI", 9, "bold"),
            fg="#e06c75", bg="#161f28"
        )
        self.status_badge.pack(side=tk.LEFT, padx=10)

        # Bouton d'attaque manuelle en simulation
        self.btn_trigger_attack = tk.Button(
            ctrl_frame, text="⚠️ Injecter Attaque DoS", font=("Segoe UI", 9, "bold"),
            bg="#d19a66", fg="#000000", relief=tk.FLAT, padx=8, pady=3,
            cursor="hand2", command=self.inject_simulated_attack
        )
        self.btn_trigger_attack.pack(side=tk.RIGHT, padx=5)

        # 3. Cartes de Métriques (KPIs)
        kpi_frame = tk.Frame(self, bg="#121820")
        kpi_frame.pack(fill=tk.X, padx=12, pady=5)

        self.card_cpu = self.create_kpi_card(kpi_frame, "CHARGE CPU", "1 %", "#98c379", 0)
        self.card_jitter = self.create_kpi_card(kpi_frame, "JITTER MAX", "0 µs", "#61afef", 1)
        self.card_miss = self.create_kpi_card(kpi_frame, "DEADLINE MISS", "0", "#98c379", 2)
        self.card_status = self.create_kpi_card(kpi_frame, "STATUT SÉCURITÉ", "NOMINAL", "#98c379", 3)

        # 4. Graphique Temps Réel de la charge CPU
        graph_frame = tk.Frame(self, bg="#1a222d", bd=1, relief=tk.SOLID)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

        graph_header = tk.Frame(graph_frame, bg="#1a222d")
        graph_header.pack(fill=tk.X, padx=10, pady=4)
        tk.Label(
            graph_header, text="📈 Évolution de la Charge CPU en direct (Dernières 60s)",
            font=("Segoe UI", 10, "bold"), fg="#abb2bf", bg="#1a222d"
        ).pack(side=tk.LEFT)
        tk.Label(
            graph_header, text="--- Seuil Alerte (50%)",
            font=("Segoe UI", 9, "bold"), fg="#e06c75", bg="#1a222d"
        ).pack(side=tk.RIGHT)

        self.canvas = tk.Canvas(graph_frame, bg="#0d1117", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))

        # 5. Journal d'Audit / Historique des Alertes
        log_frame = tk.Frame(self, bg="#1a222d", height=130)
        log_frame.pack(fill=tk.X, padx=12, pady=(0, 10))

        log_lbl = tk.Label(
            log_frame, text="📋 Journal d'Audit & Incidents (Forensic Log)",
            font=("Segoe UI", 9, "bold"), fg="#abb2bf", bg="#1a222d"
        )
        log_lbl.pack(anchor="w", padx=10, pady=(4, 2))

        # Liste / Treeview
        columns = ("time", "cpu", "jitter", "miss", "action")
        self.tree = ttk.Treeview(log_frame, columns=columns, show="headings", height=4)
        self.tree.heading("time", text="Horodatage")
        self.tree.heading("cpu", text="CPU (%)")
        self.tree.heading("jitter", text="Jitter (µs)")
        self.tree.heading("miss", text="Deadline Miss")
        self.tree.heading("action", text="Action Système")

        self.tree.column("time", width=140, anchor="center")
        self.tree.column("cpu", width=90, anchor="center")
        self.tree.column("jitter", width=100, anchor="center")
        self.tree.column("miss", width=110, anchor="center")
        self.tree.column("action", width=400, anchor="w")

        # Style Treeview sombre
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#161f28", foreground="#ffffff", fieldbackground="#161f28", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background="#212d3b", foreground="#61afef", font=("Segoe UI", 9, "bold"))

        self.tree.pack(fill=tk.X, padx=10, pady=(0, 6))

    def create_kpi_card(self, parent, title, init_val, color, col_idx):
        card = tk.Frame(parent, bg="#1a222d", bd=1, relief=tk.FLAT, padx=10, pady=8)
        card.grid(row=0, column=col_idx, sticky="nsew", padx=4)
        parent.grid_columnconfigure(col_idx, weight=1)

        t_lbl = tk.Label(card, text=title, font=("Segoe UI", 8, "bold"), fg="#7f8c8d", bg="#1a222d")
        t_lbl.pack(anchor="w")

        v_lbl = tk.Label(card, text=init_val, font=("Segoe UI", 16, "bold"), fg=color, bg="#1a222d")
        v_lbl.pack(anchor="w", pady=(2, 0))
        return {"card": card, "val_lbl": v_lbl}

    def toggle_serial(self):
        if self.is_connected:
            self.disconnect_serial()
        else:
            self.connect_serial()

    def connect_serial(self):
        port = self.port_entry.get().strip() or "COM3"
        if serial is None:
            messagebox.showerror("Erreur", "pyserial n'est pas installé. Exécutez : pip install pyserial")
            return

        try:
            self.serial_port = serial.Serial(port=port, baudrate=115200, timeout=1.0)
            self.is_connected = True
            self.is_simulating = False
            self.status_badge.config(text=f"● CONNECTÉ ({port})", fg="#98c379")
            self.btn_connect.config(text="⏹️ Déconnecter", bg="#e06c75")
            self.btn_sim.config(state=tk.DISABLED)

            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self.serial_reader_thread, daemon=True)
            self.worker_thread.start()
        except Exception as e:
            messagebox.showerror("Connexion Échouée", f"Impossible d'ouvrir le port {port} :\n{e}")

    def disconnect_serial(self):
        self.stop_event.set()
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.close()
            except Exception:
                pass
        self.is_connected = False
        self.status_badge.config(text="● DÉCONNECTÉ", fg="#e06c75")
        self.btn_connect.config(text="🔌 Connecter Carte", bg="#2da44e")
        self.btn_sim.config(state=tk.NORMAL)

    def toggle_simulation(self):
        if self.is_simulating:
            self.stop_event.set()
            self.is_simulating = False
            self.status_badge.config(text="● DÉCONNECTÉ", fg="#e06c75")
            self.btn_sim.config(text="🧪 Mode Démo / Simulation", bg="#3178c6")
            self.btn_connect.config(state=tk.NORMAL)
        else:
            self.is_simulating = True
            self.is_connected = False
            self.status_badge.config(text="● SIMULATION ACTIVE", fg="#61afef")
            self.btn_sim.config(text="⏹️ Arrêter Simulation", bg="#e06c75")
            self.btn_connect.config(state=tk.DISABLED)

            self.stop_event.clear()
            self.worker_thread = threading.Thread(target=self.simulation_reader_thread, daemon=True)
            self.worker_thread.start()

    def inject_simulated_attack(self):
        self.data_queue.put({"type": "attack_force", "cpu": 100, "jitter": 24, "miss": 0})

    def serial_reader_thread(self):
        while not self.stop_event.is_set():
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    raw = self.serial_port.readline().decode("utf-8", errors="replace").strip()
                    if raw:
                        self.parse_and_queue_line(raw)
                else:
                    time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def simulation_reader_thread(self):
        tick = 0
        while not self.stop_event.is_set():
            tick += 1
            # Tous les 12 cycles, simulation d'une attaque de 3 secondes
            is_attack = (tick % 12) in [0, 1, 2]
            if is_attack:
                cpu = 100
                jitter = 18
                miss = 0
                line = f"cpu={cpu}% idle=597733416 ref=279346 jitter_max={jitter} us miss={miss}"
                alert = f"ALERT,{cpu}"
                self.parse_and_queue_line(line)
                self.parse_and_queue_line(alert)
            else:
                cpu = 1
                jitter = 0
                miss = 0
                line = f"cpu={cpu}% idle=590000000 ref=279346 jitter_max={jitter} us miss={miss}"
                self.parse_and_queue_line(line)

            time.sleep(1.0)

    def parse_and_queue_line(self, line):
        if "cpu=" in line:
            cpu, jitter, miss = self.last_cpu, self.last_jitter, self.last_miss
            try:
                for p in line.split():
                    if p.startswith("cpu="):
                        cpu = int(p.split("=")[1].replace("%", ""))
                    elif p.startswith("jitter_max="):
                        jitter = int(p.split("=")[1])
                    elif p.startswith("miss="):
                        miss = int(p.split("=")[1])
                self.data_queue.put({"type": "telemetry", "cpu": cpu, "jitter": jitter, "miss": miss})
            except Exception:
                pass

        if line.startswith("ALERT"):
            parts = line.split(",")
            cpu_val = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 100
            self.data_queue.put({"type": "alert", "cpu": cpu_val})

    def check_queue(self):
        while not self.data_queue.empty():
            msg = self.data_queue.get_nowait()
            m_type = msg.get("type")

            if m_type == "telemetry":
                self.last_cpu = msg["cpu"]
                self.last_jitter = msg["jitter"]
                self.last_miss = msg["miss"]
                self.cpu_history.pop(0)
                self.cpu_history.append(self.last_cpu)

                # Reset état d'alerte si revenu à la normale
                if self.last_cpu < 50:
                    self.alert_state = False

            elif m_type in ["alert", "attack_force"]:
                self.alert_state = True
                cpu = msg["cpu"]
                now_str = datetime.now().strftime("%H:%M:%S")

                curr_t = time.time()
                if (curr_t - self.last_alert_time) > self.cooldown:
                    action_text = "🚨 Buzzer (PB0) + Envoi Email SMTP..."
                    item_id = self.tree.insert("", 0, values=(now_str, f"{cpu} %", f"{self.last_jitter} µs", self.last_miss, action_text))
                    self.last_alert_time = curr_t

                    def async_email(tree_id, c, j, m):
                        status = send_alert_email(self.config, c, f"ALERT,{c}")
                        log_alert_to_csv(c, j, m, f"ALERT,{c}", status)
                        status_msg = "🚨 Buzzer (PB0) + Email envoyé (OK)" if "SENT" in status else f"🚨 Buzzer (PB0) + {status}"
                        try:
                            self.tree.item(tree_id, values=(now_str, f"{c} %", f"{j} µs", m, status_msg))
                        except Exception:
                            pass

                    threading.Thread(target=async_email, args=(item_id, cpu, self.last_jitter, self.last_miss), daemon=True).start()
                else:
                    action_text = "🚨 Buzzer (PB0) + Cooldown actif (Email ignoré)"
                    self.tree.insert("", 0, values=(now_str, f"{cpu} %", f"{self.last_jitter} µs", self.last_miss, action_text))
                    log_alert_to_csv(cpu, self.last_jitter, self.last_miss, f"ALERT,{cpu}", "IGNORED_COOLDOWN")

        self.after(50, self.check_queue)

    def update_gui_loop(self):
        # Mettre à jour les cartes KPI
        self.card_cpu["val_lbl"].config(text=f"{self.last_cpu} %")
        if self.last_cpu >= 80:
            self.card_cpu["val_lbl"].config(fg="#e06c75")
        elif self.last_cpu >= 50:
            self.card_cpu["val_lbl"].config(fg="#e5c07b")
        else:
            self.card_cpu["val_lbl"].config(fg="#98c379")

        self.card_jitter["val_lbl"].config(text=f"{self.last_jitter} µs")
        self.card_miss["val_lbl"].config(text=f"{self.last_miss}")

        # Clignotement en cas d'attaque
        if self.alert_state:
            self.alert_flash_count += 1
            is_flash = (self.alert_flash_count % 2) == 0
            bg_color = "#e06c75" if is_flash else "#be5046"
            self.card_status["val_lbl"].config(text="⚠️ ATTAQUE DoS DÉTECTÉE", fg="#ffffff")
            self.card_status["card"].config(bg=bg_color)
            self.card_status["val_lbl"].config(bg=bg_color)
        else:
            self.card_status["val_lbl"].config(text="✓ NOMINAL (Sécurisé)", fg="#98c379", bg="#1a222d")
            self.card_status["card"].config(bg="#1a222d")

        # Redessiner le graphique
        self.draw_graph()
        self.after(500, self.update_gui_loop)

    def draw_graph(self):
        c = self.canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()

        if w < 50 or h < 50:
            return

        pad_l = 40
        pad_r = 20
        pad_t = 20
        pad_b = 30
        plot_w = w - pad_l - pad_r
        plot_h = h - pad_t - pad_b

        # Lignes horizontales de graduation (0%, 25%, 50%, 75%, 100%)
        for pct in [0, 25, 50, 75, 100]:
            y = pad_t + plot_h - int((pct / 100.0) * plot_h)
            line_color = "#3e4451" if pct != 50 else "#e06c75"
            dash = () if pct in [0, 50] else (3, 3)
            c.create_line(pad_l, y, w - pad_r, y, fill=line_color, dash=dash)
            c.create_text(pad_l - 8, y, text=f"{pct}%", fill="#7f8c8d", font=("Segoe UI", 8), anchor="e")

        # Tracer la courbe du CPU
        points = []
        n = len(self.cpu_history)
        step = plot_w / (n - 1) if n > 1 else plot_w

        for i, val in enumerate(self.cpu_history):
            x = pad_l + (i * step)
            y = pad_t + plot_h - int((val / 100.0) * plot_h)
            points.append((x, y))

        # Trace de la ligne
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            # Couleur dynamique selon la valeur
            seg_val = self.cpu_history[i + 1]
            col = "#e06c75" if seg_val >= 80 else ("#e5c07b" if seg_val >= 50 else "#61afef")
            c.create_line(x1, y1, x2, y2, fill=col, width=2)

        # Dernier point en surbrillance
        if points:
            lx, ly = points[-1]
            c.create_oval(lx - 4, ly - 4, lx + 4, ly + 4, fill="#ffffff", outline="#61afef", width=2)


def main():
    app = SecurityDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()
