import json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox
from io import BytesIO

# Попытка использовать Pillow для экспорта
try:
    from PIL import Image, ImageDraw
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

        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        default_font = ("Segoe UI", 10)
        self.style.configure("TLabel", font=default_font, foreground="#222222", background="#f5f6f8")
        self.style.configure("TButton", padding=6, foreground="#222222")
        self.style.map("TButton",
                       foreground=[("active", "#111111"), ("pressed", "#111111")],
                       background=[("active", "#e7e8ea"), ("pressed", "#dcdde0")])
        self.style.configure("TFrame", background="#f5f6f8")
        self.style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 11))

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenu, Editor):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.config(menu="")
        self.show_frame("MainMenu")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        if name == "Editor":
            editor = self.frames["Editor"]
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
        btns.columnconfigure((0,1,2), weight=1)

        self.btn_start = ttk.Button(btns, text="Жаңа жоба", command=lambda: self.app.show_frame("Editor"))
        self.btn_start.grid(row=0, column=0, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Жобаны ашу", command=self.open_project).grid(row=0, column=1, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Шығу", command=self.app.destroy).grid(row=0, column=2, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")

    def update_start_button(self, is_dirty: bool):
        self.btn_start.config(text="Жалғастыру" if is_dirty else "Жаңа жоба")

    def open_project(self):
        editor: "Editor" = self.app.frames["Editor"]
        # Предупреждение, если на холсте есть рисунок
        if editor.has_content():
            res = messagebox.askyesnocancel(
                "Ашу",
                "Ағымдағы кенепте сурет бар. Сақтаусыз ашамыз ба?\nИә — открыть без сохранения\nЖоқ — сначала сохранение"
            )
            if res is None:  # Cancel
                return
            if res is False:  # Save first
                if not editor.menu_save():
                    return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        try:
            editor.load_project(path)
            self.app.show_frame("Editor")
        except Exception as e:
            messagebox.showerror("Қате", f"Файлды ашу мүмкін болмады:\n{e}")

class Editor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.current_tool = tk.StringVar(value="line")
        self.stroke_color = "#222222"
        self.stroke_width = tk.IntVar(value=2)
        self.fill_color = ""  # empty = no fill
        self._start = None
        self._preview_item = None

        self.shapes = []            # [{type, coords, stroke, width, fill, item_id}]
        self._undo_stack = []
        self._item_to_index = {}    # canvas item_id -> index in self.shapes
        self._dirty = False

        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Тазарту", command=self.new_file)
        file_menu.add_command(label="Ашу...", command=self.menu_open)
        file_menu.add_command(label="Сақтау...", command=self.menu_save)
        file_menu.add_separator()
        file_menu.add_command(label="Экспортировать как...", command=self.export_as)  # новый пункт
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Артқа", command=self.undo)
        edit_menu.add_command(label="Алға", command=self.redo)
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)

        tool_menu = tk.Menu(self.menubar, tearoff=0)
        label_map = {"pen": "Қалам","line": "Сызық","rect": "Тікбұрыш","oval": "Эллипс","fill": "Құю"}
        for tool in ("pen", "line", "rect", "oval", "fill"):
            tool_menu.add_radiobutton(label=label_map[tool], value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        self.create_topbar()
        self.create_body()
        self.create_statusbar()

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
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0,6))
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="Панель", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Button(sidebar, text="Артқа", command=self.undo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(sidebar, text="Алға", command=self.redo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Separator(sidebar).pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(sidebar, text="Кеңестер:\nShift — квадрат/дөңгелек\n'Құю' — фигураны бояйды", wraplength=160)\
            .pack(anchor="w", padx=10)

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
    def has_content(self) -> bool: return len(self.shapes) > 0

    def mark_dirty(self, v=True): self._dirty = v
    def is_dirty(self): return self._dirty

    def pick_stroke(self):
        c = colorchooser.askcolor(initialcolor=self.stroke_color)[1]
        if c: self.stroke_color = c

    def pick_fill(self):
        c = colorchooser.askcolor(initialcolor=self.fill_color or "#ffffff")[1]
        if c: self.fill_color = c

    def new_file(self):
        if self.has_content():
            res = messagebox.askyesnocancel(
                "Тазарту", "Кенеп тазартылады. Алдымен сақтаймыз ба?"
            )
            if res is None:
                return
            if res is False:
                if not self.menu_save():
                    return
        self.canvas.delete("all")
        self.shapes.clear()
        self._undo_stack.clear()
        self._item_to_index.clear()
        self.mark_dirty(False)
        self.status("Тазартылды")

    def menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Project JSON", "*.json")])
        if not path:
            return False
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.shapes, f, ensure_ascii=False, indent=2)
            self.mark_dirty(False)
            self.status("Сақталды")
            return True
        except Exception as e:
            messagebox.showerror("Қате", f"Сақтау мүмкін болмады:\n{e}")
            return False

    def menu_open(self):
        # Предупреждение, если есть текущее содержимое
        if self.has_content():
            res = messagebox.askyesnocancel(
                "Ашу", "Ағымдағы кенепте сурет бар. Сақтаусыз ашамыз ба?\nИә — открыть без сохранения\nЖоқ — сначала сохранение"
            )
            if res is None:
                return
            if res is False:
                if not self.menu_save():
                    return
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if path:
            self.load_project(path)

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            self.shapes = json.load(f)
        self.redraw_all()
        self.mark_dirty(False)
        self.status("Ашылды")

    # ---------- Drawing ----------
    def on_press(self, e):
        tool = self.current_tool.get()
        if tool == "fill":
            self.apply_fill_at(e.x, e.y)
            return

        self._start = (e.x, e.y)
        w = self.stroke_width.get()
        if tool == "pen":
            item = self.canvas.create_line(e.x, e.y, e.x+1, e.y+1,
                                           fill=self.stroke_color, width=w,
                                           capstyle=tk.ROUND, smooth=True)
            self._preview_item = item
        elif tool == "line":
            self._preview_item = self.canvas.create_line(e.x, e.y, e.x, e.y,
                                                         fill=self.stroke_color, width=w)
        elif tool == "rect":
            self._preview_item = self.canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                                              outline=self.stroke_color, width=w,
                                                              fill=self.fill_color or "")
        elif tool == "oval":
            self._preview_item = self.canvas.create_oval(e.x, e.y, e.x, e.y,
                                                         outline=self.stroke_color, width=w,
                                                         fill=self.fill_color or "")

    def on_drag(self, e):
        if not self._start or not self._preview_item: return
        if self.current_tool.get() == "fill": return
        x0, y0 = self._start; x1, y1 = e.x, e.y
        if self.current_tool.get() == "pen":
            last = self.canvas.coords(self._preview_item)
            self.canvas.coords(self._preview_item, *last, x1, y1)
        elif self.current_tool.get() == "line":
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        else:
            shift_pressed = (e.state & 0x0001) != 0  # только Shift
            if shift_pressed:
                side = max(abs(x1-x0), abs(y1-y0))
                x1 = x0 + side if x1 >= x0 else x0 - side
                y1 = y0 + side if y1 >= y0 else y0 - side
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"({x1}, {y1})")

    def on_release(self, e):
        if self.current_tool.get() == "fill": return
        if not self._start or not self._preview_item: return
        x0, y0 = self._start; x1, y1 = e.x, e.y
        tool = self.current_tool.get()
        w = self.stroke_width.get(); stroke = self.stroke_color
        fill = self.fill_color if tool in ("rect","oval") and self.fill_color else ""
        if tool == "pen":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type":"pen","coords":coords,"stroke":stroke,"width":w,"fill":""})
            self._item_to_index[self._preview_item] = idx
        elif tool == "line":
            coords = [x0,y0,x1,y1]
            self.canvas.coords(self._preview_item, *coords)
            idx = len(self.shapes)
            self.shapes.append({"type":"line","coords":coords,"stroke":stroke,"width":w,"fill":""})
            self._item_to_index[self._preview_item] = idx
        elif tool == "rect":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type":"rect","coords":coords,"stroke":stroke,"width":w,"fill":fill})
            self._item_to_index[self._preview_item] = idx
        elif tool == "oval":
            coords = self.canvas.coords(self._preview_item)
            idx = len(self.shapes)
            self.shapes.append({"type":"oval","coords":coords,"stroke":stroke,"width":w,"fill":fill})
            self._item_to_index[self._preview_item] = idx
        self._start = None
        self._preview_item = None
        self._undo_stack.clear()
        self.mark_dirty(True)
        self.status("Сызылды")

    def on_motion(self, e):
        self.status(f"Коорд: {e.x}, {e.y} | Құрал: {self.current_tool.get()}")

    def apply_fill_at(self, x, y):
        # Находим верхний canvas-элемент под курсором
        items = self.canvas.find_overlapping(x, y, x, y)
        if not items:
            return
        top_item = items[-1]
        # Маппинг item -> фигура
        idx = self._item_to_index.get(top_item)
        if idx is None:
            return
        shape = self.shapes[idx]
        if shape["type"] not in ("rect", "oval"):
            return
        shape["fill"] = self.fill_color or "#ffffff"
        self.redraw_all()
        self.mark_dirty(True)
        self.status("Құю қолданылды")

    def redraw_all(self):
        self.canvas.delete("all")
        self._item_to_index.clear()
        for i, s in enumerate(self.shapes):
            t = s["type"]; w = s.get("width", 2)
            if t == "pen":
                item = self.canvas.create_line(*s["coords"], fill=s.get("stroke","#000"),
                                               width=w, capstyle=tk.ROUND, smooth=True)
            elif t == "line":
                item = self.canvas.create_line(*s["coords"], fill=s.get("stroke","#000"), width=w)
            elif t == "rect":
                item = self.canvas.create_rectangle(*s["coords"], outline=s.get("stroke","#000"),
                                                    width=w, fill=s.get("fill",""))
            elif t == "oval":
                item = self.canvas.create_oval(*s["coords"], outline=s.get("stroke","#000"),
                                               width=w, fill=s.get("fill",""))
            else:
                continue
            self._item_to_index[item] = i

    # ---------- Undo/Redo ----------
    def undo(self):
        if not self.shapes: return
        self._undo_stack.append(self.shapes.pop())
        self.redraw_all()
        self.mark_dirty(True)
        self.status("Артқа")

    def redo(self):
        if not self._undo_stack: return
        self.shapes.append(self._undo_stack.pop())
        self.redraw_all()
        self.mark_dirty(True)
        self.status("Алға")

    # ---------- Tutorial ----------
    def show_tutorial(self):
        messagebox.showinfo(
            "Туториал",
            "Құралдар: Қалам, Сызық, Тікбұрыш, Эллипс, Құю.\n"
            "- Shift: квадрат/дөңгелек.\n"
            "- 'Құю': тікбұрыш/эллипске басып бояңыз.\n"
            "- Артқа/Алға — қателіктерді түзету.\n"
            "- Сақтау/Ашу — JSON.\n"
            "- Экспорт — PNG/JPG/BMP."
        )

    # ---------- Export ----------
    def export_as(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Экспорт", "Pillow (PIL) табылмады. Экспорт үшін орнатыңыз: pip install pillow")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image","*.png"), ("JPEG Image","*.jpg;*.jpeg"), ("BMP Image","*.bmp")]
        )
        if not path:
            return

        # Размер по холсту
        w = int(self.canvas.winfo_width())
        h = int(self.canvas.winfo_height())
        if w < 2 or h < 2:
            messagebox.showerror("Экспорт", "Холст өлшемі тым кішкентай.")
            return

        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)

        # Рендер фигур в PIL
        for s in self.shapes:
            t = s["type"]; coords = s["coords"]; stroke = s.get("stroke","#000"); width = s.get("width",2)
            if t == "pen":
                pts = [(coords[i], coords[i+1]) for i in range(0, len(coords), 2)]
                if len(pts) >= 2:
                    draw.line(pts, fill=stroke, width=width, joint="curve")
            elif t == "line":
                x0,y0,x1,y1 = map(int, coords)
                draw.line([(x0,y0),(x1,y1)], fill=stroke, width=width)
            elif t == "rect":
                x0,y0,x1,y1 = map(int, coords)
                fill = s.get("fill", None) or None
                draw.rectangle([x0,y0,x1,y1], outline=stroke, width=width, fill=fill)
            elif t == "oval":
                x0,y0,x1,y1 = map(int, coords)
                fill = s.get("fill", None) or None
                draw.ellipse([x0,y0,x1,y1], outline=stroke, width=width, fill=fill)

        try:
            img.save(path)
            self.status("Экспорт завершён")
        except Exception as e:
            messagebox.showerror("Экспорт", f"Сақтау мүмкін болмады:\n{e}")

if __name__ == "__main__":
    app = App()
    try:
        from ctypes import windll
        app.call('tk', 'scaling', 1.2)
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()