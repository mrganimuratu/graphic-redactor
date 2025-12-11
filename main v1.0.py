import json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

# -----------------------------
# Simple Graphic Editor (Tkinter)
# - Main Menu (landing screen) without menubar
# - Editor screen with live preview for Line/Rect/Oval
# - Cleaner layout (sidebar tools, top bar, status bar)
# - Menubar appears only in Editor
# - Back button to MainMenu
# -----------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Қарапайым графиктік редактор — жоба")
        self.geometry("1080x700")
        self.minsize(900, 560)
        self.configure(bg="#f5f6f8")

        # Apply ttk styling for nicer look
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        default_font = ("Segoe UI", 10)
        self.style.configure("TLabel", font=default_font)
        self.style.configure("TButton", padding=6)
        self.style.configure("TFrame", background="#f5f6f8")
        self.style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Segoe UI", 11))
        self.style.map("TButton",
                       foreground=[("pressed", "!disabled"), ("active", "!disabled")],
                       )

        # Container for frames
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenu, Editor):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # Start without global menubar
        self.config(menu="")

        self.show_frame("MainMenu")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        # If entering editor, set its menubar. Otherwise clear menu.
        if name == "Editor":
            editor = self.frames["Editor"]
            # attach the editor's menubar to the app window
            try:
                self.config(menu=editor.menubar)
            except Exception:
                # fallback: set menu to empty
                self.config(menu="")
            editor.focus_canvas()
        else:
            # remove menu when on MainMenu
            self.config(menu="")

