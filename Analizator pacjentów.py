#IMPORT BIBLIOTEK
import sys
import io
import pandas as pd
import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
from datetime import datetime

#NARZĘDZIA GUI:
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QTextEdit, QFrame,
    QSplitter, QFileDialog, QTableWidget, QTableWidgetItem, QLineEdit, QMessageBox, QAction, QComboBox, QListWidget,
    QListWidgetItem, QRadioButton, QButtonGroup, QCheckBox)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
#GŁÓWNE OKNO APLIKACJI
class AnalizatorCSV(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analizator danych pacjentów")
        self.setGeometry(100, 100, 1280, 760)
        self.df = None
        self.df_filtered = None
        self.last_fig = None
        self.canvas = None
        self.filters = []
        self.initUI()

    def initUI(self):
        #MENU
        menubar = self.menuBar()

        menu_plik = menubar.addMenu("Plik")
        action_wczytaj = QAction("Wczytaj CSV", self)
        action_wczytaj.triggered.connect(self.load_csv)
        menu_plik.addAction(action_wczytaj)
        menu_plik.addSeparator()
        action_exit = QAction("Wyjście", self)
        action_exit.triggered.connect(self.close)
        menu_plik.addAction(action_exit)

        menu_eksport = menubar.addMenu("Eksport")
        action_pdf = QAction("Eksportuj raport PDF", self)
        action_pdf.triggered.connect(self.export_pdf)
        menu_eksport.addAction(action_pdf)
        action_csv = QAction("Eksportuj dane CSV", self)
        action_csv.triggered.connect(self.export_csv)
        menu_eksport.addAction(action_csv)

        #CENTRALNY UKŁAD
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        splitter = QSplitter(Qt.Horizontal)

        #PANEL BOCZNY
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        self.btn_load = QPushButton("📂 Wczytaj CSV")
        self.btn_filter = QPushButton("⚙️ Filtry")
        self.btn_stats = QPushButton("📊 Statystyki")
        self.btn_plot = QPushButton("📈 Wizualizacja")
        self.btn_export_csv = QPushButton("💾 Eksport CSV")
        self.btn_export_pdf = QPushButton("🧾 Eksport PDF")

        for b in [self.btn_load, self.btn_filter, self.btn_stats, self.btn_plot, self.btn_export_csv,
                  self.btn_export_pdf]:
            b.setMinimumHeight(40)
            panel_layout.addWidget(b)
        panel_layout.addStretch()

        splitter.addWidget(panel)

        #ZAKŁADKI
        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)

        #PODGLĄD DANYCH
        self.tab_data = QWidget()
        vbox_data = QVBoxLayout(self.tab_data)
        self.table = QTableWidget()
        vbox_data.addWidget(self.table)
        self.tabs.addTab(self.tab_data, "Podgląd danych")

        #FILTRY
        self.tab_filter = QWidget()
        vbox_filter = QVBoxLayout(self.tab_filter)

        vbox_filter.addWidget(QLabel("Wybierz kolumnę:"))
        self.combo_col = QComboBox()
        vbox_filter.addWidget(self.combo_col)

        vbox_filter.addWidget(QLabel("Wybierz operator:"))
        self.combo_op = QComboBox()
        self.combo_op.addItems(["=", ">", "<", ">=", "<=", "zawiera", "nie zawiera"])
        vbox_filter.addWidget(self.combo_op)

        vbox_filter.addWidget(QLabel("Wprowadź wartość (np. 50, male, 2024-01-01):"))
        self.input_value = QLineEdit()
        vbox_filter.addWidget(self.input_value)

        self.btn_add_condition = QPushButton("Dodaj warunek")
        vbox_filter.addWidget(self.btn_add_condition)

        vbox_filter.addWidget(QLabel("Aktywne warunki:"))
        self.list_filters = QListWidget()
        vbox_filter.addWidget(self.list_filters)

        hbox_logic = QHBoxLayout()
        hbox_logic.addWidget(QLabel("Łącz warunki za pomocą:"))
        self.radio_and = QRadioButton("AND")
        self.radio_or = QRadioButton("OR")
        self.radio_and.setChecked(True)
        self.logic_group = QButtonGroup(self)
        self.logic_group.addButton(self.radio_and)
        self.logic_group.addButton(self.radio_or)
        hbox_logic.addWidget(self.radio_and)
        hbox_logic.addWidget(self.radio_or)
        vbox_filter.addLayout(hbox_logic)

        self.btn_apply_filters = QPushButton("Zastosuj filtry")
        self.btn_clear_filters = QPushButton("Wyczyść filtry")
        hbox_buttons = QHBoxLayout()
        hbox_buttons.addWidget(self.btn_apply_filters)
        hbox_buttons.addWidget(self.btn_clear_filters)
        vbox_filter.addLayout(hbox_buttons)
        vbox_filter.addStretch()
        self.tabs.addTab(self.tab_filter, "Filtry")

        #STATYSTYKI
        self.tab_stats = QWidget()
        vbox_stats = QVBoxLayout(self.tab_stats)

        #ŹRÓDŁO DANYCH
        src_box = QHBoxLayout()
        src_box.addWidget(QLabel("Zakres danych:"))
        self.radio_scope_filtered = QRadioButton("Przefiltrowane")
        self.radio_scope_all = QRadioButton("Całe")
        self.radio_scope_filtered.setChecked(True)
        self.scope_group = QButtonGroup(self)
        self.scope_group.addButton(self.radio_scope_filtered)
        self.scope_group.addButton(self.radio_scope_all)
        src_box.addWidget(self.radio_scope_filtered)
        src_box.addWidget(self.radio_scope_all)
        vbox_stats.addLayout(src_box)

        #KOLUMNY
        vbox_stats.addWidget(QLabel("Kolumny do analizy (zaznacz co chcesz):"))
        self.list_cols = QListWidget()
        self.list_cols.setSelectionMode(QListWidget.MultiSelection)
        vbox_stats.addWidget(self.list_cols)

        #GRUPOWANIE
        grp = QHBoxLayout()
        grp.addWidget(QLabel("Grupuj wg (opcjonalnie):"))
        self.combo_groupby = QComboBox()
        grp.addWidget(self.combo_groupby)
        vbox_stats.addLayout(grp)

        #METRYKI - CHECKBOXY
        vbox_stats.addWidget(QLabel("Metryki:"))
        self.chk_count = QCheckBox("Liczność (count)")
        self.chk_mean = QCheckBox("Średnia (mean)")
        self.chk_median = QCheckBox("Mediana (median)")
        self.chk_min = QCheckBox("Min")
        self.chk_max = QCheckBox("Max")
        self.chk_std = QCheckBox("Odchylenie std")

        for c in [self.chk_count, self.chk_mean, self.chk_median, self.chk_min, self.chk_max]:
            c.setChecked(True)
        metrics_row1 = QHBoxLayout()
        for c in [self.chk_count, self.chk_mean, self.chk_median, self.chk_min, self.chk_max, self.chk_std]:
            metrics_row1.addWidget(c)
        vbox_stats.addLayout(metrics_row1)

        #URUCHOMIENIE STATYSTYKI
        self.btn_compute_stats = QPushButton("Oblicz statystyki")
        vbox_stats.addWidget(self.btn_compute_stats)

        #WYNIKI STATYSTYK
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        vbox_stats.addWidget(self.stats_text)
        self.tabs.addTab(self.tab_stats, "Statystyki")

        #WIZUALIZACJA
        self.tab_plot = QWidget()
        vbox_plot = QVBoxLayout(self.tab_plot)

        # wybór kolumn do wizualizacji
        vbox_plot.addWidget(QLabel("Kolumna X:"))
        self.combo_plot_x = QComboBox()
        vbox_plot.addWidget(self.combo_plot_x)

        vbox_plot.addWidget(QLabel("Kolumna Y (opcjonalna dla wykresu rozrzutu):"))
        self.combo_plot_y = QComboBox()
        vbox_plot.addWidget(self.combo_plot_y)

        # wybór typu wykresu
        vbox_plot.addWidget(QLabel("Typ wykresu:"))
        self.combo_chart_type = QComboBox()
        self.combo_chart_type.addItems(["Auto", "Histogram", "Wykres rozrzutu"])
        vbox_plot.addWidget(self.combo_chart_type)

        # przycisk rysowania
        self.btn_draw_plot = QPushButton("Rysuj wykres")
        vbox_plot.addWidget(self.btn_draw_plot)

        # miejsce na wykres
        self.plot_label = QLabel("Brak danych do wizualizacji.")
        vbox_plot.addWidget(self.plot_label)

        self.tabs.addTab(self.tab_plot, "Wizualizacja")

        # Połączenie
        self.btn_draw_plot.clicked.connect(self.show_plot)
        self.btn_export_csv.clicked.connect(self.export_csv)
        self.btn_export_pdf.clicked.connect(self.export_pdf)

        #LOGI
        logs_frame = QFrame()
        logs_layout = QVBoxLayout(logs_frame)
        logs_layout.addWidget(QLabel("Logi:"))
        self.logs = QTextEdit()
        self.logs.setReadOnly(True)
        logs_layout.addWidget(self.logs)
        main_layout.addWidget(splitter)
        main_layout.addWidget(logs_frame)

        #POŁĄCZENIA
        self.btn_load.clicked.connect(self.load_csv)
        self.btn_filter.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.btn_stats.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.btn_plot.clicked.connect(self.show_plot)
        self.btn_add_condition.clicked.connect(self.add_condition)
        self.btn_clear_filters.clicked.connect(self.clear_filters)
        self.btn_apply_filters.clicked.connect(self.apply_filters)
        self.btn_compute_stats.clicked.connect(self.compute_selected_stats)

    #LOG
    def log(self, msg):
        self.logs.append(f"> {msg}")

    #WCZYTYWANIE CSV
    def load_csv(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Wybierz plik CSV", "", "CSV Files (*.csv)")
        if not filename:
            return
        try:
            try:
                self.df = pd.read_csv(filename, sep=None, engine="python", on_bad_lines="skip")
            except Exception:
                self.df = pd.read_csv(filename, sep=";", engine="python", on_bad_lines="skip")

            self.df_filtered = self.df.copy()
            self.update_table(self.df)

            #UZUPEŁNIANIE LISTY KOLUMN
            self.combo_col.clear()
            self.combo_col.addItems(self.df.columns)
            self.combo_plot_x.clear()
            self.combo_plot_y.clear()
            self.combo_plot_x.addItems(self.df.columns)
            self.combo_plot_y.addItems(["(brak)"] + list(self.df.columns))

            self.list_cols.clear()
            for col in self.df.columns:
                item = QListWidgetItem(col)
                item.setCheckState(Qt.Unchecked)
                self.list_cols.addItem(item)

            self.combo_groupby.clear()
            self.combo_groupby.addItem("(brak)")
            self.combo_groupby.addItems(self.df.columns)

            self.log(f"Wczytano plik: {filename} ({len(self.df)} wierszy, {len(self.df.columns)} kolumn)")
            self.tabs.setCurrentIndex(0)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać CSV:\n{e}")
            self.log(f"Błąd przy wczytywaniu CSV: {e}")

    #TABLICA DANYCH
    def update_table(self, df):
        self.table.clear()
        if df is None or df.empty:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        for i in range(len(df)):
            for j in range(len(df.columns)):
                self.table.setItem(i, j, QTableWidgetItem(str(df.iat[i, j])))
        self.table.resizeColumnsToContents()

    #FILTRY
    def add_condition(self):
        col = self.combo_col.currentText()
        op = self.combo_op.currentText()
        val = self.input_value.text().strip()
        if not col or not val:
            QMessageBox.information(self, "Brak danych", "Wybierz kolumnę i wprowadź wartość.")
            return
        condition = (col, op, val)
        self.filters.append(condition)
        self.list_filters.addItem(f"{col} {op} {val}")
        self.input_value.clear()
        self.log(f"Dodano warunek: {col} {op} {val}")

    def clear_filters(self):
        self.filters.clear()
        self.list_filters.clear()
        if self.df is not None:
            self.df_filtered = self.df.copy()
            self.update_table(self.df)
        self.log("Wyczyszczono wszystkie filtry.")

    def apply_filters(self):
        if self.df is None or not self.filters:
            QMessageBox.information(self, "Filtry", "Nie dodano żadnych warunków.")
            return

        logic = "and" if self.radio_and.isChecked() else "or"
        masks = []

        for col, op, val in self.filters:
            series_str = self.df[col].astype(str)

            # próba wykrycia dat
            try:
                series_date = pd.to_datetime(self.df[col], errors="coerce", dayfirst=True)
                val_date = pd.to_datetime(val, errors="coerce", dayfirst=True)
            except Exception:
                series_date = pd.Series([pd.NaT] * len(self.df))
                val_date = pd.NaT

            # liczby (po oczyszczeniu z przecinków/jednostek)
            series_num = (
                self.df[col]
                .astype(str)
                .str.replace(",", ".", regex=False)
                .str.extract(r"([\d\.]+)")[0]
            )
            series_num = pd.to_numeric(series_num, errors="coerce")

            mask = pd.Series([False] * len(self.df))

            try:
                if op == "=":
                    # porównanie tekstowe + numeryczne + daty
                    mask = series_str.str.lower() == val.lower()

                    try:
                        vnum = float(val.replace(",", "."))
                        mask |= series_num == vnum
                    except Exception:
                        pass

                    if not pd.isna(val_date):
                        mask |= series_date == val_date

                elif op in [">", "<", ">=", "<="]:
                    # jeśli kolumna wygląda na daty, użyj porównania dat
                    if not series_date.isna().all() and not pd.isna(val_date):
                        if op == ">":
                            mask = series_date > val_date
                        elif op == "<":
                            mask = series_date < val_date
                        elif op == ">=":
                            mask = series_date >= val_date
                        elif op == "<=":
                            mask = series_date <= val_date
                    else:
                        # porównanie numeryczne
                        vnum = float(val.replace(",", "."))
                        if op == ">":
                            mask = series_num > vnum
                        elif op == "<":
                            mask = series_num < vnum
                        elif op == ">=":
                            mask = series_num >= vnum
                        elif op == "<=":
                            mask = series_num <= vnum

                elif op == "zawiera":
                    mask = series_str.str.contains(val, case=False, na=False)
                elif op == "nie zawiera":
                    mask = ~series_str.str.contains(val, case=False, na=False)

            except Exception as e:
                self.log(f"Błąd przy filtrze {col} {op} {val}: {e}")

            masks.append(mask.fillna(False))

        # łączenie masek logicznie
        final_mask = masks[0]
        for m in masks[1:]:
            final_mask = (final_mask & m) if logic == "and" else (final_mask | m)

        self.df_filtered = self.df[final_mask]
        self.update_table(self.df_filtered)
        self.tabs.setCurrentIndex(0)
        self.log(f"Zastosowano {len(self.filters)} filtrów ({logic.upper()}); wyników: {len(self.df_filtered)}")

    def compute_selected_stats(self):
        if self.df is None:
            QMessageBox.warning(self, "Brak danych", "Najpierw wczytaj plik CSV.")
            return

        #ZAKRES
        df_src = self.df_filtered if self.radio_scope_filtered.isChecked() and self.df_filtered is not None else self.df

        #WYBRANE KOLUMNY
        selected_cols = []
        for i in range(self.list_cols.count()):
            item = self.list_cols.item(i)
            if item.checkState() == Qt.Checked:
                selected_cols.append(item.text())

        if not selected_cols:
            QMessageBox.information(self, "Statystyki", "Zaznacz przynajmniej jedną kolumnę.")
            return

        #GRUPOWANIE
        group_col = self.combo_groupby.currentText()
        use_groupby = group_col and group_col != "(brak)"

        #METRYKI
        want = {
            "count": self.chk_count.isChecked(),
            "mean": self.chk_mean.isChecked(),
            "median": self.chk_median.isChecked(),
            "min": self.chk_min.isChecked(),
            "max": self.chk_max.isChecked(),
            "std": self.chk_std.isChecked(),
            }

       #BUDOWA RAPORTU
        lines = []
        lines.append(f"Źródło: {'PRZEFILTROWANE' if df_src is self.df_filtered else 'CAŁE DANE'}")
        if use_groupby:
            lines.append(f"Grupowanie po: {group_col}")
        lines.append(f"Kolumny: {', '.join(selected_cols)}")
        lines.append("Metryki: " + ", ".join([k for k, v in want.items() if v]))
        lines.append("—"*60)

        #AGREGACJA KOLUMN NUMERYCZNYCH
        def numeric_series(s):
            return pd.to_numeric(s, errors="coerce")

        def summary_for_group(sub_df, group_name=None):

            header = f"[Grupa: {group_name}]" if group_name is not None else "[Całość]"
            out = [header]

            for col in selected_cols:
                s = sub_df[col]
                s_num = numeric_series(s)
                out.append(f"\nKolumna: {col}")

                if want["count"]:
                    out.append(f"  count: {s.size}")

                s_clean = s_num.dropna()
                if len(s_clean) == 0:
                    #brak danych liczbowych
                    if any([want["mean"], want["median"], want["min"], want["max"], want["std"]]):
                        out.append("  (brak danych liczbowych do metryk numerycznych)")
                else:
                    if want["mean"]:
                        out.append(f"  mean: {s_clean.mean():.6g}")
                    if want["median"]:
                        out.append(f"  median: {s_clean.median():.6g}")
                    if want["min"]:
                        out.append(f"  min: {s_clean.min():.6g}")
                    if want["max"]:
                        out.append(f"  max: {s_clean.max():.6g}")
                    if want["std"]:
                        out.append(f"  std: {s_clean.std():.6g}")

            return "\n".join(out)

        try:
            if use_groupby:
                for gval, sub in df_src.groupby(group_col, dropna=False):
                    lines.append(summary_for_group(sub, group_name=str(gval)))
            else:
                lines.append(summary_for_group(df_src))

            result = "\n".join(lines)
            self.stats_text.setPlainText(result)
            self.log("Obliczono statystyki na życzenie.")
            self.tabs.setCurrentIndex(2)
        except Exception as e:
            QMessageBox.warning(self, "Błąd statystyk", f"Nie udało się policzyć statystyk:\n{e}")
            self.log(f"Błąd statystyk: {e}")

    def _to_numeric_series(self, series):
        """Próba wyciągnięcia liczby z tekstu."""
        s = (
            series.astype(str)
            .str.replace(",", ".", regex=False)
            .str.extract(r"([-+]?\d*\.?\d+)")[0]
        )
        return pd.to_numeric(s, errors="coerce")

    def _to_datetime_series(self, series):
        """Próba zamiany kolumny na daty (jeśli się uda)."""
        s = pd.to_datetime(series, errors="coerce", dayfirst=True)
        if s.notna().sum() > len(series) * 0.5:  # jeśli >50% da się sparsować jako daty
            return s
        return None

    def show_plot(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do wizualizacji.")
            return

        col_x = self.combo_plot_x.currentText()
        col_y = self.combo_plot_y.currentText()
        chart_type = self.combo_chart_type.currentText()

        if not col_x:
            QMessageBox.warning(self, "Brak kolumny", "Wybierz przynajmniej kolumnę X.")
            return

        df = self.df_filtered.copy()
        x_raw = df[col_x]
        y_raw = None if not col_y or col_y == "(brak)" else df[col_y]

        # wykrywanie typów danych
        x_date = self._to_datetime_series(x_raw)
        y_date = self._to_datetime_series(y_raw) if y_raw is not None else None

        x_num = self._to_numeric_series(x_raw)
        y_num = self._to_numeric_series(y_raw) if y_raw is not None else None

        #automatyczny wybór typu wykresu
        if chart_type == "Auto":
            if y_raw is None:
                chart_type = "Histogram"
            elif x_date is not None and y_num is not None:
                chart_type = "Liniowy (czasowy)"
            elif x_num.notna().sum() > 0 and y_num.notna().sum() > 0:
                chart_type = "Wykres rozrzutu"
            elif x_raw.nunique() < 30 and y_num.notna().sum() > 0:
                chart_type = "Boxplot"
            else:
                chart_type = "Histogram"

        #czyszczenie starego wykresu
        if self.canvas:
            self.canvas.setParent(None)

        fig, ax = plt.subplots(figsize=(8, 5))
        plt.style.use("seaborn-v0_8")

        try:
            if chart_type == "Histogram":
                x_clean = x_num.dropna()
                if x_clean.empty:
                    QMessageBox.warning(self, "Brak danych", f"Kolumna '{col_x}' nie zawiera danych liczbowych.")
                    return
                ax.hist(x_clean, bins=20, edgecolor="black", alpha=0.7)
                ax.set_title(f"Histogram kolumny: {col_x}")
                ax.set_xlabel(col_x)
                ax.set_ylabel("Liczba wystąpień")

            elif chart_type == "Wykres rozrzutu":
                mask = x_num.notna() & y_num.notna()
                x_clean, y_clean = x_num[mask], y_num[mask]
                if len(x_clean) < 3:
                    QMessageBox.warning(self, "Za mało danych", "Za mało punktów do wykresu rozrzutu.")
                    return
                ax.scatter(x_clean, y_clean, alpha=0.7, s=30, edgecolors="black", linewidths=0.3)
                ax.set_title(f"Wykres rozrzutu: {col_x} vs {col_y}")
                ax.set_xlabel(col_x)
                ax.set_ylabel(col_y)

            elif chart_type == "Liniowy (czasowy)":
                mask = x_date.notna() & y_num.notna()
                x_clean, y_clean = x_date[mask], y_num[mask]
                if len(x_clean) < 3:
                    QMessageBox.warning(self, "Za mało danych", "Za mało punktów do wykresu czasowego.")
                    return
                df_sorted = pd.DataFrame({"x": x_clean, "y": y_clean}).sort_values("x")
                ax.plot(df_sorted["x"], df_sorted["y"], marker="o", linestyle="-", alpha=0.8)
                ax.set_title(f"Wykres czasowy: {col_x} vs {col_y}")
                ax.set_xlabel(col_x)
                ax.set_ylabel(col_y)
                fig.autofmt_xdate(rotation=30)

            elif chart_type == "Boxplot":
                # jeśli X to kategorie (mało unikalnych), Y to liczby
                valid_mask = y_num.notna()
                df_valid = pd.DataFrame({"X": x_raw[valid_mask].astype(str), "Y": y_num[valid_mask]})
                if df_valid["X"].nunique() > 50:
                    QMessageBox.warning(self, "Za dużo kategorii", "Zbyt wiele kategorii do boxplota.")
                    return
                df_valid.boxplot(column="Y", by="X", grid=False, ax=ax, color=dict(boxes="blue"))
                ax.set_title(f"Boxplot: {col_y} wg {col_x}")
                ax.set_xlabel(col_x)
                ax.set_ylabel(col_y)
                plt.suptitle("")

            ax.grid(True, linestyle="--", alpha=0.6)

        except Exception as e:
            ax.clear()
            ax.text(0.5, 0.5, f"Błąd rysowania: {e}", ha="center", va="center", fontsize=12)
            self.log(f"Błąd wykresu: {e}")

        self.canvas = FigureCanvas(fig)
        layout = self.tab_plot.layout()

        keep = {self.combo_plot_x, self.combo_plot_y, self.combo_chart_type, self.btn_draw_plot}
        for i in reversed(range(layout.count())):
            w = layout.itemAt(i).widget()
            if w and w not in keep:
                w.setParent(None)

        layout.addWidget(self.canvas)
        self.canvas.draw()
        self.last_fig = fig
        self.tabs.setCurrentIndex(3)

        self.log(
            f"Wygenerowano wykres ({chart_type}) dla {col_x}" + (f" i {col_y}" if col_y and col_y != "(brak)" else ""))

    #EKSPORT CSV
    def export_csv(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do eksportu CSV!")
            return

        # domyślna nazwa pliku
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"dane_{timestamp}.csv"

        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz dane CSV",
            default_name,
            "CSV Files (*.csv)",
            options=options
        )

        if not filename:
            return

        if not filename.lower().endswith(".csv"):
            filename += ".csv"

        try:
            self.df_filtered.to_csv(filename, index=False, sep=";", encoding="utf-8-sig")
            self.log(f"Zapisano dane do pliku: {filename}")
            QMessageBox.information(self, "Eksport CSV", f"Pomyślnie zapisano dane do:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd eksportu", f"Nie udało się zapisać danych do CSV:\n{e}")
            self.log(f"Błąd eksportu CSV: {e}")

    # EKSPORT PDF
    def export_pdf(self):
        if self.df_filtered is None or self.df_filtered.empty:
            QMessageBox.warning(self, "Brak danych", "Brak danych do eksportu!")
            return

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            #Używamy czcionki systemowej Arial Unicode MS (Windows)
            font_path = r"C:\Windows\Fonts\arialuni.ttf"
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont("ArialUnicode", font_path))
                default_font = "ArialUnicode"
                self.log("Załadowano czcionkę: Arial Unicode MS")
            else:
                default_font = "Helvetica"
                self.log("Nie znaleziono Arial Unicode MS – używam Helvetica.")
        except Exception as e:
            QMessageBox.warning(
                self, "Brak biblioteki",
                "Do eksportu PDF potrzebny jest pakiet 'reportlab'.\n"
                "Zainstaluj:  pip install reportlab"
            )
            self.log(f"Brak reportlab: {e}")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"raport_{timestamp}.pdf"
        options = QFileDialog.Options()
        filename, _ = QFileDialog.getSaveFileName(
            self, "Zapisz raport PDF", default_name, "PDF Files (*.pdf)", options=options
        )
        if not filename:
            return
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        try:
            c = rl_canvas.Canvas(filename, pagesize=A4)
            width, height = A4

            #NAGŁÓWEK
            c.setFont(default_font, 16)
            c.drawString(50, height - 50, "Raport analizy danych CSV")
            c.setFont(default_font, 10)
            c.drawString(50, height - 70, "Wygenerowano przez Analizator CSV")

            #STATYSTYKI
            stats_text = self.stats_text.toPlainText()
            if not stats_text and self.df_filtered is not None:
                try:
                    stats_text = str(self.df_filtered.describe(include="all"))
                except Exception:
                    stats_text = "Brak statystyk (nie udało się wygenerować)."

            c.setFont(default_font, 11)
            text_obj = c.beginText(50, height - 110)
            for line in stats_text.splitlines():
                if text_obj.getY() < 120:
                    c.drawText(text_obj)
                    c.showPage()
                    c.setFont(default_font, 11)
                    text_obj = c.beginText(50, height - 50)
                #Kodowanie UTF-8 dla polskich znaków
                safe_line = line.encode('utf-8', errors='ignore').decode('utf-8')
                text_obj.textLine(safe_line)
            c.drawText(text_obj)

            #WYKRES
            if self.last_fig:
                buf = io.BytesIO()
                self.last_fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                img = ImageReader(buf)
                c.showPage()
                c.setFont(default_font, 14)
                c.drawString(50, height - 50, "Wykres")
                c.drawImage(img, 50, 150, width - 100, height - 250, preserveAspectRatio=True)
                buf.close()

            c.save()
            self.log(f"Zapisano raport: {filename}")
            QMessageBox.information(self, "Sukces", f"Raport zapisano jako:\n{filename}")

        except Exception as e:
            QMessageBox.warning(self, "Błąd PDF", f"Nie udało się zapisać raportu:\n{e}")
            self.log(f"Błąd PDF: {e}")

            #WYKRES
            if self.last_fig:
                buf = io.BytesIO()
                self.last_fig.savefig(buf, format="png", bbox_inches="tight")
                buf.seek(0)
                img = ImageReader(buf)
                c.showPage()
                c.setFont(default_font, 14)
                c.drawString(50, height - 50, "Wykres")
                c.drawImage(img, 50, 150, width - 100, height - 250, preserveAspectRatio=True)
                buf.close()

            c.showPage()
            c.save()
            self.log(f"Zapisano raport: {filename}")
            QMessageBox.information(self, "Sukces", f"Raport zapisano jako:\n{filename}")
        except Exception as e:
            QMessageBox.warning(self, "Błąd PDF", f"Nie udało się zapisać raportu:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AnalizatorCSV()
    window.show()
    sys.exit(app.exec_())

