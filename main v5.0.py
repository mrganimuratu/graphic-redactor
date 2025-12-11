import json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox, simpledialog

try:
    from PIL import Image, ImageDraw, ImageColor
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
        self.style.configure("TLabel", font=("Segoe UI", 10), foreground="#222222", background="#f5f6f8")
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
            self.config(menu=editor.menubar)
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

        wrapper = ttk.Frame(self, padding=30)
        wrapper.pack(expand=True)
        ttk.Label(wrapper, text="Қарапайым графиктік редактор", style="Title.TLabel").pack(pady=(10, 5))
        ttk.Label(wrapper, text="Жобаны таңдаңыз", style="Subtitle.TLabel").pack(pady=(0, 20))

        self.btn_start = ttk.Button(wrapper, text="Жаңа жоба", command=self.new_project)
        self.btn_start.pack(pady=6, ipadx=12, ipady=8, fill="x")
        ttk.Button(wrapper, text="Жобаны ашу", command=self.open_project).pack(pady=6, ipadx=12, ipady=8, fill="x")
        ttk.Button(wrapper, text="Шығу", command=self.app.destroy).pack(pady=6, ipadx=12, ipady=8, fill="x")

    def update_start_button(self, is_dirty: bool):
        self.btn_start.config(text="Жалғастыру" if is_dirty else "Жаңа жоба")

    def new_project(self):
        ed: "Editor" = self.app.frames["Editor"]
        if not ed.new_canvas_dialog():
            return
        self.app.show_frame("Editor")

    def open_project(self):
        editor: "Editor" = self.app.frames["Editor"]
        if editor.has_content():
            res = messagebox.askyesnocancel("Ашу", "Ағымдағы кенепте сурет бар. Сақтаусыз ашамыз ба?\nИә — открыть без сохранения\nЖоқ — сначала сохранение")
            if res is None:
                return
            if res is False:
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

        self.canvas_w = 1280
        self.canvas_h = 720
        self.background = "#ffffff"

        self.current_tool = tk.StringVar(value="line")
        self.stroke_color = "#222222"
        self.stroke_width = tk.IntVar(value=2)
        self.fill_color = "#ffffff"
        self._start = None
        self._preview_item = None

        self.shapes = []
        self._undo_stack = []
        self._item_to_index = {}
        self._dirty = False

        # Меню
        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Тазарту", command=self.new_file)
        file_menu.add_command(label="Жаңа холст...", command=self.new_canvas_dialog)
        file_menu.add_command(label="Ашу...", command=self.menu_open)
        file_menu.add_command(label="Сақтау...", command=self.menu_save)
        file_menu.add_separator()
        file_menu.add_command(label="Экспорт...", command=self.export_as)
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Артқа", command=self.undo, accelerator="Ctrl+Z / ⌘Z")
        edit_menu.add_command(label="Алға", command=self.redo, accelerator="Ctrl+Y / ⌘Shift+Z")
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)

        tool_menu = tk.Menu(self.menubar, tearoff=0)
        label_map = {"pen": "Қалам", "line": "Сызық", "rect": "Тікбұрыш", "oval": "Эллипс"}
        for tool in ("pen", "line", "rect", "oval"):
            tool_menu.add_radiobutton(label=label_map[tool], value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        self.create_topbar()
        self.create_body()
        self.create_statusbar()
        self.apply_scrollregion()

        self.app.bind_all("<Control-z>", lambda e: self.undo())
        self.app.bind_all("<Control-y>", lambda e: self.redo())
        self.app.bind_all("<Command-z>", lambda e: self.undo())
        self.app.bind_all("<Command-Shift-Z>", lambda e: self.redo())

    def create_topbar(self):
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(top, text="Құрал:").pack(side=tk.LEFT, padx=(6, 4))
        for t, lbl in [("pen", "Қалам"), ("line", "Сызық"), ("rect", "Тікбұрыш"), ("oval", "Эллипс")]:
            ttk.Radiobutton(top, text=lbl, variable=self.current_tool, value=t).pack(side=tk.LEFT, padx=4)
        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)
        ttk.Label(top, text="Қалыңдығы:").pack(side=tk.LEFT, padx=(0, 4))
        ttk.Spinbox(top, from_=1, to=20, width=4, textvariable=self.stroke_width).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(top, text="Сызық түсі", command=self.pick_stroke).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Құю түсі", command=self.pick_fill).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Сақтау", command=self.menu_save).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Ашу", command=self.menu_open).pack(side=tk.RIGHT, padx=4)
        ttk.Button(top, text="Тазарту", command=self.new_file).pack(side=tk.RIGHT, padx=4)

    def create_body(self):
        frame = ttk.Frame(self, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        sidebar = ttk.Frame(frame, width=180)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 6))
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="Панель", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Button(sidebar, text="Артқа", command=self.undo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(sidebar, text="Алға", command=self.redo).pack(fill=tk.X, padx=10, pady=4)

        canvas_wrap = ttk.Frame(frame)
        canvas_wrap.grid(row=0, column=1, sticky="nsew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_wrap, bg=self.background, highlightthickness=1, highlightbackground="#d0d0d0")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        xscroll = ttk.Scrollbar(canvas_wrap, orient=tk.HORIZONTAL, command=self.canvas.xview)
        yscroll = ttk.Scrollbar(canvas_wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        xscroll.grid(row=1, column=0, sticky="ew", padx=4)
        yscroll.grid(row=0, column=1, sticky="ns", pady=4)

        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))
        self.canvas.bind("<Shift-MouseWheel>", lambda e: self.canvas.xview_scroll(-1*(e.delta//120), "units"))
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)

    def create_statusbar(self):
        bar = ttk.Frame(self, padding=(6, 4))
        bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_lbl = ttk.Label(bar, text="Дайын")
        self.status_lbl.pack(side=tk.LEFT)

    def new_canvas_dialog(self):
        try:
            w = simpledialog.askinteger("Жаңа холст", "Ені (px):", initialvalue=self.canvas_w, minvalue=10, parent=self)
            if w is None: return False
            h = simpledialog.askinteger("Жаңа холст", "Биіктігі (px):", initialvalue=self.canvas_h, minvalue=10, parent=self)
            if h is None: return False
            bg = colorchooser.askcolor(title="Фон түсі", initialcolor=self.background)[1]
            if bg is None: bg = self.background
        except Exception:
            messagebox.showerror("Қате", "Дұрыс мән енгізіңіз.")
            return False
        self.canvas_w, self.canvas_h, self.background = int(w), int(h), bg
        self.canvas.delete("all")
        self.shapes.clear()
        self._undo_stack.clear()
        self._item_to_index.clear()
        self.apply_scrollregion()
        self.status("Жаңа холст жасалды")
        return True

    def apply_scrollregion(self):
        self.canvas.configure(scrollregion=(0, 0, self.canvas_w, self.canvas_h))

    def pick_stroke(self):
        c = colorchooser.askcolor(initialcolor=self.stroke_color)[1]
        if c: self.stroke_color = c

    def pick_fill(self):
        c = colorchooser.askcolor(initialcolor=self.fill_color)[1]
        if c: self.fill_color = c

    def focus_canvas(self): self.canvas.focus_set()
    def status(self, text): self.status_lbl.config(text=text)
    def has_content(self) -> bool: return len(self.shapes) > 0

    def new_file(self):
        if self.has_content():
            res = messagebox.askyesnocancel("Тазарту", "Кенеп тазартылады. Алдымен сақтаймыз ба?")
            if res is None:
                return
            if res is False:
                if not self.menu_save():
                    return
        self.canvas.delete("all")
        self.shapes.clear()
        self._undo_stack.clear()
        self._item_to_index.clear()
        self.status("Тазартылды")

    def menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Project JSON", "*.json")])
        if not path:
            return False
        try:
            data = {"meta": {"w": self.canvas_w, "h": self.canvas_h, "bg": self.background}, "shapes": self.shapes}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.status("Сақталды")
            return True
        except Exception as e:
            messagebox.showerror("Қате", f"Сақтау мүмкін болмады:\n{e}")
            return False

    def menu_open(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if path: self.load_project(path)

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = data.get("meta", {})
        self.canvas_w = meta.get("w", self.canvas_w)
        self.canvas_h = meta.get("h", self.canvas_h)
        self.background = meta.get("bg", self.background)
        self.shapes = data.get("shapes", [])
        self.apply_scrollregion()
        self.redraw_all()
        self.status("Ашылды")

    def on_press(self, e):
        tool = self.current_tool.get()
        self._start = (e.x, e.y)
        w = self.stroke_width.get()
        if tool == "pen":
            self._preview_item = self.canvas.create_line(e.x, e.y, e.x+1, e.y+1, fill=self.stroke_color, width=w, smooth=True)
        elif tool == "line":
            self._preview_item = self.canvas.create_line(e.x, e.y, e.x, e.y, fill=self.stroke_color, width=w)
        elif tool == "rect":
            self._preview_item = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline=self.stroke_color, width=w, fill=self.fill_color)
        elif tool == "oval":
            self._preview_item = self.canvas.create_oval(e.x, e.y, e.x, e.y, outline=self.stroke_color, width=w, fill=self.fill_color)

    def on_drag(self, e):
        if not self._preview_item or not self._start:
            return
        x0, y0 = self._start
        x1, y1 = e.x, e.y
        if self.current_tool.get() == "pen":
            coords = self.canvas.coords(self._preview_item) + [x1, y1]
            self.canvas.coords(self._preview_item, *coords)
        else:
            self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"{x1}, {y1}")

    def on_release(self, e):
        if not self._preview_item:
            return
        coords = self.canvas.coords(self._preview_item)
        t = self.current_tool.get()
        self.shapes.append({
            "type": t,
            "coords": coords,
            "stroke": self.stroke_color,
            "width": self.stroke_width.get(),
            "fill": self.fill_color if t in ("rect", "oval") else ""
        })
        self._preview_item = None
        self.status("Сызылды")

    def on_motion(self, e):
        self.status(f"Коорд: {e.x}, {e.y}")

    def redraw_all(self):
        self.canvas.delete("all")
        for s in self.shapes:
            t = s["type"]
            if t == "pen":
                self.canvas.create_line(*s["coords"], fill=s["stroke"], width=s["width"], smooth=True)
            elif t == "line":
                self.canvas.create_line(*s["coords"], fill=s["stroke"], width=s["width"])
            elif t == "rect":
                self.canvas.create_rectangle(*s["coords"], outline=s["stroke"], width=s["width"], fill=s["fill"])
            elif t == "oval":
                self.canvas.create_oval(*s["coords"], outline=s["stroke"], width=s["width"], fill=s["fill"])

    def undo(self):
        if not self.shapes:
            return
        self._undo_stack.append(self.shapes.pop())
        self.redraw_all()
        self.status("Артқа")

    def redo(self):
        if not self._undo_stack:
            return
        self.shapes.append(self._undo_stack.pop())
        self.redraw_all()
        self.status("Алға")

    def export_as(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Экспорт", "Pillow табылмады. Орнатыңыз: pip install pillow")
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("BMP", "*.bmp")])
        if not path:
            return
        W, H = int(self.canvas_w), int(self.canvas_h)
        img = Image.new("RGB", (W, H), ImageColor.getrgb(self.background))
        draw = ImageDraw.Draw(img)
        for s in self.shapes:
            t = s["type"]; c = s["coords"]; stroke = s["stroke"]; w = s["width"]
            if t == "pen":
                pts = [(c[i], c[i+1]) for i in range(0, len(c), 2)]
                if len(pts) >= 2:
                    draw.line(pts, fill=stroke, width=w)
            elif t == "line":
                draw.line(c, fill=stroke, width=w)
            elif t == "rect":
                draw.rectangle(c, outline=stroke, width=w, fill=s["fill"] or None)
            elif t == "oval":
                draw.ellipse(c, outline=stroke, width=w, fill=s["fill"] or None)
        img.save(path)
        self.status("Экспорт завершён")


if __name__ == "__main__":
    app = App()
    try:
        from ctypes import windll
        app.call('tk', 'scaling', 1.2)
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()
