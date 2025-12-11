import json
import copy
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog

# Pillow для экспорта и bucket-fill
try:
    from PIL import Image, ImageDraw, ImageColor, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Қарапайым графиктік редактор — жоба")
        self.geometry("1080x700")
        self.minsize(900, 560)
        self.configure(bg="#f5f6f8")

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        default_font = ("Segoe UI", 10)
        style.configure("TLabel", font=default_font, foreground="#222", background="#f5f6f8")
        style.configure("TButton", padding=6, foreground="#222")
        style.map("TButton",
                  foreground=[("active", "#111"), ("pressed", "#111")],
                  background=[("active", "#e7e8ea"), ("pressed", "#dcdde0")])
        style.configure("TFrame", background="#f5f6f8")
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 11))

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
            ed: Editor = self.frames["Editor"]
            try:
                self.config(menu=ed.menubar)
            except Exception:
                self.config(menu="")
            ed.focus_canvas()
        else:
            self.config(menu="")
            main: MainMenu = self.frames["MainMenu"]
            ed: Editor = self.frames["Editor"]
            main.update_start_button(is_dirty=ed.has_content())


class MainMenu(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        wrapper = ttk.Frame(self, padding=30, style="TFrame")
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

        self.btn_start = ttk.Button(btns, text="Жаңа жоба", command=self.new_project)
        self.btn_start.grid(row=0, column=0, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Жобаны ашу", command=self.open_project).grid(row=0, column=1, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Шығу", command=self.app.destroy).grid(row=0, column=2, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")

    def update_start_button(self, is_dirty: bool):
        self.btn_start.config(text="Жалғастыру" if is_dirty else "Жаңа жоба")

    def new_project(self):
        ed: Editor = self.app.frames["Editor"]
        if ed.is_dirty() or ed.has_content():
            res = messagebox.askyesnocancel("Жаңа жоба", "Ағымдағы жұмыс сақталсын ба?")
            if res is None:
                return
            if res is True and not ed.menu_save():
                return
        ed.new_canvas_dialog()
        self.app.show_frame("Editor")

    def open_project(self):
        ed: Editor = self.app.frames["Editor"]
        if ed.has_content():
            res = messagebox.askyesnocancel(
                "Ашу",
                "Ағымдағы кенепте сурет бар. Сақтаусыз ашамыз ба?\nИә — открыть без сохранения\nЖоқ — сначала сохранение"
            )
            if res is None:
                return
            if res is False and not ed.menu_save():
                return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        try:
            ed.load_project(path)
            self.app.show_frame("Editor")
        except Exception as e:
            messagebox.showerror("Қате", f"Файлды ашу мүмкін болмады:\n{e}")


class Editor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # Логический размер холста (управляет скроллом)
        self.canvas_w = 1280
        self.canvas_h = 720
        self.background = "#ffffff"

        # Инструменты/состояние
        self.current_tool = tk.StringVar(value="line")  # pen/line/rect/oval/fill
        self.stroke_color = "#222222"
        self.stroke_width = tk.IntVar(value=2)
        self.fill_color = "#ff0000"
        self._start = None
        self._preview_item = None

        # Данные
        self.shapes = []           # [{type, coords, stroke, width, fill}]
        self._item_to_index = {}   # canvas item id -> index
        self._dirty = False

        # Растровый слой для bucket-fill (RGBA, размер = логическому холсту)
        self.raster_img = None
        self.raster_tk = None
        self.raster_item = None

        # История (snapshots) для undo/redo, покрывает и вектор, и заливки
        self._history = []
        self._future = []

        # Меню
        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Тазарту", command=self.new_file)
        file_menu.add_command(label="Ашу...", command=self.menu_open)
        file_menu.add_command(label="Сақтау...", command=self.menu_save)
        file_menu.add_separator()
        file_menu.add_command(label="Экспортировать как...", command=self.export_as)
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Артқа", command=self.undo)
        edit_menu.add_command(label="Алға", command=self.redo)
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)

        tool_menu = tk.Menu(self.menubar, tearoff=0)
        label_map = {"pen": "Қалам", "line": "Сызық", "rect": "Тікбұрыш", "oval": "Эллипс", "fill": "Құю"}
        for tool in ("pen", "line", "rect", "oval", "fill"):
            tool_menu.add_radiobutton(label=label_map[tool], value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        # UI
        self.create_topbar()
        self.create_body()
        self.create_statusbar()

        # Инициализация
        self.apply_scrollregion()
        self._snapshot()

    # ---------- UI ----------
    def create_topbar(self):
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Құрал:").pack(side=tk.LEFT, padx=(6, 4))
        for t, lbl in [("pen","Қалам"),("line","Сызық"),("rect","Тікбұрыш"),("oval","Эллипс"),("fill","Құю")]:
            ttk.Radiobutton(top, text=lbl, variable=self.current_tool, value=t).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Label(top, text="Қалыңдығы:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(top, from_=1, to=20, width=4, textvariable=self.stroke_width).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(top, text="Сызық түсі", command=self.pick_stroke).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Құю түсі", command=self.pick_fill).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Button(top, text="Сақтау", command=self.menu_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Ашу", command=self.menu_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Тазарту", command=self.new_file).pack(side=tk.LEFT, padx=4)

        spacer = ttk.Frame(top); spacer.pack(side=tk.LEFT, expand=True)
        ttk.Button(top, text="ⓘ", width=3, command=self.show_tutorial).pack(side=tk.RIGHT, padx=(4, 8))
        ttk.Button(top, text="Басты меню", command=lambda: self.app.show_frame("MainMenu")).pack(side=tk.RIGHT, padx=(4,8))

    def create_body(self):
        body = ttk.Frame(self, padding=8)
        body.pack(fill=tk.BOTH, expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        sidebar = ttk.Frame(body, width=180)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="Панель", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Button(sidebar, text="Артқа", command=self.undo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(sidebar, text="Алға", command=self.redo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Separator(sidebar).pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(sidebar, text="Кеңестер:\nShift — квадрат/дөңгелек\n'Құю' — bucket fill\nКолесо/Shift — прокрутка",
                  wraplength=160).pack(anchor="w", padx=10)

        canvas_wrap = ttk.Frame(body)
        canvas_wrap.grid(row=0, column=1, sticky="nsew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_wrap, bg="white", highlightthickness=1, highlightbackground="#d0d0d0")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        xscroll = ttk.Scrollbar(canvas_wrap, orient=tk.HORIZONTAL, command=self.canvas.xview)
        yscroll = ttk.Scrollbar(canvas_wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        xscroll.grid(row=1, column=0, sticky="ew", padx=4)
        yscroll.grid(row=0, column=1, sticky="ns", pady=4)

        # Колесо мыши: скролл только если есть что скроллить (Tk сам ограничит)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        # Linux
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<Shift-Button-4>", lambda e: self.canvas.xview_scroll(-3, "units"))
        self.canvas.bind("<Shift-Button-5>", lambda e: self.canvas.xview_scroll(3, "units"))

        # Рисование
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.focus_set()

    def create_statusbar(self):
        status = ttk.Frame(self, padding=(6,4))
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_lbl = ttk.Label(status, text="Дайын")
        self.status_lbl.pack(side=tk.LEFT, padx=8)

    # ---------- Helpers ----------
    def focus_canvas(self): self.canvas.focus_set()
    def status(self, text): self.status_lbl.config(text=text)
    def has_content(self): return bool(self.shapes) or self.raster_img is not None
    def is_dirty(self): return self._dirty
    def mark_dirty(self, v=True): self._dirty = v

    def apply_scrollregion(self):
        self.canvas.config(scrollregion=(0, 0, self.canvas_w, self.canvas_h))
        self.redraw_all()

    # ---------- Цвета ----------
    def pick_stroke(self):
        c = colorchooser.askcolor(initialcolor=self.stroke_color)[1]
        if c: self.stroke_color = c

    def pick_fill(self):
        c = colorchooser.askcolor(initialcolor=self.fill_color or "#ffffff")[1]
        if c: self.fill_color = c

    # ---------- Прокрутка ----------
    def _on_mousewheel(self, e):
        step = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")

    def _on_shift_mousewheel(self, e):
        step = -1 if e.delta > 0 else 1
        self.canvas.xview_scroll(step * 3, "units")

    # ---------- Новый холст ----------
    def new_canvas_dialog(self):
        try:
            w = int(simpledialog.askstring("Жаңа холст", "Ені (px):", initialvalue=str(self.canvas_w)) or self.canvas_w)
            h = int(simpledialog.askstring("Жаңа холст", "Биіктігі (px):", initialvalue=str(self.canvas_h)) or self.canvas_h)
        except Exception:
            messagebox.showerror("Қате", "Сандарды дұрыс енгізіңіз")
            return
        bg = colorchooser.askcolor(title="Фон түсі", initialcolor=self.background)[1]
        if bg is None:
            bg = self.background
        self.canvas_w, self.canvas_h, self.background = max(10, w), max(10, h), bg
        # очистка
        self.shapes.clear()
        self._item_to_index.clear()
        self.raster_img = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0,0,0,0)) if PIL_AVAILABLE else None
        self.raster_tk = None
        self.raster_item = None
        self.apply_scrollregion()
        self._history.clear(); self._future.clear(); self._snapshot()
        self.mark_dirty(False)
        self.status("Жаңа холст жасалды")

    def new_file(self):
        if self.has_content():
            res = messagebox.askyesnocancel("Тазарту", "Кенеп тазартылады. Алдымен сақтаймыз ба?")
            if res is None:
                return
            if res is True and not self.menu_save():
                return
        self.new_canvas_dialog()

    # ---------- Save/Open ----------
    def menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Project JSON", "*.json")])
        if not path:
            return False
        try:
            data = {
                "meta": {"w": self.canvas_w, "h": self.canvas_h, "bg": self.background},
                "shapes": self.shapes,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.mark_dirty(False)
            self.status("Сақталды")
            return True
        except Exception as e:
            messagebox.showerror("Қате", f"Сақтау мүмкін болмады:\n{e}")
            return False

    def menu_open(self):
        if self.has_content():
            res = messagebox.askyesnocancel(
                "Ашу", "Ағымдағы кенепте сурет бар. Сақтаусыз ашамыз ба?\nИә — открыть без сохранения\nЖоқ — сначала сохранение"
            )
            if res is None:
                return
            if res is False and not self.menu_save():
                return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if path:
            self.load_project(path)

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            # старый формат
            self.shapes = data
        else:
            meta = data.get("meta", {})
            self.canvas_w = int(meta.get("w", self.canvas_w))
            self.canvas_h = int(meta.get("h", self.canvas_h))
            self.background = meta.get("bg", self.background)
            self.shapes = data.get("shapes", [])
        # сброс растрового слоя
        self.raster_img = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0,0,0,0)) if PIL_AVAILABLE else None
        self.raster_tk = None
        self.raster_item = None
        self.apply_scrollregion()
        self._history.clear(); self._future.clear(); self._snapshot()
        self.mark_dirty(False)
        self.status("Ашылды")

    # ---------- Рисование ----------
    def on_press(self, e):
        tool = self.current_tool.get()
        cx, cy = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)

        if tool == "fill":
            self.bucket_fill(int(cx), int(cy))
            return

        self._start = (cx, cy)
        w = self.stroke_width.get()
        if tool == "pen":
            self._preview_item = self.canvas.create_line(cx, cy, cx, cy,
                                                         fill=self.stroke_color, width=w,
                                                         capstyle=tk.ROUND, smooth=True)
        elif tool == "line":
            self._preview_item = self.canvas.create_line(cx, cy, cx, cy,
                                                         fill=self.stroke_color, width=w)
        elif tool == "rect":
            self._preview_item = self.canvas.create_rectangle(cx, cy, cx, cy,
                                                              outline=self.stroke_color, width=w,
                                                              fill=self.fill_color or "")
        elif tool == "oval":
            self._preview_item = self.canvas.create_oval(cx, cy, cx, cy,
                                                         outline=self.stroke_color, width=w,
                                                         fill=self.fill_color or "")

    def on_drag(self, e):
        if not self._start or not self._preview_item:
            return
        if self.current_tool.get() == "fill":
            return
        x0, y0 = self._start
        x1, y1 = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        tool = self.current_tool.get()
        if tool == "pen":
            coords = self.canvas.coords(self._preview_item)
            self.canvas.coords(self._preview_item, *coords, x1, y1)
        elif tool == "line":
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        else:
            shift_pressed = (e.state & 0x0001) != 0
            if shift_pressed:
                side = max(abs(x1 - x0), abs(y1 - y0))
                x1 = x0 + side if x1 >= x0 else x0 - side
                y1 = y0 + side if y1 >= y0 else y0 - side
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"({int(x1)}, {int(y1)})")

    def on_release(self, e):
        if self.current_tool.get() == "fill":
            return
        if not self._start or not self._preview_item:
            return
        x0, y0 = self._start
        x1, y1 = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        tool = self.current_tool.get()
        w = self.stroke_width.get()
        stroke = self.stroke_color
        fill = self.fill_color if tool in ("rect", "oval") and self.fill_color else ""

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
        self._future.clear()
        self._snapshot()
        self.mark_dirty(True)
        self.status("Сызылды")

    def on_motion(self, e):
        cx, cy = int(self.canvas.canvasx(e.x)), int(self.canvas.canvasy(e.y))
        self.status(f"Коорд: {cx}, {cy} | Құрал: {self.current_tool.get()}")

    # ---------- Перерисовка ----------
    def redraw_all(self):
        self.canvas.delete("all")
        # фон (для визуала; flood-fill считает «стены» по рендеру ниже)
        self.canvas.create_rectangle(0, 0, self.canvas_w, self.canvas_h,
                                     fill=self.background, outline=self.background, tags=("__bg__",))
        # растровые заливки
        if PIL_AVAILABLE:
            if self.raster_img is None:
                self.raster_img = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))
            self.raster_tk = ImageTk.PhotoImage(self.raster_img)
            self.raster_item = self.canvas.create_image(0, 0, image=self.raster_tk, anchor="nw", tags=("__raster__",))
            self.canvas.tag_lower(self.raster_item)

        # вектор
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

    # ---------- Undo/Redo: снапшоты (вектор + заливки) ----------
    def _snapshot(self):
        snap = {
            "shapes": copy.deepcopy(self.shapes),
            "raster": self.raster_img.copy() if (PIL_AVAILABLE and self.raster_img is not None) else None
        }
        self._history.append(snap)
        # ограничение длины истории при желании
        if len(self._history) > 100:
            self._history.pop(0)

    def undo(self):
        if len(self._history) <= 1:
            return
        self._future.append(self._history.pop())
        state = self._history[-1]
        self.shapes = copy.deepcopy(state["shapes"])
        self.raster_img = state["raster"].copy() if state["raster"] is not None else (Image.new("RGBA", (self.canvas_w, self.canvas_h), (0,0,0,0)) if PIL_AVAILABLE else None)
        self.redraw_all()
        self.status("Артқа")

    def redo(self):
        if not self._future:
            return
        state = self._future.pop()
        self._history.append({
            "shapes": copy.deepcopy(state["shapes"]),
            "raster": state["raster"].copy() if state["raster"] is not None else None
        })
        self.shapes = copy.deepcopy(state["shapes"])
        self.raster_img = state["raster"].copy() if state["raster"] is not None else (Image.new("RGBA", (self.canvas_w, self.canvas_h), (0,0,0,0)) if PIL_AVAILABLE else None)
        self.redraw_all()
        self.status("Алға")

    # ---------- Bucket fill (работает и с Rect/Oval) ----------
    def bucket_fill(self, x, y):
        if not PIL_AVAILABLE:
            messagebox.showerror("Қате", "Pillow қажет: pip install pillow")
            return
        if x < 0 or y < 0 or x >= self.canvas_w or y >= self.canvas_h:
            return

        # Рендер сцены в RGB: фон + заливки + вектор (контуры — «стены», fill фигур тоже учитываем)
        scene = Image.new("RGB", (self.canvas_w, self.canvas_h), ImageColor.getrgb(self.background))
        draw = ImageDraw.Draw(scene)

        # существующие заливки (как слой под вектором)
        if self.raster_img is None:
            self.raster_img = Image.new("RGBA", (self.canvas_w, self.canvas_h), (0, 0, 0, 0))
        scene.paste(self.raster_img.convert("RGB"), (0, 0))

        # векторные фигуры: сначала заливки, затем контуры — так «стены» всегда чёткие
        for s in self.shapes:
            t = s["type"]; coords = list(map(int, s["coords"])); stroke = s.get("stroke", "#000"); width = int(s.get("width", 2))
            fill = s.get("fill") or None
            if t == "rect":
                x0,y0,x1,y1 = coords
                if fill: draw.rectangle([x0,y0,x1,y1], fill=fill)
            elif t == "oval":
                x0,y0,x1,y1 = coords
                if fill: draw.ellipse([x0,y0,x1,y1], fill=fill)
        for s in self.shapes:
            t = s["type"]; coords = list(map(int, s["coords"])); stroke = s.get("stroke", "#000"); width = int(s.get("width", 2))
            if t == "pen":
                pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                if len(pts) >= 2: draw.line(pts, fill=stroke, width=width)
            elif t == "line":
                x0,y0,x1,y1 = coords; draw.line([(x0,y0),(x1,y1)], fill=stroke, width=width)
            elif t == "rect":
                x0,y0,x1,y1 = coords; draw.rectangle([x0,y0,x1,y1], outline=stroke, width=width)
            elif t == "oval":
                x0,y0,x1,y1 = coords; draw.ellipse([x0,y0,x1,y1], outline=stroke, width=width)

        target = scene.getpixel((x, y))
        fill_rgb = ImageColor.getrgb(self.fill_color)
        if target == fill_rgb:
            return

        # Flood fill (4-связность)
        W, H = self.canvas_w, self.canvas_h
        mask = Image.new("1", (W, H), 0)
        mpx = mask.load(); spx = scene.load()
        stack = [(x, y)]
        while stack:
            px, py = stack.pop()
            if px < 0 or py < 0 or px >= W or py >= H: continue
            if mpx[px, py] == 1: continue
            if spx[px, py] != target: continue
            mpx[px, py] = 1
            stack.extend(((px+1,py),(px-1,py),(px,py+1),(px,py-1)))

        # Наложить заливку на растровый слой
        paint = Image.new("RGBA", (W, H), fill_rgb + (255,))
        self._future.clear()
        # snapshot до изменения
        self._snapshot()
        self.raster_img.paste(paint, (0, 0), mask)
        self.redraw_all()
        # snapshot после — чтобы undo вернулся к предыдущему
        self._history[-1] = {
            "shapes": copy.deepcopy(self.shapes),
            "raster": self.raster_img.copy()
        }
        self.mark_dirty(True)
        self.status("Құю қолданылды")

    # ---------- Экспорт ----------
    def export_as(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Экспорт", "Pillow (PIL) табылмады. Экспорт үшін орнатыңыз: pip install pillow")
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG Image","*.png"), ("JPEG Image","*.jpg;*.jpeg"), ("BMP Image","*.bmp")])
        if not path:
            return
        W, H = self.canvas_w, self.canvas_h
        img = Image.new("RGB", (W, H), ImageColor.getrgb(self.background))
        if self.raster_img is not None:
            img.paste(self.raster_img.convert("RGB"), (0, 0))
        draw = ImageDraw.Draw(img)
        for s in self.shapes:
            t = s["type"]; coords = list(map(int, s["coords"])); stroke = s.get("stroke","#000"); width = int(s.get("width",2))
            fill = s.get("fill") or None
            if t == "pen":
                pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                if len(pts) >= 2: draw.line(pts, fill=stroke, width=width)
            elif t == "line":
                x0,y0,x1,y1 = coords; draw.line([(x0,y0),(x1,y1)], fill=stroke, width=width)
            elif t == "rect":
                x0,y0,x1,y1 = coords; draw.rectangle([x0,y0,x1,y1], outline=stroke, width=width, fill=fill)
            elif t == "oval":
                x0,y0,x1,y1 = coords; draw.ellipse([x0,y0,x1,y1], outline=stroke, width=width, fill=fill)
        try:
            img.save(path)
            self.status("Экспорт завершён")
        except Exception as e:
            messagebox.showerror("Экспорт", f"Сақтау мүмкін болмады:\n{e}")

    # ---------- Туториал ----------
    def show_tutorial(self):
        messagebox.showinfo(
            "Туториал",
            "Құралдар: Қалам, Сызық, Тікбұрыш, Эллипс, Құю.\n"
            "- Shift: квадрат/дөңгелек.\n"
            "- 'Құю' — аймақты шекараға дейін бояйды (жұмыс істейді және фигураларда).\n"
            "- Колесо — тік, Shift+колесо — көлденең прокрутка.\n"
            "- Жаңа холст — өлшемдерімен диалог.\n"
            "- Сақтау/Ашу — JSON (өлшемдері сақталады).\n"
            "- Экспорт — PNG/JPG/BMP."
        )


if __name__ == "__main__":
    app = App()
    try:
        from ctypes import windll
        app.call('tk', 'scaling', 1.2)
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()