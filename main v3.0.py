import json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog

# --------- PIL (экспорт) ----------
try:
    from PIL import Image, ImageDraw
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


# ===================== APP =====================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Қарапайым графиктік редактор — жоба")
        self.geometry("1080x700")
        self.minsize(900, 560)
        self.configure(bg="#f5f6f8")

        # ttk styling + hover текст не пропадает
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f5f6f8")
        style.configure("TLabel", background="#f5f6f8", foreground="#222", font=("Segoe UI", 10))
        style.configure("TButton", padding=6, foreground="#222")
        style.map("TButton",
                  foreground=[("active", "#111"), ("pressed", "#111")],
                  background=[("active", "#e7e8ea"), ("pressed", "#dcdde0")])
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 11))

        # контейнер экранов
        container = ttk.Frame(self)
        container.pack(fill=tk.BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenu, Editor):
            frame = F(container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.config(menu="")
        self.show_frame("MainMenu")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if name == "Editor":
            editor: Editor = self.frames["Editor"]
            try:
                self.config(menu=editor.menubar)
            except Exception:
                self.config(menu="")
            editor.focus_canvas()
        else:
            self.config(menu="")
            main: MainMenu = self.frames["MainMenu"]
            editor: Editor = self.frames["Editor"]
            main.update_start_button(is_dirty=editor.has_content())


# ===================== MAIN MENU =====================
class MainMenu(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        wrapper = ttk.Frame(self, padding=30)
        wrapper.grid(row=0, column=0, sticky="nsew")
        wrapper.grid_rowconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=0)
        wrapper.grid_rowconfigure(2, weight=1)
        wrapper.grid_columnconfigure(0, weight=1)

        title = ttk.Label(wrapper, text="Қарапайым графиктік редактор", style="Title.TLabel")
        subtitle = ttk.Label(wrapper, text="Жобаны таңдаңыз", style="Subtitle.TLabel")
        title.grid(row=0, column=0, pady=(20, 6))
        subtitle.grid(row=1, column=0, pady=(0, 18))

        btns = ttk.Frame(wrapper)
        btns.grid(row=2, column=0)
        btns.columnconfigure((0, 1, 2), weight=1)

        self.btn_start = ttk.Button(btns, text="Жаңа жоба", command=self.new_project_dialog)
        self.btn_start.grid(row=0, column=0, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Жобаны ашу", command=self.open_project).grid(row=0, column=1, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Шығу", command=self.app.destroy).grid(row=0, column=2, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")

    def update_start_button(self, is_dirty: bool):
        self.btn_start.config(text="Жалғастыру" if is_dirty else "Жаңа жоба")

    def new_project_dialog(self):
        editor: "Editor" = self.app.frames["Editor"]
        if editor.has_content():
            if not editor.confirm_discard_or_save(title="Жаңа жоба"):
                return
        params = NewProjectDialog(self).result
        if not params:
            return
        # создать новый документ с параметрами
        self.app.show_frame("Editor")
        editor.init_new_document(**params)

    def open_project(self):
        editor: "Editor" = self.app.frames["Editor"]
        if editor.has_content():
            if not editor.confirm_discard_or_save(title="Ашу"):
                return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        try:
            editor.load_project(path)
            self.app.show_frame("Editor")
        except Exception as e:
            messagebox.showerror("Қате", f"Файлды ашу мүмкін болмады:\n{e}")


# ===================== NEW PROJECT DIALOG =====================
class NewProjectDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Жаңа жоба")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.w_var = tk.IntVar(value=1280)
        self.h_var = tk.IntVar(value=720)
        self.bg_mode = tk.StringVar(value="color")  # color | transparent
        self.bg_color = "#ffffff"

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Холст ені (px):").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.w_var, width=10).grid(row=0, column=1, sticky="w", pady=4, padx=(8, 0))

        ttk.Label(frm, text="Холст биіктігі (px):").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=self.h_var, width=10).grid(row=1, column=1, sticky="w", pady=4, padx=(8, 0))

        ttk.Label(frm, text="Фон:").grid(row=2, column=0, sticky="w", pady=4)
        bg_row = ttk.Frame(frm); bg_row.grid(row=2, column=1, sticky="w", pady=4)
        ttk.Radiobutton(bg_row, text="Түс", variable=self.bg_mode, value="color").pack(side="left")
        ttk.Radiobutton(bg_row, text="Мөлдір", variable=self.bg_mode, value="transparent").pack(side="left", padx=(8, 0))
        ttk.Button(frm, text="Таңдау…", command=self.pick_color).grid(row=2, column=2, sticky="w", padx=(8, 0))

        ttk.Separator(frm).grid(row=3, column=0, columnspan=3, sticky="ew", pady=8)

        actions = ttk.Frame(frm); actions.grid(row=4, column=0, columnspan=3, sticky="e")
        ttk.Button(actions, text="Болдырмау", command=self.cancel).pack(side="right", padx=6)  # cancel dialog only
        ttk.Button(actions, text="Құру", command=self.ok).pack(side="right")

        self.result = None
        self.wait_window(self)

    def pick_color(self):
        c = colorchooser.askcolor(initialcolor=self.bg_color)[1]
        if c:
            self.bg_color = c

    def ok(self):
        w = max(1, int(self.w_var.get() or 1))
        h = max(1, int(self.h_var.get() or 1))
        bg = None if self.bg_mode.get() == "transparent" else self.bg_color
        self.result = {"canvas_w": w, "canvas_h": h, "background": bg}
        self.destroy()

    def cancel(self):
        self.result = None
        self.destroy()


# ===================== EDITOR =====================
class Editor(ttk.Frame):
    def __init__(self, parent, app: App):
        super().__init__(parent)
        self.app = app

        # --- состояние документа ---
        self.doc = {
            "canvas_w": 1280,
            "canvas_h": 720,
            "background": "#ffffff"  # None -> прозрачный (для экспорта PNG)
        }

        # --- состояние инструмента ---
        self.current_tool = tk.StringVar(value="line")   # pen/line/rect/oval/fill/move
        self.stroke_color = "#222222"
        self.stroke_width = tk.IntVar(value=2)
        self.fill_color = "#ffffff"  # дефолт, чтобы «Құю» не был пустым
        self._start = None
        self._preview_item = None

        # --- данные фигур ---
        self.shapes = []          # [{type, coords, stroke, width, fill}]
        self._undo_stack = []
        self._item_to_index = {}  # canvas item_id -> index
        self._dirty = False

        # --- меню ---
        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Тазарту", command=self.menu_new_project)
        file_menu.add_command(label="Ашу...", command=self.menu_open, accelerator="Ctrl/Cmd+O")
        file_menu.add_command(label="Сақтау...", command=self.menu_save, accelerator="Ctrl/Cmd+S")
        file_menu.add_separator()
        file_menu.add_command(label="Экспортировать как...", command=self.export_as)
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Артқа", command=self.undo, accelerator="Ctrl/Cmd+Z")
        edit_menu.add_command(label="Алға", command=self.redo, accelerator="Ctrl/Cmd+Y  |  Ctrl/Cmd+Shift+Z")
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)

        tool_menu = tk.Menu(self.menubar, tearoff=0)
        labels = {"pen": "Қалам", "line": "Сызық", "rect": "Тікбұрыш", "oval": "Эллипс",
                  "fill": "Құю", "move": "Жылжыту"}
        for tool in ("pen", "line", "rect", "oval", "fill", "move"):
            tool_menu.add_radiobutton(label=labels[tool], value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        # --- UI ---
        self.create_topbar()
        self.create_body()
        self.create_statusbar()

        # --- хоткеи (кроссплатформенно) ---
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-Z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())
        self.bind_all("<Control-Y>", lambda e: self.redo())
        self.bind_all("<Control-Shift-Z>", lambda e: self.redo())
        # macOS Command
        self.bind_all("<Command-z>", lambda e: self.undo())
        self.bind_all("<Command-Z>", lambda e: self.undo())
        self.bind_all("<Command-y>", lambda e: self.redo())
        self.bind_all("<Command-Y>", lambda e: self.redo())
        self.bind_all("<Command-Shift-Z>", lambda e: self.redo())
        # файл
        self.bind_all("<Control-s>", lambda e: self.menu_save())
        self.bind_all("<Control-o>", lambda e: self.menu_open())
        self.bind_all("<Command-s>", lambda e: self.menu_save())
        self.bind_all("<Command-o>", lambda e: self.menu_open())

        # начальный документ
        self.apply_canvas_geometry()

    # ---------- UI ----------
    def create_topbar(self):
        top = ttk.Frame(self, padding=(8, 6)); top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Құрал:").pack(side=tk.LEFT, padx=(6, 4))
        for t, lbl in [("pen","Қалам"),("line","Сызық"),("rect","Тікбұрыш"),
                       ("oval","Эллипс"),("fill","Құю"),("move","Жылжыту")]:
            ttk.Radiobutton(top, text=lbl, variable=self.current_tool, value=t).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Label(top, text="Қалыңдығы:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(top, from_=1, to=20, width=4, textvariable=self.stroke_width).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(top, text="Сызық түсі", command=self.pick_stroke).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Құю түсі", command=self.pick_fill).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Button(top, text="Сақтау", command=self.menu_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Ашу", command=self.menu_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Тазарту", command=self.menu_new_project).pack(side=tk.LEFT, padx=4)

        spacer = ttk.Frame(top); spacer.pack(side=tk.LEFT, expand=True)
        ttk.Button(top, text="ⓘ", width=3, command=self.show_tutorial).pack(side=tk.RIGHT, padx=(4, 8))
        ttk.Button(top, text="Басты меню", command=lambda: self.app.show_frame("MainMenu")).pack(side=tk.RIGHT, padx=(4, 8))

    def create_body(self):
        body = ttk.Frame(self, padding=8); body.pack(fill=tk.BOTH, expand=True)
        body.rowconfigure(0, weight=1); body.columnconfigure(1, weight=1)

        # sidebar
        s = ttk.Frame(body, width=180); s.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        s.grid_propagate(False)
        ttk.Label(s, text="Панель", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Button(s, text="Артқа", command=self.undo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(s, text="Алға", command=self.redo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Separator(s).pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(s, text="Кеңестер:\nShift — квадрат/дөңгелек\n'Құю' — тікбұрыш/эллипс\n'Жылжыту' — тасымалдау",
                  wraplength=160).pack(anchor="w", padx=10)

        # canvas area
        cw = ttk.Frame(body); cw.grid(row=0, column=1, sticky="nsew")
        cw.rowconfigure(0, weight=1); cw.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(cw, bg="white", highlightthickness=1, highlightbackground="#d0d0d0")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        xscroll = ttk.Scrollbar(cw, orient=tk.HORIZONTAL, command=self.canvas.xview)
        yscroll = ttk.Scrollbar(cw, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        xscroll.grid(row=1, column=0, sticky="ew", padx=4)
        yscroll.grid(row=0, column=1, sticky="ns", pady=4)

        # events
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)

    def create_statusbar(self):
        status = ttk.Frame(self, padding=(6, 4)); status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_lbl = ttk.Label(status, text="Дайын"); self.status_lbl.pack(side=tk.LEFT, padx=8)

    # ---------- helpers ----------
    def focus_canvas(self): self.canvas.focus_set()
    def status(self, t): self.status_lbl.config(text=t)
    def has_content(self): return len(self.shapes) > 0
    def mark_dirty(self, v=True): self._dirty = v

    def apply_canvas_geometry(self):
        w, h = self.doc["canvas_w"], self.doc["canvas_h"]
        self.canvas.config(scrollregion=(0, 0, w, h))
        # рисуем фон как отдельный прямоугольник на слое 0
        self.canvas.delete("all")
        bg = self.doc["background"]
        if bg is not None:
            self.canvas.create_rectangle(0, 0, w, h, fill=bg, outline=bg, tags=("__bg__",))
        self._item_to_index.clear()
        self.redraw_all(skip_clear=True)

    # ---------- color pickers ----------
    def pick_stroke(self):
        c = colorchooser.askcolor(initialcolor=self.stroke_color)[1]
        if c: self.stroke_color = c

    def pick_fill(self):
        c = colorchooser.askcolor(initialcolor=self.fill_color or "#ffffff")[1]
        if c: self.fill_color = c

    # ---------- file ops ----------
    def confirm_discard_or_save(self, title="Ескерту"):
        if not self.has_content() and not self._dirty:
            return True
        res = messagebox.askyesnocancel(title, "Ағымдағы өзгерістер бар. Сақтамай ауыстырамыз ба?\nИә — жалғастыру\nЖоқ — алдымен сақтау")
        if res is None:
            return False
        if res is False:
            return self.menu_save()
        return True

    def menu_new_project(self):
        if not self.confirm_discard_or_save("Жаңа жоба"):
            return
        params = NewProjectDialog(self).result
        if not params:
            return
        self.init_new_document(**params)

    def init_new_document(self, canvas_w: int, canvas_h: int, background):
        self.doc.update({"canvas_w": canvas_w, "canvas_h": canvas_h, "background": background})
        self.shapes.clear(); self._undo_stack.clear(); self._item_to_index.clear()
        self.mark_dirty(False)
        self.apply_canvas_geometry()
        self.status("Жаңа жоба жасалды")

    def menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Project JSON", "*.json")])
        if not path:
            return False
        payload = {"doc": self.doc, "shapes": self.shapes}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self.mark_dirty(False)
            self.status("Сақталды")
            return True
        except Exception as e:
            messagebox.showerror("Қате", f"Сақтау мүмкін болмады:\n{e}")
            return False

    def menu_open(self):
        if not self.confirm_discard_or_save("Ашу"):
            return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if path:
            self.load_project(path)

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # обратная совместимость (старый формат — список фигур)
        if isinstance(data, list):
            self.shapes = data
        else:
            self.doc = data.get("doc", self.doc)
            self.shapes = data.get("shapes", [])
        self.apply_canvas_geometry()
        self.mark_dirty(False)
        self.status("Ашылды")

    # ---------- drawing / tools ----------
    def on_press(self, e):
        tool = self.current_tool.get()

        if tool == "fill":
            self.apply_fill_at(e.x, e.y)
            return

        if tool == "move":
            # выбрать верхний элемент (кроме фона)
            item = self.pick_top_item(e.x, e.y)
            self._selected_item = item
            self._move_last_pos = (e.x, e.y)
            return

        self._start = (e.x, e.y)
        w = self.stroke_width.get()
        if tool == "pen":
            self._preview_item = self.canvas.create_line(e.x, e.y, e.x + 1, e.y + 1,
                                                         fill=self.stroke_color, width=w,
                                                         capstyle=tk.ROUND, smooth=True)
        elif tool == "line":
            self._preview_item = self.canvas.create_line(e.x, e.y, e.x, e.y,
                                                         fill=self.stroke_color, width=w)
        elif tool == "rect":
            self._preview_item = self.canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                                              outline=self.stroke_color, width=w,
                                                              fill="")
        elif tool == "oval":
            self._preview_item = self.canvas.create_oval(e.x, e.y, e.x, e.y,
                                                         outline=self.stroke_color, width=w,
                                                         fill="")

    def on_drag(self, e):
        tool = self.current_tool.get()
        if tool == "move":
            if not hasattr(self, "_selected_item") or not self._selected_item:
                return
            x0, y0 = self._move_last_pos
            dx, dy = e.x - x0, e.y - y0
            if dx or dy:
                self.canvas.move(self._selected_item, dx, dy)
                # обновим статус и точку
                self._move_last_pos = (e.x, e.y)
            self.status("Жылжыту")
            return

        if not self._start or not self._preview_item:
            return
        x0, y0 = self._start
        x1, y1 = e.x, e.y
        if tool == "pen":
            last = self.canvas.coords(self._preview_item)
            self.canvas.coords(self._preview_item, *last, x1, y1)
        elif tool == "line":
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        else:
            # Shift только при реальном нажатии
            shift_pressed = (e.state & 0x0001) != 0
            if shift_pressed:
                side = max(abs(x1 - x0), abs(y1 - y0))
                x1 = x0 + side if x1 >= x0 else x0 - side
                y1 = y0 + side if y1 >= y0 else y0 - side
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"({x1}, {y1})")

    def on_release(self, e):
        tool = self.current_tool.get()

        if tool == "move":
            if hasattr(self, "_selected_item") and self._selected_item:
                # синхронизировать coords в self.shapes
                idx = self._item_to_index.get(self._selected_item)
                if idx is not None:
                    new_coords = self.canvas.coords(self._selected_item)
                    self.shapes[idx]["coords"] = new_coords
                    self._undo_stack.clear()
                    self.mark_dirty(True)
            self._selected_item = None
            self._move_last_pos = None
            return

        if tool == "fill":
            return

        if not self._start or not self._preview_item:
            return

        x0, y0 = self._start
        x1, y1 = e.x, e.y
        w = self.stroke_width.get()
        stroke = self.stroke_color
        fill = ""  # заливка при рисовании — пустая; заливаем позднее отдельным инструментом

        if tool == "pen":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type": "pen", "coords": coords, "stroke": stroke, "width": w, "fill": ""})
            self._item_to_index[self._preview_item] = idx
        elif tool == "line":
            coords = [x0, y0, x1, y1]
            self.canvas.coords(self._preview_item, *coords)
            idx = len(self.shapes)
            self.shapes.append({"type": "line", "coords": coords, "stroke": stroke, "width": w, "fill": ""})
            self._item_to_index[self._preview_item] = idx
        elif tool == "rect":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type": "rect", "coords": coords, "stroke": stroke, "width": w, "fill": fill})
            self._item_to_index[self._preview_item] = idx
        elif tool == "oval":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type": "oval", "coords": coords, "stroke": stroke, "width": w, "fill": fill})
            self._item_to_index[self._preview_item] = idx

        self._start = None
        self._preview_item = None
        self._undo_stack.clear()
        self.mark_dirty(True)
        self.status("Сызылды")

    def on_motion(self, e):
        self.status(f"Коорд: {e.x}, {e.y} | Құрал: {self.current_tool.get()}")

    # ---------- selection helpers ----------
    def pick_top_item(self, x, y):
        # пропускаем фоновый __bg__
        items = self.canvas.find_overlapping(x, y, x, y)
        items = [i for i in items if "__bg__" not in self.canvas.gettags(i)]
        return items[-1] if items else None

    # ---------- FILL (Құю) — ФИКС ----------
    def apply_fill_at(self, x, y):
        item = self.pick_top_item(x, y)
        if not item:
            return
        idx = self._item_to_index.get(item)
        if idx is None:
            return
        shape = self.shapes[idx]
        if shape["type"] not in ("rect", "oval"):
            return
        # применяем цвет
        shape["fill"] = self.fill_color or "#ffffff"
        # обновляем только этот item (быстрее, но можно и redraw_all)
        if shape["type"] == "rect":
            self.canvas.itemconfig(item, fill=shape["fill"])
        elif shape["type"] == "oval":
            self.canvas.itemconfig(item, fill=shape["fill"])
        self._undo_stack.clear()
        self.mark_dirty(True)
        self.status("Құю қолданылды")

    # ---------- redraw ----------
    def redraw_all(self, skip_clear=False):
        if not skip_clear:
            self.canvas.delete("all")
            # фон
            w, h = self.doc["canvas_w"], self.doc["canvas_h"]
            bg = self.doc["background"]
            if bg is not None:
                self.canvas.create_rectangle(0, 0, w, h, fill=bg, outline=bg, tags=("__bg__",))
        self._item_to_index.clear()
        for i, s in enumerate(self.shapes):
            t = s["type"]; w = s.get("width", 2)
            if t == "pen":
                item = self.canvas.create_line(*s["coords"], fill=s.get("stroke", "#000"),
                                               width=w, capstyle=tk.ROUND, smooth=True)
            elif t == "line":
                item = self.canvas.create_line(*s["coords"], fill=s.get("stroke", "#000"), width=w)
            elif t == "rect":
                item = self.canvas.create_rectangle(*s["coords"], outline=s.get("stroke", "#000"),
                                                    width=w, fill=s.get("fill", ""))
            elif t == "oval":
                item = self.canvas.create_oval(*s["coords"], outline=s.get("stroke", "#000"),
                                               width=w, fill=s.get("fill", ""))
            else:
                continue
            self._item_to_index[item] = i

    # ---------- undo/redo ----------
    def undo(self):
        if not self.shapes:
            return
        self._undo_stack.append(self.shapes.pop())
        self.redraw_all()
        self.mark_dirty(True)
        self.status("Артқа")

    def redo(self):
        if not self._undo_stack:
            return
        self.shapes.append(self._undo_stack.pop())
        self.redraw_all()
        self.mark_dirty(True)
        self.status("Алға")

    # ---------- tutorial ----------
    def show_tutorial(self):
        messagebox.showinfo(
            "Туториал",
            "Құралдар: Қалам, Сызық, Тікбұрыш, Эллипс, Құю, Жылжыту.\n"
            "- Shift: квадрат/дөңгелек.\n"
            "- 'Құю': тікбұрыш/эллипске басып бояу.\n"
            "- 'Жылжыту': объектіні тасымалдау.\n"
            "- Артқа/Алға: Ctrl/Cmd+Z, Ctrl/Cmd+Y (немесе Ctrl/Cmd+Shift+Z).\n"
            "- Сақтау/Ашу — JSON.\n"
            "- Экспорт — PNG/JPG/BMP, өлшемі — холст өлшемі."
        )

    # ---------- export (логические размеры холста) ----------
    def export_as(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Экспорт", "Pillow табылмады. Орнатыңыз: pip install pillow")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("JPEG Image", "*.jpg;*.jpeg"), ("BMP Image", "*.bmp")]
        )
        if not path:
            return

        W = int(self.doc["canvas_w"])
        H = int(self.doc["canvas_h"])
        bg = self.doc["background"]

        # PNG с альфой, остальные — RGB
        ext = path.lower().split(".")[-1]
        use_alpha = (ext == "png" and bg is None)

        mode = "RGBA" if use_alpha else "RGB"
        bg_color = (0, 0, 0, 0) if use_alpha else (255, 255, 255)
        if bg is not None:
            from PIL import ImageColor
            rgb = ImageColor.getrgb(bg)
            bg_color = (rgb[0], rgb[1], rgb[2], 255) if use_alpha else rgb

        img = Image.new(mode, (W, H), bg_color)
        draw = ImageDraw.Draw(img)

        # рендер фигур
        for s in self.shapes:
            t = s["type"]; coords = s["coords"]; stroke = s.get("stroke", "#000"); width = s.get("width", 2)
            if t == "pen":
                pts = [(coords[i], coords[i + 1]) for i in range(0, len(coords), 2)]
                if len(pts) >= 2:
                    draw.line(pts, fill=stroke, width=int(width))
            elif t == "line":
                x0, y0, x1, y1 = map(int, coords)
                draw.line([(x0, y0), (x1, y1)], fill=stroke, width=int(width))
            elif t == "rect":
                x0, y0, x1, y1 = map(int, coords)
                fill = s.get("fill", None) or None
                draw.rectangle([x0, y0, x1, y1], outline=stroke, width=int(width), fill=fill)
            elif t == "oval":
                x0, y0, x1, y1 = map(int, coords)
                fill = s.get("fill", None) or None
                draw.ellipse([x0, y0, x1, y1], outline=stroke, width=int(width), fill=fill)

        try:
            img.save(path)
            self.status("Экспорт аяқталды")
        except Exception as e:
            messagebox.showerror("Экспорт", f"Сақтау мүмкін болмады:\n{e}")


# ===================== RUN =====================
if __name__ == "__main__":
    app = App()
    try:
        from ctypes import windll
        app.call('tk', 'scaling', 1.2)
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()
