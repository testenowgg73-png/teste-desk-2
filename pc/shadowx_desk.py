"""
ShadowX Desk - app do PC
Requisitos:  pip install pillow pyautogui
USB: precisa do 'adb' (Android platform-tools) no PATH ou na pasta 'platform-tools' ao lado deste arquivo.
"""
import base64
import io
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox

from PIL import Image, ImageDraw, ImageOps, ImageTk

try:
    import pyautogui
except Exception:
    pyautogui = None

if getattr(sys, "frozen", False):  # rodando como .exe
    BASE = os.path.dirname(sys.executable)
else:
    BASE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(BASE, "config.json")
IMG_DIR = os.path.join(BASE, "imagens")
os.makedirs(IMG_DIR, exist_ok=True)

COLS, ROWS = 5, 3
X0, DX, Y0, DY, W, H = 54, 188, 69, 163, 156, 132
BG, CELL, RED, FG = "#0e0a0a", "#555555", "#e8232b", "#eeeeee"
GREEN = "#2ecc71"
NOMES = {
    "programa": "Abrir programa / arquivo",
    "link": "Abrir link (URL)",
    "atalho": "Atalho de teclado (ex: ctrl+shift+m)",
    "texto": "Digitar texto",
}


# ---------- utilitarios ----------
def load_cfg():
    d = {"ip": "192.168.0.10", "porta": "5555", "usb": True, "botoes": []}
    try:
        with open(CFG, encoding="utf-8") as f:
            d.update(json.load(f))
    except Exception:
        pass
    d["botoes"] = (d["botoes"] + [{} for _ in range(COLS * ROWS)])[: COLS * ROWS]
    return d


def save_cfg(d):
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def rrect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1, x1 + r, y1]
    return c.create_polygon(pts, smooth=True, **kw)


def rounded(img, size, r):
    img = ImageOps.fit(img.convert("RGBA"), size, Image.LANCZOS)
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), r, fill=255)
    img.putalpha(m)
    return img


def find_adb():
    p = shutil.which("adb")
    if p:
        return p
    for cand in (os.path.join(BASE, "platform-tools", "adb.exe"),
                 os.path.join(BASE, "platform-tools", "adb"),
                 os.path.join(BASE, "adb.exe"), os.path.join(BASE, "adb")):
        if os.path.exists(cand):
            return cand
    return None


def executar(b):
    t, v = b.get("tipo", "programa"), b.get("valor", "")
    if not v:
        return
    try:
        if t == "programa":
            subprocess.Popen(v, shell=True)
        elif t == "link":
            webbrowser.open(v)
        elif t == "atalho" and pyautogui:
            pyautogui.hotkey(*[k.strip() for k in v.lower().split("+")])
        elif t == "texto" and pyautogui:
            pyautogui.write(v, interval=0.01)
    except Exception as e:
        print("Erro na ação:", e)