class MainMenu(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # responsive grid
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

        ttk.Button(btns, text="Жаңа жоба", command=lambda: self.app.show_frame("Editor")).grid(row=0, column=0, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Жобаны ашу", command=self.open_project).grid(row=0, column=1, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Шығу", command=self.app.destroy).grid(row=0, column=2, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")

        # subtle footer
        footer = ttk.Label(wrapper, text="Жоба — оқу/демонстрация үшін", font=("Segoe UI", 9))
        footer.grid(row=3, column=0, pady=(18, 8))

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        editor: Editor = self.app.frames["Editor"]
        try:
            editor.load_project(path)
            self.app.show_frame("Editor")
        except Exception as e:
            messagebox.showerror("Қате", f"Файлды ашу мүмкін болмады:\n{e}")

class Editor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        # State
        self.current_tool = tk.StringVar(value="line")
        self.stroke_color = "#222222"
        self.stroke_width = tk.IntVar(value=2)
        self.fill_color = ""  # empty = no fill
        self._start = None
        self._preview_item = None

        # Data for save
        self.shapes = []  # list of dicts

        # Menubar (created but not attached here)
        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Жаңа", command=self.new_file)
        file_menu.add_command(label="Ашу...", command=self.menu_open)
        file_menu.add_command(label="Сақтау...", command=self.menu_save)
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Болдырмау", command=self.undo)
        edit_menu.add_command(label="Қайтару", command=self.redo)
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)
        tool_menu = tk.Menu(self.menubar, tearoff=0)
        for tool in ("pen", "line", "rect", "oval"):
            tool_menu.add_radiobutton(label=tool.capitalize(), value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        # Layout: Top bar, left toolbar, canvas, right panel, status bar
        self.create_topbar()
        self.create_body()
        self.create_statusbar()

    # ---------- UI ----------
    def create_topbar(self):
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Құрал:").pack(side=tk.LEFT, padx=(6, 4))
        for t, lbl in [("pen", "Қалам"), ("line", "Сызық"), ("rect", "Тікбұрыш"), ("oval", "Эллипс")]:
            ttk.Radiobutton(top, text=lbl, variable=self.current_tool, value=t).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Label(top, text="Қалыңдығы:").pack(side=tk.LEFT, padx=(0, 4))
        spin = ttk.Spinbox(top, from_=1, to=20, width=4, textvariable=self.stroke_width)
        spin.pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(top, text="Сызық түсі", command=self.pick_stroke).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Құю түсі", command=self.pick_fill).pack(side=tk.LEFT, padx=4)

        ttk.Separator(top, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        ttk.Button(top, text="Сақтау", command=self.menu_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Ашу", command=self.menu_open).pack(side=tk.LEFT, padx=4)
        ttk.Button(top, text="Жаңа", command=self.new_file).pack(side=tk.LEFT, padx=4)

        # Spacer
        spacer = ttk.Frame(top)
        spacer.pack(side=tk.LEFT, expand=True)

        # Back to Main Menu button (visible in Editor)
        ttk.Button(top, text="Басты меню", command=lambda: self.app.show_frame("MainMenu")).pack(side=tk.RIGHT, padx=(4,8))

    def create_body(self):
        body = ttk.Frame(self, padding=8)
        body.pack(fill=tk.BOTH, expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        # Left sidebar
        sidebar = ttk.Frame(body, width=180)
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0,6))
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="Панель", font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
        ttk.Button(sidebar, text="Болдырмау", command=self.undo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Button(sidebar, text="Қайтару", command=self.redo).pack(fill=tk.X, padx=10, pady=4)
        ttk.Separator(sidebar).pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(sidebar, text="Кеңестер:\nShift — квадрат/дөңгелек", wraplength=160).pack(anchor="w", padx=10)

        # Canvas area
        canvas_wrap = ttk.Frame(body)
        canvas_wrap.grid(row=0, column=1, sticky="nsew")
        canvas_wrap.rowconfigure(0, weight=1)
        canvas_wrap.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_wrap, bg="white", highlightthickness=1, highlightbackground="#d0d0d0")
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        # Scrollbars
        xscroll = ttk.Scrollbar(canvas_wrap, orient=tk.HORIZONTAL, command=self.canvas.xview)
        yscroll = ttk.Scrollbar(canvas_wrap, orient=tk.VERTICAL, command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        xscroll.grid(row=1, column=0, sticky="ew", padx=4)
        yscroll.grid(row=0, column=1, sticky="ns", pady=4)

        # Bindings
        self.canvas.bind("<Button-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.on_motion)

        # make canvas initially focusable
        self.canvas.focus_set()

    def create_statusbar(self):
        status = ttk.Frame(self, padding=(6,4))
        status.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_lbl = ttk.Label(status, text="Дайын")
        self.status_lbl.pack(side=tk.LEFT, padx=8)

    # ---------- Actions ----------
    def focus_canvas(self):
        self.canvas.focus_set()

    def pick_stroke(self):
        c = colorchooser.askcolor(initialcolor=self.stroke_color)[1]
        if c:
            self.stroke_color = c

    def pick_fill(self):
        c = colorchooser.askcolor(initialcolor=self.fill_color or "#ffffff")[1]
        if c:
            self.fill_color = c

    def new_file(self):
        if messagebox.askyesno("Жаңа", "Жаңа бос кенеп бастаймыз ба? Ағымдағы жұмыс өшіріледі."):
            self.canvas.delete("all")
            self.shapes.clear()
            if hasattr(self, "_undo_stack"):
                self._undo_stack.clear()
            self.status("Жаңа басталды")

    def menu_save(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.shapes, f, ensure_ascii=False, indent=2)
            self.status("Сақталды")
        except Exception as e:
            messagebox.showerror("Қате", f"Сақтау мүмкін болмады:\n{e}")

    def menu_open(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if path:
            self.load_project(path)

    def load_project(self, path):
        with open(path, "r", encoding="utf-8") as f:
            self.shapes = json.load(f)
        self.redraw_all()
        self.status("Ашылды")

    def status(self, text):
        self.status_lbl.config(text=text)

    # ---------- Drawing logic (with live preview) ----------
    def on_press(self, e):
        self._start = (e.x, e.y)
        tool = self.current_tool.get()
        if tool == "pen":
            item = self.canvas.create_line(e.x, e.y, e.x+1, e.y+1, fill=self.stroke_color, width=self.stroke_width.get(), capstyle=tk.ROUND, smooth=True)
            self._preview_item = item
        else:
            # Create a temporary preview item
            if tool == "line":
                self._preview_item = self.canvas.create_line(e.x, e.y, e.x, e.y, fill=self.stroke_color, width=self.stroke_width.get())
            elif tool == "rect":
                self._preview_item = self.canvas.create_rectangle(e.x, e.y, e.x, e.y, outline=self.stroke_color, width=self.stroke_width.get(), fill=self.fill_color)
            elif tool == "oval":
                self._preview_item = self.canvas.create_oval(e.x, e.y, e.x, e.y, outline=self.stroke_color, width=self.stroke_width.get(), fill=self.fill_color)

    def on_drag(self, e):
        if not self._start or not self._preview_item:
            return
        x0, y0 = self._start
        x1, y1 = e.x, e.y
        if self.current_tool.get() == "pen":
            # Extend the freehand stroke
            last = self.canvas.coords(self._preview_item)
            self.canvas.coords(self._preview_item, *last, x1, y1)
        else:
            if self.current_tool.get() == "line":
                self.canvas.coords(self._preview_item, x0, y0, x1, y1)
            else:
                # Shift for square/circle if Shift pressed - support multiple masks
                shift_pressed = bool(e.state & 0x0001) or bool(e.state & 0x0004) or bool(e.state & 0x0008)
                if shift_pressed:
                    side = max(abs(x1-x0), abs(y1-y0))
                    x1 = x0 + side if x1 >= x0 else x0 - side
                    y1 = y0 + side if y1 >= y0 else y0 - side
                self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"({x1}, {y1})")

    def on_release(self, e):
        if not self._start or not self._preview_item:
            return
        x0, y0 = self._start
        x1, y1 = e.x, e.y
        tool = self.current_tool.get()
        w = self.stroke_width.get()
        stroke = self.stroke_color
        fill = self.fill_color if tool in ("rect", "oval") and self.fill_color else ""
        # Finalize shape (keep existing item, just record its data)
        if tool == "pen":
            coords = self.canvas.coords(self._preview_item)
            self.shapes.append({"type": "pen", "coords": coords, "stroke": stroke, "width": w})
        elif tool == "line":
            coords = [x0, y0, x1, y1]
            self.canvas.coords(self._preview_item, *coords)
            self.shapes.append({"type": "line", "coords": coords, "stroke": stroke, "width": w})
        elif tool == "rect":
            coords = self.canvas.coords(self._preview_item)
            self.shapes.append({"type": "rect", "coords": coords, "stroke": stroke, "width": w, "fill": fill})
        elif tool == "oval":
            coords = self.canvas.coords(self._preview_item)
            self.shapes.append({"type": "oval", "coords": coords, "stroke": stroke, "width": w, "fill": fill})
        self._start = None
        self._preview_item = None
        self.status("Сызылды")
        # clear redo stack on new action
        if hasattr(self, "_undo_stack"):
            self._undo_stack.clear()

    def on_motion(self, e):
        self.status(f"Коорд: {e.x}, {e.y} | Құрал: {self.current_tool.get()}")

    def redraw_all(self):
        self.canvas.delete("all")
        for s in self.shapes:
            t = s["type"]
            if t == "pen":
                self.canvas.create_line(*s["coords"], fill=s.get("stroke", "#000"), width=s.get("width", 2), capstyle=tk.ROUND, smooth=True)
            elif t == "line":
                self.canvas.create_line(*s["coords"], fill=s.get("stroke", "#000"), width=s.get("width", 2))
            elif t == "rect":
                self.canvas.create_rectangle(*s["coords"], outline=s.get("stroke", "#000"), width=s.get("width", 2), fill=s.get("fill", ""))
            elif t == "oval":
                self.canvas.create_oval(*s["coords"], outline=s.get("stroke", "#000"), width=s.get("width", 2), fill=s.get("fill", ""))

    # ---------- Undo/Redo (simple) ----------
    def undo(self):
        if not self.shapes:
            return
        if not hasattr(self, "_undo_stack"):
            self._undo_stack = []
        self._undo_stack.append(self.shapes.pop())
        self.redraw_all()
        self.status("Болдырмау")

    def redo(self):
        if not hasattr(self, "_undo_stack") or not self._undo_stack:
            return
        self.shapes.append(self._undo_stack.pop())
        self.redraw_all()
        self.status("Қайтару")


if __name__ == "__main__":
    app = App()
    # Windows DPI helpers (optional, safe)
    try:
        from ctypes import windll
        app.call('tk', 'scaling', 1.2)
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()