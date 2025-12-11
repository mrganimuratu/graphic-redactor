import json
import tkinter as tk
from tkinter import ttk, filedialog, colorchooser, messagebox

# -----------------------------
# Simple Graphic Editor (Tkinter) — фикс багов/улучшения
# 1) Shift корректно работает только при нажатии
# 2) Текст на кнопках не пропадает при наведении (фикс стилей)
# 3) "Жаңа" -> "Тазарту"
# 4) "Болдырмау" -> "Артқа", "Қайтару" -> "Алға"
# 5) Добавлен инструмент "Құю" (заливка фигур rect/oval по клику)
# 6) Если на холсте есть объекты, в главном меню "Жаңа жоба" -> "Жалғастыру"
# 7) Удалён нижний текст в главном меню
# 8) Добавлена кнопка ⓘ с кратким туториалом
# -----------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Қарапайым графиктік редактор — жоба")
        self.geometry("1080x700")
        self.minsize(900, 560)
        self.configure(bg="#f5f6f8")

        # ttk styling
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

        # Container
        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (MainMenu, Editor):
            frame = F(self.container, self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        # start without menubar
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
            # Обновить надпись кнопки в главном меню в зависимости от содержимого холста
            main: MainMenu = self.frames["MainMenu"]
            editor: Editor = self.frames["Editor"]
            main.update_start_button(is_dirty=editor.has_content())

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

        # Кнопка будет переименовываться в update_start_button()
        self.btn_start = ttk.Button(btns, text="Жаңа жоба", command=lambda: self.app.show_frame("Editor"))
        self.btn_start.grid(row=0, column=0, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Жобаны ашу", command=self.open_project).grid(row=0, column=1, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")
        ttk.Button(btns, text="Шығу", command=self.app.destroy).grid(row=0, column=2, padx=8, pady=6, ipadx=12, ipady=8, sticky="ew")

        # убран footer по требованию

    def update_start_button(self, is_dirty: bool):
        self.btn_start.config(text="Жалғастыру" if is_dirty else "Жаңа жоба")

    def open_project(self):
        path = filedialog.askopenfilename(filetypes=[("Project JSON", "*.json")])
        if not path:
            return
        editor: "Editor" = self.app.frames["Editor"]
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
        self._undo_stack = []

        # Menubar
        self.menubar = tk.Menu(self.app)
        file_menu = tk.Menu(self.menubar, tearoff=0)
        file_menu.add_command(label="Тазарту", command=self.new_file)  # rename
        file_menu.add_command(label="Ашу...", command=self.menu_open)
        file_menu.add_command(label="Сақтау...", command=self.menu_save)
        file_menu.add_separator()
        file_menu.add_command(label="Басты меню", command=lambda: self.app.show_frame("MainMenu"))
        file_menu.add_command(label="Шығу", command=self.app.destroy)
        self.menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        edit_menu.add_command(label="Артқа", command=self.undo)  # rename
        edit_menu.add_command(label="Алға", command=self.redo)   # rename
        self.menubar.add_cascade(label="Өңдеу", menu=edit_menu)

        tool_menu = tk.Menu(self.menubar, tearoff=0)
        for tool in ("pen", "line", "rect", "oval", "fill"):
            # labels для меню на казахском
            label_map = {
                "pen": "Қалам",
                "line": "Сызық",
                "rect": "Тікбұрыш",
                "oval": "Эллипс",
                "fill": "Құю",
            }
            tool_menu.add_radiobutton(label=label_map[tool], value=tool, variable=self.current_tool)
        self.menubar.add_cascade(label="Құралдар", menu=tool_menu)

        # Layout
        self.create_topbar()
        self.create_body()
        self.create_statusbar()

    # ---------- UI ----------
    def create_topbar(self):
        top = ttk.Frame(self, padding=(8, 6))
        top.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(top, text="Құрал:").pack(side=tk.LEFT, padx=(6, 4))
        for t, lbl in [("pen", "Қалам"), ("line", "Сызық"), ("rect", "Тікбұрыш"), ("oval", "Эллипс"), ("fill", "Құю")]:
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
        ttk.Button(top, text="Тазарту", command=self.new_file).pack(side=tk.LEFT, padx=4)  # rename

        # Spacer
        spacer = ttk.Frame(top)
        spacer.pack(side=tk.LEFT, expand=True)

        # Info (ⓘ) button — tutorial
        ttk.Button(top, text="ⓘ", width=3, command=self.show_tutorial).pack(side=tk.RIGHT, padx=(4, 8))
        # Back to Main Menu
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
        ttk.Button(sidebar, text="Артқа", command=self.undo).pack(fill=tk.X, padx=10, pady=4)  # rename
        ttk.Button(sidebar, text="Алға", command=self.redo).pack(fill=tk.X, padx=10, pady=4)   # rename
        ttk.Separator(sidebar).pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(sidebar, text="Кеңестер:\nShift — квадрат/дөңгелек\n'Құю' — фигураны бояйды", wraplength=160)\
            .pack(anchor="w", padx=10)

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
        if messagebox.askyesno("Тазарту", "Бос кенепті бастаймыз ба? Ағымдағы жұмыс өшіріледі."):
            self.canvas.delete("all")
            self.shapes.clear()
            self._undo_stack.clear()
            self.status("Тазартылды")

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

    def has_content(self) -> bool:
        return len(self.shapes) > 0

    def show_tutorial(self):
        messagebox.showinfo(
            "Туториал",
            "Құралдар: Қалам, Сызық, Тікбұрыш, Эллипс, Құю.\n"
            "- Shift ұстасаңыз: квадрат/дөңгелек.\n"
            "- 'Құю' құралымен фигураны басып бояңыз.\n"
            "- Артқа/Алға — қателікті түзету.\n"
            "- Сақтау/Ашу — JSON форматында."
        )

    # ---------- Drawing logic ----------
    def on_press(self, e):
        tool = self.current_tool.get()

        # Инструмент "Құю" — сразу применяем заливку к верхней фигуре под курсором
        if tool == "fill":
            self.apply_fill_at(e.x, e.y)
            self.status("Құю")
            return

        self._start = (e.x, e.y)
        if tool == "pen":
            item = self.canvas.create_line(
                e.x, e.y, e.x+1, e.y+1,
                fill=self.stroke_color, width=self.stroke_width.get(),
                capstyle=tk.ROUND, smooth=True
            )
            self._preview_item = item
        else:
            if tool == "line":
                self._preview_item = self.canvas.create_line(
                    e.x, e.y, e.x, e.y,
                    fill=self.stroke_color, width=self.stroke_width.get()
                )
            elif tool == "rect":
                self._preview_item = self.canvas.create_rectangle(
                    e.x, e.y, e.x, e.y,
                    outline=self.stroke_color, width=self.stroke_width.get(),
                    fill=self.fill_color or ""
                )
            elif tool == "oval":
                self._preview_item = self.canvas.create_oval(
                    e.x, e.y, e.x, e.y,
                    outline=self.stroke_color, width=self.stroke_width.get(),
                    fill=self.fill_color or ""
                )

    def on_drag(self, e):
        if not self._start or not self._preview_item:
            return
        if self.current_tool.get() == "fill":
            return  # нет предпросмотра для заливки

        x0, y0 = self._start
        x1, y1 = e.x, e.y
        if self.current_tool.get() == "pen":
            last = self.canvas.coords(self._preview_item)
            self.canvas.coords(self._preview_item, *last, x1, y1)
        else:
            if self.current_tool.get() == "line":
                self.canvas.coords(self._preview_item, x0, y0, x1, y1)
            else:
                # Корректная проверка Shift — только ShiftMask (0x0001)
                shift_pressed = (e.state & 0x0001) != 0
                if shift_pressed:
                    side = max(abs(x1 - x0), abs(y1 - y0))
                    x1 = x0 + side if x1 >= x0 else x0 - side
                    y1 = y0 + side if y1 >= y0 else y0 - side
                self.canvas.coords(self._preview_item, x0, y0, x1, y1)
        self.status(f"({x1}, {y1})")

    def on_release(self, e):
        if self.current_tool.get() == "fill":
            return  # ничего не делаем тут

        if not self._start or not self._preview_item:
            return
        x0, y0 = self._start
        x1, y1 = e.x, e.y
        tool = self.current_tool.get()
        w = self.stroke_width.get()
        stroke = self.stroke_color
        fill = self.fill_color if tool in ("rect", "oval") and self.fill_color else ""
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
        self._undo_stack.clear()

    def on_motion(self, e):
        self.status(f"Коорд: {e.x}, {e.y} | Құрал: {self.current_tool.get()}")

    def apply_fill_at(self, x, y):
        # найти верхнюю фигуру (rect/oval) под курсором и применить заливку
        # через пересечение маленького прямоугольника
        items = self.canvas.find_overlapping(x, y, x, y)
        if not items:
            return
        top_item = items[-1]
        # восстановить по координатам совпадающую фигуру
        coords = self.canvas.coords(top_item)
        # ищем последнюю фигуру с такими координатами
        for s in reversed(self.shapes):
            if s.get("coords") == coords and s["type"] in ("rect", "oval"):
                s["fill"] = self.fill_color or "#ffffff"
                break
        self.redraw_all()

    def redraw_all(self):
        self.canvas.delete("all")
        for s in self.shapes:
            t = s["type"]
            if t == "pen":
                self.canvas.create_line(
                    *s["coords"], fill=s.get("stroke", "#000"),
                    width=s.get("width", 2), capstyle=tk.ROUND, smooth=True
                )
            elif t == "line":
                self.canvas.create_line(
                    *s["coords"], fill=s.get("stroke", "#000"),
                    width=s.get("width", 2)
                )
            elif t == "rect":
                self.canvas.create_rectangle(
                    *s["coords"], outline=s.get("stroke", "#000"),
                    width=s.get("width", 2), fill=s.get("fill", "")
                )
            elif t == "oval":
                self.canvas.create_oval(
                    *s["coords"], outline=s.get("stroke", "#000"),
                    width=s.get("width", 2), fill=s.get("fill", "")
                )

    # ---------- Undo/Redo ----------
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