# ---------- app ----------
class App:
    def __init__(self):
        self.cfg = load_cfg()
        self.root = tk.Tk()
        self.root.title("ShadowX Desk")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)
        self.q = queue.Queue()
        self.sock = None
        self.got_hello = False
        self.lock = threading.Lock()
        self.photos = []
        self.build()
        self.redraw()
        self.root.protocol("WM_DELETE_WINDOW", self.fechar)
        self.root.after(100, self.poll)

    # ----- interface -----
    def build(self):
        c = self.c = tk.Canvas(self.root, width=1024, height=600, bg=BG, highlightthickness=0)
        c.pack()
        rrect(c, 6, 6, 1018, 32, 13, fill="#100d0d", outline="#4a4444")
        self.dot = c.create_oval(9, 9, 29, 29, fill=RED, outline="")
        self.title = c.create_text(38, 19, text="ShadowX Desk", anchor="w", fill=FG, font=("Segoe UI", 10))

        rrect(c, 10, 548, 1014, 588, 20, fill="#100d0d", outline="#3a3333")
        for x1, x2 in ((31, 165), (210, 344), (381, 514)):
            rrect(c, x1, 552, x2, 584, 16, fill="#1b1b1b", outline="")
        f = ("Segoe UI", 10)
        c.create_text(47, 568, text="IP:", anchor="w", fill=FG, font=f)
        c.create_text(222, 568, text="Porta:", anchor="w", fill=FG, font=f)
        c.create_text(392, 568, text="USB:", anchor="w", fill=FG, font=f)

        def entry(var):
            return tk.Entry(self.root, textvariable=var, bg="#1b1b1b", fg=FG, relief="flat",
                            insertbackground=FG, font=f, bd=0)
        self.v_ip = tk.StringVar(value=self.cfg["ip"])
        self.v_porta = tk.StringVar(value=self.cfg["porta"])
        c.create_window(72, 568, window=entry(self.v_ip), anchor="w", width=88)
        c.create_window(265, 568, window=entry(self.v_porta), anchor="w", width=72)
        self.usb_txt = c.create_text(430, 568, anchor="w", fill=GREEN, font=("Segoe UI", 10, "bold"), tags="usb")
        c.tag_bind("usb", "<Button-1>", lambda e: self.toggle_usb())
        self.show_usb()

        rrect(c, 878, 552, 1012, 584, 16, fill=RED, outline="", tags="btn")
        self.btn_txt = c.create_text(945, 568, text="Conectar", fill="white", font=f, tags="btn")
        c.tag_bind("btn", "<Button-1>", lambda e: self.toggle())

    def show_usb(self):
        on = self.cfg["usb"]
        self.c.itemconfig(self.usb_txt, text="Ligado" if on else "Desligado (Wi-Fi)",
                          fill=GREEN if on else "#999999")

    def toggle_usb(self):
        self.cfg["usb"] = not self.cfg["usb"]
        self.show_usb()

    def redraw(self):
        c = self.c
        c.delete("cell")
        self.photos = []
        for i, b in enumerate(self.cfg["botoes"]):
            r, col = divmod(i, COLS)
            x, y = X0 + DX * col, Y0 + DY * r
            tag = f"c{i}"
            rrect(c, x, y, x + W, y + H, 16, fill=CELL, outline="#7a7a7a", tags=("cell", tag))
            p = b.get("imagem")
            full = os.path.join(BASE, p) if p else ""
            if p and os.path.exists(full):
                ph = ImageTk.PhotoImage(rounded(Image.open(full), (W, H), 16))
                self.photos.append(ph)
                c.create_image(x, y, image=ph, anchor="nw", tags=("cell", tag))
            elif not b.get("nome"):
                cx, cy = x + W / 2, y + H / 2
                c.create_line(cx - 12, cy, cx + 12, cy, fill="#7c7c7c", width=3, tags=("cell", tag))
                c.create_line(cx, cy - 12, cx, cy + 12, fill="#7c7c7c", width=3, tags=("cell", tag))
            if b.get("nome"):
                c.create_text(x + W / 2, y + H - 14, text=b["nome"], fill="white",
                              font=("Segoe UI", 10, "bold"), tags=("cell", tag))
            c.tag_bind(tag, "<Button-1>", lambda e, i=i: self.editar(i))
            c.tag_bind(tag, "<Button-3>", lambda e, i=i: self.limpar(i))

    def limpar(self, i):
        self.cfg["botoes"][i] = {}
        self.salvar_e_enviar()

    def salvar_e_enviar(self):
        save_cfg(self.cfg)
        self.redraw()
        if self.sock:
            threading.Thread(target=lambda: self.send(self.payload()), daemon=True).start()

    def editar(self, i):
        b = self.cfg["botoes"][i]
        w = tk.Toplevel(self.root)
        w.title(f"Botão {i + 1}")
        w.configure(bg=BG, padx=16, pady=14)
        w.transient(self.root)
        w.grab_set()
        nome = tk.StringVar(value=b.get("nome", ""))
        img = tk.StringVar(value=b.get("imagem", ""))
        tipo = tk.StringVar(value=NOMES.get(b.get("tipo", "programa")))
        val = tk.StringVar(value=b.get("valor", ""))
        kw = dict(bg=BG, fg=FG, anchor="w")
        ek = dict(bg="#1b1b1b", fg=FG, relief="flat", insertbackground=FG, width=44)

        tk.Label(w, text="Nome:", **kw).grid(row=0, column=0, sticky="w", pady=4)
        tk.Entry(w, textvariable=nome, **ek).grid(row=0, column=1, columnspan=2, pady=4)

        tk.Label(w, text="Imagem:", **kw).grid(row=1, column=0, sticky="w", pady=4)
        tk.Label(w, textvariable=img, bg=BG, fg="#999999", width=34, anchor="w").grid(row=1, column=1)

        def escolher():
            p = filedialog.askopenfilename(parent=w, filetypes=[("Imagens", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
            if p:
                dest = f"btn{i + 1}_{os.path.basename(p)}"
                shutil.copy(p, os.path.join(IMG_DIR, dest))
                img.set("imagens/" + dest)
        tk.Button(w, text="Escolher...", command=escolher, bg="#333", fg=FG, relief="flat").grid(row=1, column=2)

        tk.Label(w, text="Ação:", **kw).grid(row=2, column=0, sticky="w", pady=4)
        om = tk.OptionMenu(w, tipo, *NOMES.values())
        om.configure(bg="#1b1b1b", fg=FG, relief="flat", highlightthickness=0, width=38)
        om.grid(row=2, column=1, columnspan=2, sticky="w", pady=4)

        tk.Label(w, text="Valor:", **kw).grid(row=3, column=0, sticky="w", pady=4)
        tk.Entry(w, textvariable=val, **ek).grid(row=3, column=1, columnspan=2, pady=4)

        def salvar():
            rev = {v: k for k, v in NOMES.items()}
            self.cfg["botoes"][i] = {"nome": nome.get(), "imagem": img.get(),
                                     "tipo": rev[tipo.get()], "valor": val.get()}
            self.salvar_e_enviar()
            w.destroy()

        def apagar():
            self.limpar(i)
            w.destroy()
        fr = tk.Frame(w, bg=BG)
        fr.grid(row=4, column=0, columnspan=3, pady=(12, 0))
        tk.Button(fr, text="Salvar", command=salvar, bg=RED, fg="white", relief="flat", width=12).pack(side="left", padx=6)
        tk.Button(fr, text="Limpar", command=apagar, bg="#333", fg=FG, relief="flat", width=12).pack(side="left", padx=6)

    # ----- conexão -----
    def payload(self):
        out = []
        for i, b in enumerate(self.cfg["botoes"]):
            data = ""
            p = b.get("imagem")
            full = os.path.join(BASE, p) if p else ""
            if p and os.path.exists(full):
                im = rounded(Image.open(full), (200, 170), 24)
                buf = io.BytesIO()
                im.save(buf, "PNG")
                data = base64.b64encode(buf.getvalue()).decode()
            out.append({"id": i, "label": b.get("nome", ""), "img": data})
        return {"type": "config", "buttons": out}

    def send(self, obj):
        with self.lock:
            if self.sock:
                try:
                    self.sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
                except OSError:
                    pass

    def toggle(self):
        if self.sock:
            self.desconectar()
        else:
            self.cfg["ip"], self.cfg["porta"] = self.v_ip.get().strip(), self.v_porta.get().strip()
            save_cfg(self.cfg)
            threading.Thread(target=self._conectar, daemon=True).start()

    def _conectar(self):
        try:
            port = int(self.cfg["porta"])
        except ValueError:
            self.q.put(("erro", "Porta inválida."))
            return
        host = self.cfg["ip"]
        if self.cfg["usb"]:
            adb = find_adb()
            if not adb:
                self.q.put(("erro", "adb não encontrado.\nColoque a pasta 'platform-tools' ao lado do programa "
                                    "ou adicione o adb ao PATH."))
                return
            r = subprocess.run([adb, "forward", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            if r.returncode != 0:
                self.q.put(("erro", "Falha no adb:\n" + (r.stderr or r.stdout) +
                            "\nVerifique o cabo USB e se a Depuração USB está ativa no tablet."))
                return
            host = "127.0.0.1"
        try:
            s = socket.create_connection((host, port), timeout=5)
        except OSError as e:
            self.q.put(("erro", f"Não foi possível conectar em {host}:{port}\n{e}"))
            return
        s.settimeout(None)
        self.sock = s
        self.got_hello = False
        self.t0 = time.time()
        self.q.put(("ok", None))
        self.send(self.payload())
        try:
            for line in s.makefile("r", encoding="utf-8"):
                m = json.loads(line)
                if m.get("type") == "hello":
                    self.got_hello = True
                elif m.get("type") == "press":
                    self.q.put(("press", m.get("id")))
        except Exception:
            pass
        self.q.put(("fim", s))

    def desconectar(self):
        s, self.sock = self.sock, None
        if s:
            try:
                s.close()
            except OSError:
                pass
        self.c.itemconfig(self.dot, fill=RED)
        self.c.itemconfig(self.btn_txt, text="Conectar")

    def poll(self):
        try:
            while True:
                k, v = self.q.get_nowait()
                if k == "ok":
                    self.c.itemconfig(self.dot, fill=GREEN)
                    self.c.itemconfig(self.btn_txt, text="Desconectar")
                elif k == "erro":
                    messagebox.showerror("ShadowX Desk", v)
                elif k == "press":
                    if isinstance(v, int) and 0 <= v < len(self.cfg["botoes"]):
                        threading.Thread(target=executar, args=(self.cfg["botoes"][v],), daemon=True).start()
                elif k == "fim" and self.sock is v:
                    ok = self.got_hello
                    self.desconectar()
                    if not ok:
                        messagebox.showwarning("ShadowX Desk", "O tablet não respondeu.\n"
                                               "Abra o app ShadowX Desk no tablet e toque em Conectar.")
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def fechar(self):
        self.desconectar()
        self.root.destroy()


if __name__ == "__main__":
    App().root.mainloop()
