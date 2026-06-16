import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, Image, HRFlowable, PageBreak)
import io, os, warnings
warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────
BG       = "#0F1117"
PANEL    = "#1A1D2E"
CARD     = "#20243A"
ACCENT   = "#4F8EF7"
ACCENT2  = "#A259FF"
SUCCESS  = "#2ECC71"
WARNING  = "#F39C12"
DANGER   = "#E74C3C"
TEXT     = "#E8EAED"
SUBTEXT  = "#9AA0B4"
BORDER   = "#2D3150"
ENTRY_BG = "#12152A"
ENTRY_FG = "#E8EAED"

plt.style.use('dark_background')
sns.set_theme(style="darkgrid")

CHART_W = 6.8   # fixed chart width  (inches)
CHART_H = 3.6   # fixed chart height (inches)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def styled_btn(parent, text, command, color=ACCENT, fg="#FFFFFF", width=18):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg=fg, font=("Segoe UI", 10, "bold"),
                     relief="flat", bd=0, padx=12, pady=7,
                     cursor="hand2", activebackground=ACCENT2,
                     activeforeground=fg, width=width)


def card_frame(parent, title=None, pady=8, padx=8):
    outer = tk.Frame(parent, bg=CARD, relief="flat", bd=0,
                     highlightbackground=BORDER, highlightthickness=1)
    if title:
        tk.Label(outer, text=title, bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
    inner = tk.Frame(outer, bg=CARD)
    inner.pack(fill="both", expand=True, padx=padx, pady=pady)
    return outer, inner


def section_label(parent, text):
    tk.Label(parent, text=text, bg=PANEL, fg=ACCENT,
             font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(12, 4))


def make_scrollable_area(parent):
    """Returns inner_frame inside a Canvas+Scrollbar — pack chart rows here."""
    container = tk.Frame(parent, bg=PANEL)
    container.pack(fill="both", expand=True)

    vbar = tk.Scrollbar(container, orient="vertical", bg=PANEL)
    vbar.pack(side="right", fill="y")

    canvas = tk.Canvas(container, bg=PANEL, highlightthickness=0,
                       yscrollcommand=vbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    vbar.config(command=canvas.yview)

    inner = tk.Frame(canvas, bg=PANEL)
    win   = canvas.create_window((0, 0), window=inner, anchor="nw")

    def _resize(e):
        canvas.itemconfig(win, width=e.width)
    canvas.bind("<Configure>", _resize)

    def _update_scroll(e):
        canvas.configure(scrollregion=canvas.bbox("all"))
    inner.bind("<Configure>", _update_scroll)

    def _mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", _mousewheel)

    return inner


def add_chart_row(parent, figs_list):
    """
    Embeds up to 2 figures in a horizontal row.
    Both charts get identical fixed pixel size so they never overlap.
    """
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", padx=8, pady=6)

    # ✅ Equal columns (IMPORTANT)
    for i in range(2):
        row.grid_columnconfigure(i, weight=1)

    px_w = int(CHART_W * 96)
    px_h = int(CHART_H * 96)

    for idx, fig in enumerate(figs_list):
        card = tk.Frame(row, bg=CARD,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=idx, padx=6, pady=4, sticky="nsew")

        cv = FigureCanvasTkAgg(fig, master=card)
        cv.draw()

        widget = cv.get_tk_widget()
        widget.configure(width=px_w, height=px_h)
        widget.pack(fill="both", expand=True, padx=4, pady=4)


# ─────────────────────────────────────────────────────────────
# MAIN APPLICATION
# ─────────────────────────────────────────────────────────────
class StressTestApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚙  Stress Testing & Scenario Analysis  |  Manufacturing Domain")
        self.geometry("1350x860")
        self.configure(bg=BG)
        self.resizable(True, True)

        self.df_raw      = None
        self.df_clean    = None
        self.num_cols    = []
        self.corr_matrix = None
        self.figures     = {}

        self._build_ui()

    # ── TOP BANNER ────────────────────────────────────────────
    def _build_ui(self):
        banner = tk.Frame(self, bg=PANEL, height=56)
        banner.pack(fill="x")
        banner.pack_propagate(False)
        tk.Label(banner, text="⚙  Stress Testing & Scenario Analysis",
                 bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 15, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(banner, text="Manufacturing / Industrial Domain  |  P&S Project",
                 bg=PANEL, fg=SUBTEXT,
                 font=("Segoe UI", 10)).pack(side="right", padx=20)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=PANEL, foreground=SUBTEXT,
                        font=("Segoe UI", 10, "bold"), padding=[16, 8])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#FFFFFF")])
        style.configure("TV.Treeview",
                         background=CARD, foreground=TEXT,
                         rowheight=26, fieldbackground=CARD, borderwidth=0)
        style.configure("TV.Treeview.Heading",
                         background=PANEL, foreground=ACCENT,
                         font=("Segoe UI", 9, "bold"))
        style.map("TV.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#FFFFFF")])

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        self.tab_data     = tk.Frame(nb, bg=PANEL)
        self.tab_eda      = tk.Frame(nb, bg=PANEL)
        self.tab_stress   = tk.Frame(nb, bg=PANEL)
        self.tab_scenario = tk.Frame(nb, bg=PANEL)
        self.tab_report   = tk.Frame(nb, bg=PANEL)

        nb.add(self.tab_data,     text="  📂 Data Input  ")
        nb.add(self.tab_eda,      text="  📊 EDA & Insights  ")
        nb.add(self.tab_stress,   text="  🔥 Stress Testing  ")
        nb.add(self.tab_scenario, text="  🎲 Scenario Analysis  ")
        nb.add(self.tab_report,   text="  📄 Export Report  ")

        self._build_data_tab()
        self._build_eda_tab()
        self._build_stress_tab()
        self._build_scenario_tab()
        self._build_report_tab()

    # ══════════════════════════════════════════════════════════
    # TAB 1 — DATA INPUT
    # ══════════════════════════════════════════════════════════
    def _build_data_tab(self):
        p    = self.tab_data
        left = tk.Frame(p, bg=PANEL, width=300)
        left.pack(side="left", fill="y", padx=(10, 4), pady=10)
        left.pack_propagate(False)
        right = tk.Frame(p, bg=PANEL)
        right.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=10)

        # CSV Upload
        co, ci = card_frame(left, "📂 Upload CSV File")
        co.pack(fill="x", pady=(0, 8))
        styled_btn(ci, "Browse CSV File", self._load_csv, width=22).pack(pady=4)
        self.lbl_file = tk.Label(ci, text="No file selected", bg=CARD, fg=SUBTEXT,
                                  font=("Segoe UI", 9), wraplength=230)
        self.lbl_file.pack(pady=2)

        # Manual Entry
        mo, mi = card_frame(left, "✏  Manual Data Entry")
        mo.pack(fill="x", pady=(0, 8))
        tk.Label(mi, text="Columns (comma-sep):", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w")
        self.ent_cols = tk.Entry(mi, bg=ENTRY_BG, fg=ENTRY_FG,
                                  insertbackground=TEXT, font=("Segoe UI", 9),
                                  relief="flat", bd=4)
        self.ent_cols.insert(0, "Units_Sold,Revenue,Defects,Downtime,Profit")
        self.ent_cols.pack(fill="x", pady=2)
        tk.Label(mi, text="Rows (one per line, comma-sep):", bg=CARD, fg=TEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        self.txt_manual = tk.Text(mi, height=7, bg=ENTRY_BG, fg=ENTRY_FG,
                                   insertbackground=TEXT, font=("Courier", 9),
                                   relief="flat", bd=4)
        self.txt_manual.insert("1.0",
            "320,45000,8,2.5,12000\n410,58000,5,1.2,18000\n"
            "290,38000,12,4.1,8000\n380,52000,6,1.8,15000\n"
            "450,63000,3,0.9,22000\n260,34000,15,5.2,5000\n"
            "400,55000,7,2.0,16000\n350,48000,9,3.1,11000\n"
            "480,70000,2,0.7,25000\n300,41000,11,3.8,9000\n"
            "420,59000,4,1.5,19000\n370,51000,8,2.4,13000")
        self.txt_manual.pack(fill="x", pady=2)
        styled_btn(mi, "Load Manual Data", self._load_manual,
                   color=SUCCESS, width=22).pack(pady=6)

        # Cleaning
        clo, cli = card_frame(left, "🧹 Data Cleaning Options")
        clo.pack(fill="x", pady=(0, 8))
        self.var_nulls    = tk.BooleanVar(value=True)
        self.var_outliers = tk.BooleanVar(value=True)
        for txt, var in [("Remove / fill null values", self.var_nulls),
                          ("Remove outliers (IQR method)", self.var_outliers)]:
            tk.Checkbutton(cli, text=txt, variable=var, bg=CARD, fg=TEXT,
                           selectcolor=ENTRY_BG, font=("Segoe UI", 9),
                           activebackground=CARD).pack(anchor="w")
        styled_btn(cli, "Apply Cleaning", self._apply_cleaning,
                   color=WARNING, width=22).pack(pady=6)

        # ── RIGHT: Data Preview ─────────────────────────────────
        section_label(right, "📋 Data Preview  (use scrollbar → to see all columns)")

        frame_prev = tk.Frame(right, bg=CARD,
                              highlightbackground=BORDER, highlightthickness=1)
        frame_prev.pack(fill="both", expand=True, pady=(0, 6))

        # CRITICAL pack order: scrollbars first, then treeview
        vbar = tk.Scrollbar(frame_prev, orient="vertical")
        hbar = tk.Scrollbar(frame_prev, orient="horizontal")
        vbar.pack(side="right",  fill="y")
        hbar.pack(side="bottom", fill="x")

        self.tree_prev = ttk.Treeview(frame_prev,
                                       yscrollcommand=vbar.set,
                                       xscrollcommand=hbar.set,
                                       show="headings",
                                       style="TV.Treeview")
        self.tree_prev.pack(fill="both", expand=True)   # pack LAST

        vbar.config(command=self.tree_prev.yview)
        hbar.config(command=self.tree_prev.xview)

        self.lbl_shape = tk.Label(right, text="No data loaded",
                                   bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9))
        self.lbl_shape.pack(anchor="w", pady=2)

        section_label(right, "📌 Field Information")
        self.txt_fields = scrolledtext.ScrolledText(
            right, height=6, bg=CARD, fg=TEXT,
            font=("Courier", 9), relief="flat", bd=4)
        self.txt_fields.pack(fill="x")

    # ── data helpers ───────────────────────────────────────────
    def _load_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All", "*.*")])
        if not path:
            return
        try:
            self.df_raw = pd.read_csv(path)
            self.lbl_file.config(text=os.path.basename(path))
            self._refresh_preview(self.df_raw)
            self._apply_cleaning()
            messagebox.showinfo("Success",
                f"Loaded {len(self.df_raw)} rows × {len(self.df_raw.columns)} columns")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _load_manual(self):
        try:
            cols = [c.strip() for c in self.ent_cols.get().split(",")]
            raw  = self.txt_manual.get("1.0", "end").strip().split("\n")
            rows = [[float(x) for x in r.split(",")] for r in raw if r.strip()]
            self.df_raw = pd.DataFrame(rows, columns=cols)
            self._refresh_preview(self.df_raw)
            self._apply_cleaning()
            messagebox.showinfo("Success",
                f"Loaded {len(self.df_raw)} rows of manual data")
        except Exception as e:
            messagebox.showerror("Error", f"Check your data format.\n{e}")

    def _apply_cleaning(self):
        if self.df_raw is None:
            messagebox.showwarning("Warning", "Load data first!")
            return
        df = self.df_raw.copy()
        removed_nulls = removed_outliers = 0

        if self.var_nulls.get():
            removed_nulls = int(df.isnull().sum().sum())
            df = df.fillna(df.mean(numeric_only=True))

        if self.var_outliers.get():
            num = df.select_dtypes(include=np.number)
            Q1  = num.quantile(0.25)
            Q3  = num.quantile(0.75)
            IQR = Q3 - Q1
            mask = ~((num < Q1 - 1.5*IQR) | (num > Q3 + 1.5*IQR)).any(axis=1)
            before = len(df)
            df = df[mask]
            removed_outliers = before - len(df)

        self.df_clean    = df.reset_index(drop=True)
        self.num_cols    = list(df.select_dtypes(include=np.number).columns)
        self.corr_matrix = df[self.num_cols].corr()

        self._refresh_preview(self.df_clean)
        self._update_fields_info(removed_nulls, removed_outliers)
        self._populate_combos()
        messagebox.showinfo("Cleaning Done",
            f"Nulls filled: {removed_nulls}\n"
            f"Outliers removed: {removed_outliers}\n"
            f"Clean rows: {len(self.df_clean)}")

    def _refresh_preview(self, df):
        self.tree_prev.delete(*self.tree_prev.get_children())
        cols = list(df.columns)
        self.tree_prev["columns"] = cols
        for c in cols:
            self.tree_prev.heading(c, text=c, anchor="center")
            # fixed width per column — horizontal scrollbar handles overflow
            self.tree_prev.column(c, width=140, minwidth=100,
                                   anchor="center", stretch=False)
        for _, row in df.head(50).iterrows():
            self.tree_prev.insert("", "end", values=list(row))
        self.lbl_shape.config(
            text=f"Shape: {df.shape[0]} rows × {df.shape[1]} columns  "
                 f"(showing first 50 rows)")

    def _update_fields_info(self, nulls, outliers):
        df = self.df_clean
        self.txt_fields.config(state="normal")
        self.txt_fields.delete("1.0", "end")
        hdr = (f"{'FIELD':<22} {'TYPE':<12} {'NULLS':<8} "
               f"{'UNIQUE':<10} {'MIN':<12} {'MAX':<12}")
        lines = [hdr, "-" * 78]
        for c in df.columns:
            dtype  = str(df[c].dtype)
            n_null = df[c].isnull().sum()
            n_uniq = df[c].nunique()
            is_num = pd.api.types.is_numeric_dtype(df[c])
            mn     = f"{df[c].min():.2f}" if is_num else "N/A"
            mx     = f"{df[c].max():.2f}" if is_num else "N/A"
            lines.append(
                f"{c:<22} {dtype:<12} {n_null:<8} {n_uniq:<10} {mn:<12} {mx:<12}")
        lines.append(f"\n✔ Nulls filled: {nulls}  |  Outliers removed: {outliers}")
        self.txt_fields.insert("1.0", "\n".join(lines))
        self.txt_fields.config(state="disabled")

    def _populate_combos(self):
        if not self.num_cols:
            return
        self.combo_dist["values"]       = self.num_cols
        self.combo_dist.set(self.num_cols[0])
        self.combo_stress_col["values"] = self.num_cols
        self.combo_stress_col.set(self.num_cols[0])
        self.combo_target["values"]     = self.num_cols
        self.combo_target.set(self.num_cols[-1])

    # ══════════════════════════════════════════════════════════
    # TAB 2 — EDA & INSIGHTS
    # ══════════════════════════════════════════════════════════
    def _build_eda_tab(self):
        p    = self.tab_eda
        ctrl = tk.Frame(p, bg=PANEL, width=255)
        ctrl.pack(side="left", fill="y", padx=(10, 4), pady=10)
        ctrl.pack_propagate(False)

        self.eda_plot_area = tk.Frame(p, bg=PANEL)
        self.eda_plot_area.pack(side="left", fill="both", expand=True,
                                padx=(4, 10), pady=10)

        section_label(ctrl, "📊 EDA Controls")
        styled_btn(ctrl, "Descriptive Statistics",
                   self._show_desc_stats, width=26).pack(pady=4, fill="x")
        styled_btn(ctrl, "Correlation Heatmap",
                   self._show_corr_heatmap, width=26).pack(pady=4, fill="x")

        tk.Label(ctrl, text="Distribution of:", bg=PANEL, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(10, 0))
        self.var_dist_col = tk.StringVar()
        self.combo_dist   = ttk.Combobox(ctrl, textvariable=self.var_dist_col,
                                          state="readonly", font=("Segoe UI", 9))
        self.combo_dist.pack(fill="x", pady=2)
        styled_btn(ctrl, "Plot Distribution",
                   self._show_distribution, width=26).pack(pady=4, fill="x")
        styled_btn(ctrl, "Trend Analysis (All)",
                   self._show_trends, width=26).pack(pady=4, fill="x")
        styled_btn(ctrl, "Auto Insights",
                   self._show_insights, color=ACCENT2, width=26).pack(pady=4, fill="x")

        section_label(ctrl, "📋 Quick Stats")
        self.txt_stats = scrolledtext.ScrolledText(
            ctrl, bg=CARD, fg=TEXT, font=("Courier", 8),
            relief="flat", bd=4)
        self.txt_stats.pack(fill="both", expand=True, pady=4)

    def _check_data(self):
        if self.df_clean is None:
            messagebox.showwarning("No Data",
                "Please load and clean data first (Tab 1).")
            return False
        return True

    def _clear_plot_area(self):
        for w in self.eda_plot_area.winfo_children():
            w.destroy()

    def _new_fig(self):
        """Create a blank styled figure at fixed size."""
        fig, ax = plt.subplots(figsize=(CHART_W, CHART_H), facecolor=BG)
        ax.set_facecolor(CARD)
        for sp in ax.spines.values():
            sp.set_edgecolor(BORDER)
        return fig, ax

    def _section_header(self, parent, title, subtitle=""):
        tk.Label(parent, text=title, bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 13, "bold")).pack(
                 anchor="w", padx=10, pady=(10, 2))
        if subtitle:
            tk.Label(parent, text=subtitle, bg=PANEL, fg=SUBTEXT,
                     font=("Segoe UI", 9)).pack(
                     anchor="w", padx=10, pady=(0, 6))

    # ── Descriptive Statistics ─────────────────────────────────
    def _show_desc_stats(self):
        if not self._check_data():
            return
        df   = self.df_clean[self.num_cols]
        desc = df.describe().T
        desc["skewness"] = df.skew()
        desc["kurtosis"] = df.kurtosis()

        self.txt_stats.config(state="normal")
        self.txt_stats.delete("1.0", "end")

        explanation = (
            "📊 QUICK STATS GUIDE\n"
            "──────────────────────────────\n"
            "Mean       → Average value\n"
            "Std Dev    → Data spread (higher = more variation)\n"
            "Min / Max  → Lowest / Highest value\n"
            "25%        → 25% of data is below this\n"
            "50%        → Median (middle value)\n"
            "75%        → 75% of data is below this\n"
            "Skewness   → Data symmetry\n"
            "              > 0 → Right skewed\n"
            "              < 0 → Left skewed\n"
            "Kurtosis   → Outliers presence\n"
            "              > 0 → More outliers\n"
            "              < 0 → Fewer outliers\n"
            "\n📌 VALUES:\n"
            "──────────────────────────────\n"
        )

        self.txt_stats.insert("1.0",
            explanation + desc.to_string(float_format=lambda x: f"{x:.3f}"))
        self.txt_stats.config(state="disabled")

        self._clear_plot_area()
        inner = make_scrollable_area(self.eda_plot_area)

        self._section_header(inner,
            "📊 Descriptive Statistics — All Metrics",
            "  Each chart shows one statistic for all variables  |  Scroll ↓ to see all")

        # ── Full table ────────────────────────────────────────
        tbl_f = tk.Frame(inner, bg=CARD,
                         highlightbackground=BORDER, highlightthickness=1)
        tbl_f.pack(fill="x", padx=8, pady=(0, 10))
        tk.Label(tbl_f, text="  Full Statistics Table",
                 bg=CARD, fg=ACCENT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=6, pady=(4, 0))
        tbl_txt = tk.Text(tbl_f, height=len(self.num_cols) + 3,
                          bg=ENTRY_BG, fg=TEXT, font=("Courier", 9),
                          relief="flat", bd=4)
        tbl_txt.pack(fill="x", padx=6, pady=(2, 6))
        hdr = (f"{'Variable':<22} {'Count':>6} {'Mean':>10} {'Std':>10} "
               f"{'Min':>10} {'25%':>10} {'50%':>10} {'75%':>10} "
               f"{'Max':>10} {'Skew':>8} {'Kurt':>8}")
        tbl_txt.insert("end", hdr + "\n" + "─" * 116 + "\n")
        for var in self.num_cols:
            r = desc.loc[var]
            tbl_txt.insert("end",
                f"{var:<22} {int(r['count']):>6} {r['mean']:>10.3f} "
                f"{r['std']:>10.3f} {r['min']:>10.3f} {r['25%']:>10.3f} "
                f"{r['50%']:>10.3f} {r['75%']:>10.3f} {r['max']:>10.3f} "
                f"{r['skewness']:>8.3f} {r['kurtosis']:>8.3f}\n")
        tbl_txt.config(state="disabled")

        # ── Individual charts — 2 per row, identical fixed size ──
        metrics   = ["mean","std","min","max","25%","50%","75%","skewness","kurtosis"]
        labels    = ["Mean","Std Deviation","Minimum","Maximum",
                     "25th Percentile","Median (50th)","75th Percentile",
                     "Skewness","Kurtosis"]
        clrs      = [ACCENT, ACCENT2, SUCCESS, DANGER, WARNING,
                     "#00BCD4","#FF9800","#E91E63","#8BC34A"]
        descs_txt = [
            "Average value of each variable",
            "Spread / variability around the mean",
            "Lowest recorded value per variable",
            "Highest recorded value per variable",
            "Value below which 25% of data falls",
            "Middle value — robust central measure",
            "Value below which 75% of data falls",
            "Asymmetry: >0 right-skewed  <0 left-skewed",
            "Tail heaviness: >0 means outlier-prone"
        ]

        all_figs = []
        batch    = []

        for idx in range(len(metrics)):
            m, lbl, cl, dsc = metrics[idx], labels[idx], clrs[idx], descs_txt[idx]
            vals = desc[m]

            fig, ax = self._new_fig()
            x_pos   = np.arange(len(vals))
            bars    = ax.bar(x_pos, vals, color=cl, alpha=0.82,
                             edgecolor="none", width=0.6)

            rng = (vals.max() - vals.min()) or 1
            for bar, v in zip(bars, vals):
                ypos   = bar.get_height()
                offset = rng * 0.03
                va     = "bottom" if ypos >= 0 else "top"
                ax.text(bar.get_x() + bar.get_width() / 2,
                        ypos + (offset if ypos >= 0 else -offset),
                        f"{v:.2f}", ha="center", va=va,
                        fontsize=8, color=TEXT, fontweight="bold")

            ax.set_xticks(x_pos)
            ax.set_xticklabels(vals.index, rotation=35, ha="right",
                               fontsize=9, color=SUBTEXT)
            ax.set_title(lbl, color=TEXT, fontsize=11, fontweight="bold", pad=10)
            ax.set_ylabel(lbl, color=SUBTEXT, fontsize=9)
            ax.tick_params(axis="y", colors=SUBTEXT, labelsize=8)
            ax.axhline(0, color=BORDER, lw=0.8, ls="--")
            ax.text(0.5, 1.01, dsc, transform=ax.transAxes,
                    fontsize=8, color=SUBTEXT, ha="center", va="bottom",wrap=True)
            fig.tight_layout(rect=[0, 0, 1, 0.95])

            all_figs.append(fig)
            batch.append(fig)

            if len(batch) == 2:
                add_chart_row(inner, batch)
                batch = []

        if batch:                      # last single chart
            add_chart_row(inner, batch)

        self.figures["desc_stats"]     = all_figs[0]
        self.figures["desc_stats_all"] = all_figs

    # ── Correlation Heatmap ────────────────────────────────────
    def _show_corr_heatmap(self):
        if not self._check_data():
            return
        self._clear_plot_area()
        corr = self.corr_matrix
        n    = len(corr)
        sz   = max(6, n * 0.9)
        fig, ax = plt.subplots(figsize=(sz, sz * 0.85), facecolor=BG)
        cmap = sns.diverging_palette(230, 20, as_cmap=True)
        sns.heatmap(corr, annot=True, fmt=".2f", cmap=cmap, ax=ax,
                    linewidths=0.5, linecolor=BORDER,
                    annot_kws={"size": 9}, vmin=-1, vmax=1,
                    cbar_kws={"shrink": 0.8})
        ax.set_facecolor(CARD)
        ax.set_title("Correlation Matrix Heatmap",
                     color=TEXT, fontsize=13, fontweight="bold", pad=12)
        ax.tick_params(colors=TEXT)
        fig.tight_layout()
        self.figures["heatmap"] = fig
        cv = FigureCanvasTkAgg(fig, master=self.eda_plot_area)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

        self.txt_stats.config(state="normal")
        self.txt_stats.delete("1.0", "end")
        self.txt_stats.insert("1.0",
            "STRONG CORRELATIONS (|r| > 0.5):\n" + "─" * 40 + "\n")
        for i in range(n):
            for j in range(i + 1, n):
                r = corr.iloc[i, j]
                if abs(r) > 0.5:
                    d = "↑↑ Positive" if r > 0 else "↑↓ Negative"
                    self.txt_stats.insert("end",
                        f"{corr.columns[i]} ↔ {corr.columns[j]}\n"
                        f"  r = {r:.3f}  [{d}]\n\n")
        self.txt_stats.config(state="disabled")

    # ── Distribution ───────────────────────────────────────────
    def _show_distribution(self):
        if not self._check_data():
            return
        col = self.var_dist_col.get()
        if not col:
            return
        self._clear_plot_area()
        data    = self.df_clean[col].dropna()
        mu      = data.mean()
        sigma   = data.std()

        tk.Label(self.eda_plot_area,
                 text=f"Distribution Analysis — {col}",
                 bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=10, pady=(6,2))

        row_f = tk.Frame(self.eda_plot_area, bg=PANEL)
        row_f.pack(fill="x", padx=8, pady=4)

        px_w = int(CHART_W * 96)
        px_h = int(CHART_H * 96)

        # ── Histogram ───────────────────────────────
        fig0, ax0 = self._new_fig()
        ax0.hist(data, bins=20, color=ACCENT, alpha=0.7,
                 edgecolor="none", density=True)
        x = np.linspace(data.min(), data.max(), 200)
        ax0.plot(x, stats.norm.pdf(x, mu, sigma),
                 color=ACCENT2, lw=2, label="Normal fit")
        ax0.set_title("Histogram + Normal Fit",
                      color=TEXT, fontsize=10, fontweight="bold")
        ax0.set_xlabel(col, color=SUBTEXT, fontsize=8)
        ax0.set_ylabel("Density", color=SUBTEXT, fontsize=8)
        ax0.tick_params(colors=SUBTEXT, labelsize=7)
        ax0.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)
        fig0.tight_layout(pad=1.6)

        # ── Box Plot ─────────────────────────────────
        fig1, ax1 = self._new_fig()
        ax1.boxplot(data, patch_artist=True, notch=True,
                    boxprops=dict(facecolor=ACCENT, color=ACCENT),
                    medianprops=dict(color=SUCCESS, linewidth=2),
                    whiskerprops=dict(color=SUBTEXT),
                    capprops=dict(color=SUBTEXT),
                    flierprops=dict(marker='o', color=DANGER, markersize=4))
        ax1.set_title("Box Plot", color=TEXT, fontsize=10, fontweight="bold")
        ax1.set_ylabel(col, color=SUBTEXT, fontsize=8)
        ax1.tick_params(colors=SUBTEXT, labelsize=7)
        fig1.tight_layout(pad=1.6)

        # ── Q-Q Plot ─────────────────────────────────
        fig2, ax2 = self._new_fig()
        (osm, osr), (slope, intercept, r) = stats.probplot(data)
        ax2.scatter(osm, osr, color=ACCENT, alpha=0.7, s=18)
        ax2.plot(osm, slope * np.array(osm) + intercept,
                 color=ACCENT2, lw=2, label=f"R²={r**2:.3f}")
        ax2.set_title("Q-Q Plot (Normality Check)",
                      color=TEXT, fontsize=10, fontweight="bold")
        ax2.set_xlabel("Theoretical Quantiles", color=SUBTEXT, fontsize=8)
        ax2.set_ylabel("Sample Quantiles", color=SUBTEXT, fontsize=8)
        ax2.tick_params(colors=SUBTEXT, labelsize=7)
        ax2.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)
        fig2.tight_layout(pad=1.6)

        for fig in [fig0, fig1, fig2]:
            card = tk.Frame(row_f, bg=CARD,
                            highlightbackground=BORDER, highlightthickness=1)
            card.pack(side="left", padx=5, pady=2)
            cv = FigureCanvasTkAgg(fig, master=card)
            cv.draw()
            cv.get_tk_widget().configure(width=px_w, height=px_h)
            cv.get_tk_widget().pack(padx=4, pady=4)

        sk    = stats.skew(data)
        ku    = stats.kurtosis(data)
        _, pn = stats.shapiro(data[:50])
        self.txt_stats.config(state="normal")
        self.txt_stats.delete("1.0", "end")
        self.txt_stats.insert("1.0",
            f"Variable : {col}\n{'─'*28}\n"
            f"Mean     : {mu:.4f}\nStd Dev  : {sigma:.4f}\n"
            f"Min      : {data.min():.4f}\nMax      : {data.max():.4f}\n"
            f"Skewness : {sk:.4f}\nKurtosis : {ku:.4f}\n"
            f"Shapiro p: {pn:.4f}\n"
            f"Normal?  : {'YES ✔' if pn > 0.05 else 'NO ✘'}\n")
        self.txt_stats.config(state="disabled")
        self.figures[f"dist_{col}"] = fig0

    # ── Trend Analysis ─────────────────────────────────────────
    def _show_trends(self):
        if not self._check_data():
            return
        self._clear_plot_area()
        df = self.df_clean
        x  = np.arange(len(df))

        inner = make_scrollable_area(self.eda_plot_area)
        self._section_header(inner,
            "📈 Trend Analysis — All Variables",
            "  Blue=Actual  |  Purple=5-pt Rolling Avg  |  "
            "Orange dashed=Trend Line  |  Scroll ↓ for more")

        all_figs = []
        batch    = []

        for col in self.num_cols:
            data = df[col].values
            fig, ax = self._new_fig()

            ax.plot(x, data, color=ACCENT, alpha=0.55, lw=1.2, label="Actual")

            if len(df) >= 5:
                roll = pd.Series(data).rolling(5, min_periods=1).mean()
                ax.plot(x, roll, color=ACCENT2, lw=2, label="5-pt Avg")

            z  = np.polyfit(x, data, 1)
            pf = np.poly1d(z)
            direction = "↑" if z[0] >= 0 else "↓"
            ax.plot(x, pf(x), "--", color=WARNING, lw=2,
                    label=f"Trend {direction} ({z[0]:+.3f}/obs)")

            if "Date" in df.columns:
                step  = max(1, len(df) // 8)
                ticks = x[::step]
                xlbls = df["Date"].iloc[::step].astype(str).str[:10].tolist()
                ax.set_xticks(ticks)
                ax.set_xticklabels(xlbls, rotation=30, ha="right",
                                   fontsize=8, color=SUBTEXT)
            else:
                ax.set_xlabel("Observation Index", color=SUBTEXT, fontsize=8)
                ax.tick_params(axis="x", colors=SUBTEXT, labelsize=8)

            ax.set_title(col, color=TEXT, fontsize=11, fontweight="bold", pad=8)
            ax.set_ylabel(col, color=SUBTEXT, fontsize=9)
            ax.tick_params(axis="y", colors=SUBTEXT, labelsize=8)
            ax.legend(fontsize=8, facecolor=PANEL, edgecolor=BORDER,
                      labelcolor=TEXT, loc="upper right", framealpha=0.9)

            ann = (f"μ = {data.mean():.2f}  σ = {data.std():.2f}\n"
                   f"Min = {data.min():.2f}  Max = {data.max():.2f}")
            ax.text(0.01, 0.97, ann, transform=ax.transAxes,
                    fontsize=8, color=TEXT, va="top", ha="left",
                    bbox=dict(boxstyle="round,pad=0.35", facecolor=ENTRY_BG,
                              edgecolor=BORDER, alpha=0.9))
            fig.tight_layout(rect=[0, 0, 1, 0.95])

            all_figs.append(fig)
            batch.append(fig)

            if len(batch) == 2:
                add_chart_row(inner, batch)
                batch = []

        if batch:
            add_chart_row(inner, batch)

        self.figures["trends"]     = all_figs[0] if all_figs else None
        self.figures["trends_all"] = all_figs

    # ── Auto Insights ──────────────────────────────────────────
    def _show_insights(self):
        if not self._check_data():
            return
        df       = self.df_clean
        insights = []

        for col in self.num_cols:
            sk    = stats.skew(df[col])
            mu    = df[col].mean()
            sigma = df[col].std()
            cv    = sigma / mu * 100 if mu != 0 else 0
            z     = np.polyfit(np.arange(len(df)), df[col], 1)
            if abs(sk) > 1:
                insights.append(
                    f"⚠  {col}: Highly skewed ({sk:.2f}) — not normally distributed")
            if cv > 30:
                insights.append(
                    f"📈 {col}: High variability (CV={cv:.1f}%) — process inconsistency")
            if z[0] > 0.05 * abs(mu):
                insights.append(f"↗  {col}: Significant INCREASING trend detected")
            elif z[0] < -0.05 * abs(mu):
                insights.append(f"↘  {col}: Significant DECREASING trend detected")

        corr = self.corr_matrix
        n    = len(corr.columns)
        for i in range(n):
            for j in range(i + 1, n):
                r = corr.iloc[i, j]
                if r > 0.7:
                    insights.append(
                        f"🔗 Strong POSITIVE correlation: "
                        f"{corr.columns[i]} ↔ {corr.columns[j]} (r={r:.2f})")
                elif r < -0.7:
                    insights.append(
                        f"🔗 Strong NEGATIVE correlation: "
                        f"{corr.columns[i]} ↔ {corr.columns[j]} (r={r:.2f})")

        self._clear_plot_area()
        f = tk.Frame(self.eda_plot_area, bg=PANEL)
        f.pack(fill="both", expand=True, padx=10, pady=10)
        tk.Label(f, text="🔍 Auto-Generated Insights",
                 bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))
        txt = scrolledtext.ScrolledText(f, bg=CARD, fg=TEXT,
                                         font=("Segoe UI", 11),
                                         relief="flat", bd=4, wrap="word")
        txt.pack(fill="both", expand=True)
        txt.insert("1.0",
            "\n\n".join(insights) if insights
            else "✅ No significant anomalies detected. Data appears stable.")
        txt.config(state="disabled")

    # ══════════════════════════════════════════════════════════
    # TAB 3 — STRESS TESTING
    # ══════════════════════════════════════════════════════════
    def _build_stress_tab(self):
        p    = self.tab_stress
        left = tk.Frame(p, bg=PANEL, width=320)
        left.pack(side="left", fill="y", padx=(10, 4), pady=10)
        left.pack_propagate(False)
        right = tk.Frame(p, bg=PANEL)
        right.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=10)

        section_label(left, "🔥 Stress Testing Controls")
        tk.Label(left, text="Stress Mode:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.stress_mode = tk.StringVar(value="single")
        for val, lbl in [("single","Single Variable"),
                          ("multiple","Multiple Variables"),
                          ("all","All Variables")]:
            tk.Radiobutton(left, text=lbl, variable=self.stress_mode,
                           value=val, bg=PANEL, fg=TEXT,
                           selectcolor=ENTRY_BG, font=("Segoe UI", 9),
                           activebackground=PANEL,
                           command=self._refresh_stress_ui).pack(
                           anchor="w", padx=10)

        self.stress_single_frame = tk.Frame(left, bg=PANEL)
        self.stress_single_frame.pack(fill="x", pady=4)
        tk.Label(self.stress_single_frame, text="Variable:",
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)).pack(anchor="w")
        self.var_stress_col   = tk.StringVar()
        self.combo_stress_col = ttk.Combobox(
            self.stress_single_frame, textvariable=self.var_stress_col,
            state="readonly", font=("Segoe UI", 9))
        self.combo_stress_col.pack(fill="x", pady=2)
        tk.Label(self.stress_single_frame,
                 text="Change % (e.g. +20 or -15):",
                 bg=PANEL, fg=SUBTEXT,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        self.ent_stress_pct = tk.Entry(
            self.stress_single_frame, bg=ENTRY_BG, fg=ENTRY_FG,
            insertbackground=TEXT, font=("Segoe UI", 10), relief="flat", bd=4)
        self.ent_stress_pct.insert(0, "20")
        self.ent_stress_pct.pack(fill="x", pady=2)

        self.stress_multi_frame = tk.Frame(left, bg=PANEL)
        tk.Label(self.stress_multi_frame,
                 text="Variables & Changes (one per line)\nFormat: VarName,pct",
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)).pack(anchor="w")
        self.txt_multi_stress = tk.Text(
            self.stress_multi_frame, height=5, bg=ENTRY_BG, fg=ENTRY_FG,
            insertbackground=TEXT, font=("Courier", 9), relief="flat", bd=4)
        self.txt_multi_stress.insert("1.0", "Revenue,20\nDefects,15")
        self.txt_multi_stress.pack(fill="x", pady=2)

        self.stress_all_frame = tk.Frame(left, bg=PANEL)
        tk.Label(self.stress_all_frame,
                 text="Apply same % to ALL variables:",
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)).pack(anchor="w")
        self.ent_all_pct = tk.Entry(
            self.stress_all_frame, bg=ENTRY_BG, fg=ENTRY_FG,
            insertbackground=TEXT, font=("Segoe UI", 10), relief="flat", bd=4)
        self.ent_all_pct.insert(0, "25")
        self.ent_all_pct.pack(fill="x", pady=2)

        tk.Label(left, text="VaR Confidence Level:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        self.var_conf = tk.StringVar(value="95")
        cf = tk.Frame(left, bg=PANEL)
        cf.pack(anchor="w")
        for v in ["90", "95", "99"]:
            tk.Radiobutton(cf, text=f"{v}%", variable=self.var_conf,
                           value=v, bg=PANEL, fg=TEXT, selectcolor=ENTRY_BG,
                           font=("Segoe UI", 9),
                           activebackground=PANEL).pack(side="left", padx=6)

        styled_btn(left, "▶  Run Stress Test",
                   self._run_stress_test,
                   color=DANGER, width=28).pack(pady=12, fill="x")

        section_label(right, "📊 Stress Test Results")
        self.txt_stress_result = scrolledtext.ScrolledText(
            right, height=10, bg=CARD, fg=TEXT,
            font=("Courier", 9), relief="flat", bd=4)
        self.txt_stress_result.pack(fill="x", pady=(0, 6))
        self.stress_plot_area = tk.Frame(right, bg=PANEL)
        self.stress_plot_area.pack(fill="both", expand=True)

    def _refresh_stress_ui(self):
        self.stress_single_frame.pack_forget()
        self.stress_multi_frame.pack_forget()
        self.stress_all_frame.pack_forget()
        m = self.stress_mode.get()
        if m == "single":
            self.stress_single_frame.pack(fill="x", pady=4)
        elif m == "multiple":
            self.stress_multi_frame.pack(fill="x", pady=4)
        else:
            self.stress_all_frame.pack(fill="x", pady=4)

    def _run_stress_test(self):
        if not self._check_data():
            return
        df       = self.df_clean.copy()
        corr     = self.corr_matrix
        mode     = self.stress_mode.get()
        conf     = int(self.var_conf.get())
        stresses = {}

        try:
            if mode == "single":
                col = self.var_stress_col.get() or self.num_cols[0]
                stresses[col] = float(self.ent_stress_pct.get())
            elif mode == "multiple":
                for line in self.txt_multi_stress.get("1.0","end").strip().split("\n"):
                    if "," in line:
                        c, v = line.split(",", 1)
                        stresses[c.strip()] = float(v.strip())
            else:
                pct = float(self.ent_all_pct.get())
                for c in self.num_cols:
                    stresses[c] = pct
        except Exception as e:
            messagebox.showerror("Input Error", str(e))
            return

        df_stressed  = df.copy()
        already_done = set(stresses.keys())

        for col, pct in stresses.items():
            if col not in self.num_cols:
                continue
            delta = df[col].mean() * (pct / 100)
            df_stressed[col] = df[col] + delta
            for other in self.num_cols:
                if other in already_done:
                    continue
                r = corr.loc[col, other]
                if abs(r) > 0.3:
                    s_col = df[col].std()
                    s_oth = df[other].std()
                    if s_col > 0:
                        df_stressed[other] += r * (s_oth / s_col) * delta

        alpha   = 1 - conf / 100
        results = []
        for col in self.num_cols:
            orig = df[col].values
            strd = df_stressed[col].values
            vo   = np.percentile(orig, alpha * 100)
            vs   = np.percentile(strd, alpha * 100)
            cvo  = orig[orig <= vo].mean() if len(orig[orig <= vo]) else vo
            cvs  = strd[strd <= vs].mean() if len(strd[strd <= vs]) else vs
            results.append({
                "Variable":              col,
                "Orig Mean":             orig.mean(),
                "Stressed Mean":         strd.mean(),
                "Δ Mean":                strd.mean() - orig.mean(),
                f"VaR{conf}% Orig":      vo,
                f"VaR{conf}% Stressed":  vs,
                f"CVaR{conf}% Stressed": cvs,
            })
        self.stress_results = pd.DataFrame(results)
        self.df_stressed    = df_stressed

        self.txt_stress_result.config(state="normal")
        self.txt_stress_result.delete("1.0","end")
        self.txt_stress_result.insert("1.0",
            f"STRESS TEST RESULTS  |  Mode: {mode.upper()}  |  "
            f"Confidence: {conf}%\n{'═'*70}\n\nApplied Stresses:\n")
        for c, v in stresses.items():
            self.txt_stress_result.insert("end", f"  {c}: {v:+.1f}%\n")
        self.txt_stress_result.insert("end", f"\n{'─'*95}\n")
        self.txt_stress_result.insert("end",
            f"{'Variable':<22} {'Orig Mean':>11} {'Stressed':>11} "
            f"{'Δ Mean':>10} {'VaR Orig':>11} "
            f"{'VaR Str':>11} {'CVaR Str':>11}\n" + "─"*95 + "\n")
        for _, row in self.stress_results.iterrows():
            self.txt_stress_result.insert("end",
                f"{row['Variable']:<22} {row['Orig Mean']:>11.3f} "
                f"{row['Stressed Mean']:>11.3f} {row['Δ Mean']:>+10.3f} "
                f"{row[f'VaR{conf}% Orig']:>11.3f} "
                f"{row[f'VaR{conf}% Stressed']:>11.3f} "
                f"{row[f'CVaR{conf}% Stressed']:>11.3f}\n")
        self.txt_stress_result.config(state="disabled")

        for w in self.stress_plot_area.winfo_children():
            w.destroy()
        n   = len(self.num_cols)
        fig, axes = plt.subplots(1, min(n, 5), figsize=(14, 4), facecolor=BG)
        if n == 1:
            axes = [axes]
        fig.suptitle(f"Before vs After Stress  |  {conf}% VaR",
                     color=TEXT, fontsize=12, fontweight="bold")
        for col, ax in zip(self.num_cols[:5], axes):
            ax.set_facecolor(CARD)
            o = df[col].values
            s = df_stressed[col].values
            ax.hist(o, bins=15, alpha=0.5, color=ACCENT,
                    label="Original", density=True)
            ax.hist(s, bins=15, alpha=0.5, color=DANGER,
                    label="Stressed", density=True)
            vo = np.percentile(o, alpha * 100)
            vs = np.percentile(s, alpha * 100)
            ax.axvline(vo, color=ACCENT, ls="--", lw=1.5,
                       label=f"VaR Orig {vo:.2f}")
            ax.axvline(vs, color=DANGER, ls="--", lw=1.5,
                       label=f"VaR Str {vs:.2f}")
            ax.set_title(col, color=TEXT, fontsize=9, fontweight="bold")
            ax.tick_params(colors=SUBTEXT, labelsize=7)
            ax.legend(fontsize=6, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)
            for sp in ax.spines.values():
                sp.set_edgecolor(BORDER)
        fig.tight_layout()
        self.figures["stress"] = fig
        cv = FigureCanvasTkAgg(fig, master=self.stress_plot_area)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

    # ══════════════════════════════════════════════════════════
    # TAB 4 — SCENARIO ANALYSIS
    # ══════════════════════════════════════════════════════════
    def _build_scenario_tab(self):
        p    = self.tab_scenario
        left = tk.Frame(p, bg=PANEL, width=310)
        left.pack(side="left", fill="y", padx=(10, 4), pady=10)
        left.pack_propagate(False)
        right = tk.Frame(p, bg=PANEL)
        right.pack(side="left", fill="both", expand=True, padx=(4, 10), pady=10)

        section_label(left, "🎲 Scenario Controls")
        tk.Label(left, text="Number of Simulations:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.var_sims = tk.StringVar(value="5000")
        ttk.Combobox(left, textvariable=self.var_sims,
                     values=["1000","2000","5000","10000"],
                     state="readonly", font=("Segoe UI", 9)).pack(fill="x", pady=2)

        tk.Label(left, text="Target Variable:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        self.var_target   = tk.StringVar()
        self.combo_target = ttk.Combobox(left, textvariable=self.var_target,
                                          state="readonly", font=("Segoe UI", 9))
        self.combo_target.pack(fill="x", pady=2)

        tk.Label(left, text="Scenario Name:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(8, 0))
        self.ent_scenario_name = tk.Entry(
            left, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=TEXT,
            font=("Segoe UI", 9), relief="flat", bd=4)
        self.ent_scenario_name.insert(0, "Baseline")
        self.ent_scenario_name.pack(fill="x", pady=2)

        tk.Label(left,
                 text="Variable Adjustments (optional)\nFormat: VarName,pct",
                 bg=PANEL, fg=SUBTEXT, font=("Segoe UI", 9)).pack(
                 anchor="w", pady=(8, 0))
        self.txt_scenario_adj = tk.Text(
            left, height=5, bg=ENTRY_BG, fg=ENTRY_FG,
            insertbackground=TEXT, font=("Courier", 9), relief="flat", bd=4)
        self.txt_scenario_adj.pack(fill="x", pady=2)

        styled_btn(left, "▶  Run Monte Carlo",
                   self._run_monte_carlo, color=ACCENT2, width=28).pack(pady=6, fill="x")
        styled_btn(left, "Add & Compare Scenario",
                   self._add_scenario, color=SUCCESS, width=28).pack(pady=4, fill="x")
        styled_btn(left, "Clear All Scenarios",
                   self._clear_scenarios, color="#555", width=28).pack(pady=4, fill="x")

        section_label(right, "📊 Monte Carlo Results")
        self.txt_scen_result = scrolledtext.ScrolledText(
            right, height=8, bg=CARD, fg=TEXT,
            font=("Courier", 9), relief="flat", bd=4)
        self.txt_scen_result.pack(fill="x", pady=(0, 6))
        self.scen_canvas_frame = tk.Frame(right, bg=PANEL)
        self.scen_canvas_frame.pack(fill="both", expand=True)
        self.scenarios = {}

    def _run_monte_carlo(self):
        if not self._check_data():
            return
        df     = self.df_clean
        n      = int(self.var_sims.get())
        target = self.var_target.get() or self.num_cols[-1]
        adj    = {}
        for line in self.txt_scenario_adj.get("1.0","end").strip().split("\n"):
            if "," in line:
                c, v = line.split(",", 1)
                col_name = c.strip()
                if col_name not in self.num_cols:
                    messagebox.showerror("Error", f"Column '{col_name}' not found")
                    return

                adj[col_name] = float(v.strip()) / 100

        sim = {}
        for col in self.num_cols:
            mu_c = df[col].mean() * (1 + adj.get(col, 0))
            si_c = df[col].std()
            sim[col] = np.random.normal(mu_c, si_c, n)

        try:
            L = np.linalg.cholesky(
                self.corr_matrix.values + np.eye(len(self.num_cols)) * 1e-6)
            z = np.random.standard_normal((n, len(self.num_cols))) @ L.T
            for i, col in enumerate(self.num_cols):
                mu_c = df[col].mean() * (1 + adj.get(col, 0))
                si_c = df[col].std()
                sim[col] = stats.norm.ppf(stats.norm.cdf(z[:, i]), mu_c, si_c)
        except np.linalg.LinAlgError:
            pass

        samp   = sim[target]
        mean_s = samp.mean(); std_s = samp.std()
        v95    = np.percentile(samp, 5)
        v99    = np.percentile(samp, 1)
        cv95   = samp[samp <= v95].mean() if len(samp[samp <= v95]) else v95
        cv99   = samp[samp <= v99].mean() if len(samp[samp <= v99]) else v99
        p_bl   = (samp < df[target].mean() * 0.9).mean() * 100

        name = self.ent_scenario_name.get() or "Scenario"
        self.scenarios[name] = dict(
            target=target, n=n, samples=samp,
            mean=mean_s, std=std_s,
            var95=v95, var99=v99, cvar95=cv95, cvar99=cv99,
            p_below=p_bl, adjustments=adj.copy())

        self.txt_scen_result.config(state="normal")
        self.txt_scen_result.delete("1.0","end")
        self.txt_scen_result.insert("1.0",
            f"MONTE CARLO — '{name}'  |  N={n:,}\n{'═'*50}\n\n"
            f"Target Variable : {target}\n"
            f"Mean            : {mean_s:.4f}\n"
            f"Std Deviation   : {std_s:.4f}\n"
            f"VaR (95%)       : {v95:.4f}\n"
            f"VaR (99%)       : {v99:.4f}\n"
            f"CVaR (95%)      : {cv95:.4f}\n"
            f"CVaR (99%)      : {cv99:.4f}\n"
            f"P(below 90% baseline): {p_bl:.2f}%\n")
        if adj:
            self.txt_scen_result.insert("end", "\nAdjustments:\n")
            for c, v in adj.items():
                self.txt_scen_result.insert("end", f"  {c}: {v*100:+.1f}%\n")
        self.txt_scen_result.config(state="disabled")

        self._plot_mc(name, samp, target, v95, v99, cv95)

    def _plot_mc(self, name, samp, target, v95, v99, cv95):
        for w in self.scen_canvas_frame.winfo_children():
            w.destroy()
        fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), facecolor=BG)
        fig.suptitle(f"Monte Carlo — {name}  |  Target: {target}",
                     color=TEXT, fontsize=12, fontweight="bold")

        for ax in axes:
            ax.set_facecolor(CARD)
            for sp in ax.spines.values():
                sp.set_edgecolor(BORDER)

        axes[0].hist(samp, bins=60, color=ACCENT, alpha=0.75, density=True)
        axes[0].axvline(v95,  color=WARNING, lw=2, ls="--", label=f"VaR 95%: {v95:.2f}")
        axes[0].axvline(v99,  color=DANGER,  lw=2, ls="--", label=f"VaR 99%: {v99:.2f}")
        axes[0].axvline(cv95, color=ACCENT2, lw=1.5, ls=":", label=f"CVaR 95%: {cv95:.2f}")
        xm = np.linspace(samp.min(), samp.max(), 200)
        axes[0].plot(xm, stats.norm.pdf(xm, samp.mean(), samp.std()),
                     color=SUCCESS, lw=2)
        axes[0].set_title("Simulated Distribution",
                          color=TEXT, fontsize=9, fontweight="bold")
        axes[0].tick_params(colors=SUBTEXT, labelsize=7)
        axes[0].legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)

        ss  = np.sort(samp)
        cdf = np.arange(1, len(ss)+1) / len(ss)
        axes[1].plot(ss, cdf, color=ACCENT, lw=2)
        axes[1].axhline(0.05, color=WARNING, ls="--", lw=1.5, label="5th pct")
        axes[1].axhline(0.01, color=DANGER,  ls="--", lw=1.5, label="1st pct")
        axes[1].set_title("CDF", color=TEXT, fontsize=9, fontweight="bold")
        axes[1].set_xlabel(target, color=SUBTEXT, fontsize=8)
        axes[1].set_ylabel("Probability", color=SUBTEXT, fontsize=8)
        axes[1].tick_params(colors=SUBTEXT, labelsize=7)
        axes[1].legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)

        rm = np.cumsum(samp) / np.arange(1, len(samp)+1)
        axes[2].plot(rm, color=ACCENT, lw=1.2, alpha=0.8)
        axes[2].axhline(samp.mean(), color=SUCCESS, lw=2, ls="--",
                        label=f"Final μ={samp.mean():.3f}")
        axes[2].set_title("Convergence of Mean",
                          color=TEXT, fontsize=9, fontweight="bold")
        axes[2].set_xlabel("Simulation #", color=SUBTEXT, fontsize=8)
        axes[2].tick_params(colors=SUBTEXT, labelsize=7)
        axes[2].legend(fontsize=7, facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT)

        fig.tight_layout()
        self.figures["monte_carlo"] = fig
        cv = FigureCanvasTkAgg(fig, master=self.scen_canvas_frame)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

    def _add_scenario(self):
        if len(self.scenarios) < 2:
            messagebox.showinfo("Need 2+",
                "Run at least 2 named scenarios, then click this.")
            return
        self._plot_scenario_comparison()

    def _plot_scenario_comparison(self):
        targets = {sc["target"] for sc in self.scenarios.values()}
        if len(targets) > 1:
            messagebox.showerror("Error", "All scenarios must use SAME target variable")
            return
        for w in self.scen_canvas_frame.winfo_children():
            w.destroy()
        clrs = [ACCENT, ACCENT2, SUCCESS, WARNING, DANGER]
        fig, axes = plt.subplots(1, 2, figsize=(13, 5), facecolor=BG)
        fig.suptitle("Scenario Comparison",
                     color=TEXT, fontsize=13, fontweight="bold")

        for ax in axes:
            ax.set_facecolor(CARD)
            for sp in ax.spines.values():
                sp.set_edgecolor(BORDER)

        for (nm, sc), cl in zip(self.scenarios.items(), clrs):
            axes[0].hist(sc["samples"], bins=50, alpha=0.5,
                         color=cl, density=True, label=nm)
        axes[0].set_title("Distribution Overlay",
                          color=TEXT, fontsize=10, fontweight="bold")
        axes[0].tick_params(colors=SUBTEXT, labelsize=7)
        axes[0].legend(facecolor=PANEL, edgecolor=BORDER,
                       labelcolor=TEXT, fontsize=8)

        names = list(self.scenarios.keys())
        xp    = np.arange(len(names))
        w     = 0.25
        axes[1].bar(xp-w, [self.scenarios[n]["mean"]  for n in names],
                    width=w, color=ACCENT,  label="Mean",    alpha=0.85)
        axes[1].bar(xp,   [self.scenarios[n]["var95"] for n in names],
                    width=w, color=WARNING, label="VaR 95%", alpha=0.85)
        axes[1].bar(xp+w, [self.scenarios[n]["var99"] for n in names],
                    width=w, color=DANGER,  label="VaR 99%", alpha=0.85)
        axes[1].set_xticks(xp)
        axes[1].set_xticklabels(names, color=TEXT, fontsize=8)
        axes[1].set_title("Mean & VaR Comparison",
                          color=TEXT, fontsize=10, fontweight="bold")
        axes[1].tick_params(colors=SUBTEXT, labelsize=7)
        axes[1].legend(facecolor=PANEL, edgecolor=BORDER,
                       labelcolor=TEXT, fontsize=8)

        fig.tight_layout()
        self.figures["scenario_compare"] = fig
        cv = FigureCanvasTkAgg(fig, master=self.scen_canvas_frame)
        cv.draw()
        cv.get_tk_widget().pack(fill="both", expand=True)

    def _clear_scenarios(self):
        self.scenarios.clear()
        self.txt_scen_result.config(state="normal")
        self.txt_scen_result.delete("1.0","end")
        self.txt_scen_result.config(state="disabled")
        for w in self.scen_canvas_frame.winfo_children():
            w.destroy()

    # ══════════════════════════════════════════════════════════
    # TAB 5 — EXPORT REPORT
    # ══════════════════════════════════════════════════════════
    def _build_report_tab(self):
        p = self.tab_report
        c = tk.Frame(p, bg=PANEL)
        c.pack(expand=True, fill="both", padx=40, pady=30)

        tk.Label(c, text="📄 Export Full Analysis Report",
                 bg=PANEL, fg=ACCENT,
                 font=("Segoe UI", 16, "bold")).pack(pady=(0, 8))
        tk.Label(c,
                 text="Generates a PDF with all statistics, charts, "
                      "stress test and scenario results.",
                 bg=PANEL, fg=SUBTEXT,
                 font=("Segoe UI", 10), wraplength=500).pack()

        tk.Label(c, text="Report Title:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(20, 2))
        self.ent_report_title = tk.Entry(
            c, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=TEXT,
            font=("Segoe UI", 11), relief="flat", bd=4, width=50)
        self.ent_report_title.insert(0,
            "Stress Testing & Scenario Analysis Report")
        self.ent_report_title.pack(fill="x", pady=2)

        tk.Label(c, text="Author / Student Name:", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.ent_author = tk.Entry(
            c, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=TEXT,
            font=("Segoe UI", 11), relief="flat", bd=4, width=50)
        self.ent_author.insert(0, "Student Name")
        self.ent_author.pack(fill="x", pady=2)

        styled_btn(c, "📥  Generate & Save PDF Report",
                   self._export_pdf, color=ACCENT, width=36).pack(pady=24)
        self.lbl_report_status = tk.Label(c, text="", bg=PANEL, fg=SUCCESS,
                                           font=("Segoe UI", 10))
        self.lbl_report_status.pack()

    def _export_pdf(self):
        if not self._check_data():
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="stress_testing_report.pdf")
        if not path:
            return
        try:
            self._generate_pdf(path)
            self.lbl_report_status.config(
                text=f"✔  Report saved: {os.path.basename(path)}")
            messagebox.showinfo("Success", f"PDF saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _generate_pdf(self, path):
        doc   = SimpleDocTemplate(path, pagesize=A4,
                                   rightMargin=40, leftMargin=40,
                                   topMargin=50, bottomMargin=40)
        story = []
        W     = A4[0] - 80

        def h1(t):
            return Paragraph(f"<b>{t}</b>",
                ParagraphStyle("h1", fontSize=16,
                    textColor=colors.HexColor("#4F8EF7"),
                    spaceAfter=8, spaceBefore=16,
                    fontName="Helvetica-Bold"))

        def h2(t):
            return Paragraph(f"<b>{t}</b>",
                ParagraphStyle("h2", fontSize=12,
                    textColor=colors.HexColor("#2E75B6"),
                    spaceAfter=4, spaceBefore=10,
                    fontName="Helvetica-Bold"))

        def body(t):
            return Paragraph(t,
                ParagraphStyle("body", fontSize=9,
                    textColor=colors.black, spaceAfter=4, leading=14))

        def fig_to_img(fig, h_ratio=0.45):
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100,
                        facecolor=fig.get_facecolor())
            buf.seek(0)
            return Image(buf, width=W, height=W * h_ratio)

        story += [
            Spacer(1, 60),
            Paragraph(self.ent_report_title.get(),
                ParagraphStyle("cov", fontSize=22,
                    textColor=colors.HexColor("#1F4E79"),
                    alignment=1, fontName="Helvetica-Bold", spaceAfter=10)),
            Paragraph("Manufacturing / Industrial Domain  |  Probability & Statistics",
                ParagraphStyle("sub", fontSize=11, textColor=colors.grey,
                    alignment=1, spaceAfter=6)),
            HRFlowable(width=W, thickness=2, color=colors.HexColor("#1F4E79")),
            Spacer(1, 10),
            Paragraph(f"Author: {self.ent_author.get()}",
                ParagraphStyle("auth", fontSize=10,
                    textColor=colors.grey, alignment=1)),
            PageBreak(),
        ]

        story.append(h1("1. Dataset Summary"))
        df = self.df_clean
        story.append(body(
            f"Rows: {len(df)}  |  Columns: {len(df.columns)}  |  "
            f"Numeric fields: {len(self.num_cols)}"))
        story.append(Spacer(1, 6))
        td = [["Field","Type","Mean","Std","Min","Max"]]
        for col in self.num_cols:
            td.append([col,"float",
                       f"{df[col].mean():.3f}", f"{df[col].std():.3f}",
                       f"{df[col].min():.3f}", f"{df[col].max():.3f}"])
        t = Table(td, colWidths=[W/6]*6)
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#1F4E79")),
            ("TEXTCOLOR",(0,0),(-1,0), colors.white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1), 8),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),
             [colors.white, colors.HexColor("#EBF3FB")]),
            ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ]))
        story += [t, PageBreak()]

        story.append(h1("2. EDA & Insights"))
        for key, title in [("heatmap","Correlation Heatmap"),
                            ("desc_stats","Descriptive Statistics"),
                            ("trends","Trend Analysis")]:
            if key in self.figures and self.figures[key]:
                story.append(h2(title))
                story.append(fig_to_img(self.figures[key]))
                story.append(Spacer(1, 10))
        story.append(PageBreak())

        story.append(h1("3. Stress Testing Results"))
        if hasattr(self, "stress_results"):
            sr   = self.stress_results
            cols = list(sr.columns)
            td2  = [cols] + [
                [f"{v:.3f}" if isinstance(v, float) else str(v) for v in row]
                for row in sr.values]
            cw = W / len(cols)
            t2 = Table(td2, colWidths=[cw]*len(cols))
            t2.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#C0392B")),
                ("TEXTCOLOR",(0,0),(-1,0), colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1), 7),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white, colors.HexColor("#FDECEA")]),
                ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ]))
            story.append(t2)
        if "stress" in self.figures:
            story += [Spacer(1, 10), fig_to_img(self.figures["stress"], 0.32)]
        story.append(PageBreak())

        story.append(h1("4. Monte Carlo Scenario Analysis"))
        if self.scenarios:
            td3 = [["Scenario","Target","N","Mean","Std",
                    "VaR 95%","VaR 99%","CVaR 95%"]]
            for nm, sc in self.scenarios.items():
                td3.append([nm, sc["target"], f"{sc['n']:,}",
                             f"{sc['mean']:.3f}", f"{sc['std']:.3f}",
                             f"{sc['var95']:.3f}", f"{sc['var99']:.3f}",
                             f"{sc['cvar95']:.3f}"])
            t3 = Table(td3, colWidths=[W/8]*8)
            t3.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(-1,0), colors.HexColor("#6A0DAD")),
                ("TEXTCOLOR",(0,0),(-1,0), colors.white),
                ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
                ("FONTSIZE",(0,0),(-1,-1), 7.5),
                ("ROWBACKGROUNDS",(0,1),(-1,-1),
                 [colors.white, colors.HexColor("#F3E8FF")]),
                ("GRID",(0,0),(-1,-1),0.5,colors.lightgrey),
                ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ]))
            story.append(t3)
        for key in ["monte_carlo","scenario_compare"]:
            if key in self.figures:
                story += [Spacer(1, 10), fig_to_img(self.figures[key], 0.38)]

        doc.build(story)


# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = StressTestApp()
    app.mainloop()
