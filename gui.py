import os
import sys
import traceback
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QObject, QThread, Signal, Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from parser import parse_wb, build_result_columns
import regulations as rg
from regulations import GradeThreshold, Regulation

APP_TITLE = "Grade Report Generator"
GRADE_RULES_DIR = "grade_rules"


class SignalWriter:
    """Redirects writes (e.g. print()) into a Qt signal so log lines cross threads safely."""

    def __init__(self, signal: Signal):
        self.signal = signal

    def write(self, text):
        if text.strip():
            self.signal.emit(text)

    def flush(self):
        pass


class Worker(QObject):
    log = Signal(str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, in_file: str, reg_file: str, write_intermediate: bool = True):
        super().__init__()
        self.in_file = in_file
        self.reg_file = reg_file
        self.write_intermediate = write_intermediate

    def run(self):
        old_stdout = sys.stdout
        sys.stdout = SignalWriter(self.log)
        try:
            self.log.emit(f"Loading regulation: {self.reg_file}")
            reg = rg.Regulation.load(self.reg_file)

            self.log.emit(f"Parsing workbook: {self.in_file}")
            parsed_data = parse_wb(self.in_file, reg, write_intermediate=self.write_intermediate)

            df_result = pd.DataFrame(parsed_data)
            df_result.columns = build_result_columns(df_result.shape[1])
            self.log.emit(f"Done. Parsed {len(df_result)} row(s).")
            self.finished.emit(df_result)
        except Exception as exc:
            self.log.emit(f"Error: {exc}\n{traceback.format_exc()}")
            self.error.emit(str(exc))
        finally:
            sys.stdout = old_stdout


class GradeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(960, 680)

        self.last_result_df: pd.DataFrame | None = None
        self.last_input_file: str | None = None
        self.thread: QThread | None = None
        self.worker: Worker | None = None

        self._build_ui()
        self._refresh_registry_options()

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        title = QLabel(APP_TITLE)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        root.addWidget(title)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs)

        main_tab = QWidget()
        self.tabs.addTab(main_tab, "Home")
        rules_tab = QWidget()
        self.tabs.addTab(rules_tab, "Grading Rules")
        log_tab = QWidget()
        self.tabs.addTab(log_tab, "Log")

        self._build_main_tab(main_tab)
        self._build_rules_tab(rules_tab)
        self._build_log_tab(log_tab)

    def _build_main_tab(self, tab: QWidget):
        grid = QGridLayout(tab)

        grid.addWidget(QLabel("Input workbook (.xlsx)"), 0, 0)
        self.in_edit = QLineEdit()
        grid.addWidget(self.in_edit, 0, 1)
        in_browse = QPushButton("Browse...")
        in_browse.clicked.connect(self._pick_input)
        grid.addWidget(in_browse, 0, 2)

        grid.addWidget(QLabel("Grading regulation"), 1, 0)
        self.reg_combo = QComboBox()
        self.reg_combo.setEditable(True)
        grid.addWidget(self.reg_combo, 1, 1)
        reg_browse = QPushButton("Browse...")
        reg_browse.clicked.connect(self._pick_registry)
        grid.addWidget(reg_browse, 1, 2)

        self.intermediate_checkbox = QCheckBox("Save intermediate per-student files")
        self.intermediate_checkbox.setChecked(True)
        grid.addWidget(self.intermediate_checkbox, 2, 0, 1, 3)

        action_row = QHBoxLayout()
        self.run_btn = QPushButton("Process")
        self.run_btn.setMinimumHeight(36)
        run_font = QFont()
        run_font.setBold(True)
        run_font.setPointSize(11)
        self.run_btn.setFont(run_font)
        self.run_btn.clicked.connect(self._on_run)
        action_row.addWidget(self.run_btn)

        self.status_label = QLabel("")
        status_font = QFont()
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        action_row.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        action_row.addWidget(self.progress, stretch=1)

        grid.addLayout(action_row, 3, 0, 1, 3)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        grid.addWidget(self.table, 4, 0, 1, 3)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self.save_btn = QPushButton("Save As...")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save_as)
        save_row.addWidget(self.save_btn)
        grid.addLayout(save_row, 5, 0, 1, 3)

        grid.setColumnStretch(1, 1)
        grid.setRowStretch(4, 1)

    def _build_log_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)
        self.log_box = QPlainTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

    RULES_COLUMNS = ["Min GPA", "Letter", "Label"]

    def _build_rules_tab(self, tab: QWidget):
        layout = QVBoxLayout(tab)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Regulation name"))
        self.rule_name_edit = QLineEdit()
        name_row.addWidget(self.rule_name_edit, stretch=1)
        layout.addLayout(name_row)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(len(self.RULES_COLUMNS))
        self.rules_table.setHorizontalHeaderLabels(self.RULES_COLUMNS)
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.rules_table, stretch=1)

        row_btns = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self._rules_add_row)
        row_btns.addWidget(add_row_btn)
        remove_row_btn = QPushButton("Remove Row")
        remove_row_btn.clicked.connect(self._rules_remove_row)
        row_btns.addWidget(remove_row_btn)
        row_btns.addStretch(1)
        layout.addLayout(row_btns)

        action_btns = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._rules_new)
        action_btns.addWidget(new_btn)
        load_btn = QPushButton("Load...")
        load_btn.clicked.connect(self._rules_load)
        action_btns.addWidget(load_btn)
        action_btns.addStretch(1)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._rules_save)
        action_btns.addWidget(save_btn)
        layout.addLayout(action_btns)

        self._rules_new()

    def _rules_add_row(self, min_points: float = 0.0, letter: str = "", label: str = ""):
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        self.rules_table.setItem(row, 0, QTableWidgetItem(str(min_points)))
        self.rules_table.setItem(row, 1, QTableWidgetItem(letter))
        self.rules_table.setItem(row, 2, QTableWidgetItem(label))

    def _rules_remove_row(self):
        rows = sorted({idx.row() for idx in self.rules_table.selectedIndexes()}, reverse=True)
        if not rows:
            rows = [self.rules_table.rowCount() - 1] if self.rules_table.rowCount() else []
        for row in rows:
            self.rules_table.removeRow(row)

    def _populate_rules_table(self, reg: Regulation):
        self.rule_name_edit.setText(reg.name)
        self.rules_table.setRowCount(0)
        for threshold in reg.sorted_thresholds():
            self._rules_add_row(threshold.min_points, threshold.letter, threshold.label)

    def _rules_new(self):
        self._populate_rules_table(Regulation.default())

    def _rules_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load grading regulation", GRADE_RULES_DIR, "JSON files (*.json);;All files (*)"
        )
        if not path:
            return
        try:
            reg = Regulation.load(path)
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to load regulation:\n{exc}")
            return
        self._populate_rules_table(reg)

    def _rules_gather(self) -> Regulation:
        name = self.rule_name_edit.text().strip() or "Untitled Regulation"
        thresholds = []
        for row in range(self.rules_table.rowCount()):
            gpa_item = self.rules_table.item(row, 0)
            letter_item = self.rules_table.item(row, 1)
            label_item = self.rules_table.item(row, 2)

            gpa_text = gpa_item.text().strip() if gpa_item else ""
            letter = letter_item.text().strip() if letter_item else ""
            label = label_item.text().strip() if label_item else ""

            if not gpa_text and not letter and not label:
                continue
            if not gpa_text or not letter:
                raise ValueError(f"Row {row + 1}: Min GPA and Letter are required.")
            try:
                min_points = float(gpa_text)
            except ValueError:
                raise ValueError(f"Row {row + 1}: '{gpa_text}' is not a valid number.")

            thresholds.append(GradeThreshold(min_points=min_points, letter=letter, label=label))

        if not thresholds:
            raise ValueError("Add at least one grade threshold.")

        return Regulation(name=name, thresholds=thresholds)

    def _rules_save(self):
        try:
            reg = self._rules_gather()
        except ValueError as exc:
            QMessageBox.critical(self, APP_TITLE, str(exc))
            return

        default_name = self.rule_name_edit.text().strip() or "regulation"
        filename, ok = QInputDialog.getText(
            self, "Save grading regulation", "File name:", text=default_name
        )
        if not ok or not filename.strip():
            return
        filename = filename.strip()
        if not filename.lower().endswith(".json"):
            filename += ".json"

        rules_dir = Path(GRADE_RULES_DIR)
        rules_dir.mkdir(parents=True, exist_ok=True)
        path = rules_dir / filename

        if path.exists():
            reply = QMessageBox.question(
                self, APP_TITLE,
                f"'{filename}' already exists in {GRADE_RULES_DIR}. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        try:
            reg.save(str(path))
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to save regulation:\n{exc}")
            return

        QMessageBox.information(self, APP_TITLE, f"Saved regulation to {path}")
        self._refresh_registry_options()
        self.reg_combo.setCurrentText(str(path))

    # ---------- helpers ----------
    def _refresh_registry_options(self):
        rules_dir = Path(GRADE_RULES_DIR)
        options = sorted(str(p) for p in rules_dir.glob("*.json")) if rules_dir.is_dir() else []
        current = self.reg_combo.currentText()
        self.reg_combo.clear()
        self.reg_combo.addItems(options)
        if current:
            self.reg_combo.setCurrentText(current)
        elif options:
            self.reg_combo.setCurrentIndex(0)

    def _pick_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select input workbook", "", "Excel files (*.xlsx);;All files (*)"
        )
        if path:
            self.in_edit.setText(path)

    def _pick_registry(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select grading regulation (JSON)", "", "JSON files (*.json);;All files (*)"
        )
        if path:
            self.reg_combo.setEditText(path)
            self._refresh_registry_options()
            self.reg_combo.setEditText(path)

    def _log(self, message: str):
        self.log_box.appendPlainText(message.rstrip("\n"))

    def _populate_table(self, df: pd.DataFrame):
        columns = [str(c) for c in df.columns]
        self.table.clear()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(len(df))

        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, value in enumerate(row.tolist()):
                if isinstance(value, float):
                    text = "" if pd.isna(value) else f"{round(value, 2)}"
                elif isinstance(value, bool):
                    text = "Yes" if value else "No"
                else:
                    text = "" if value is None else str(value)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)

        self.table.resizeColumnsToContents()

    # ---------- run ----------
    def _on_run(self):
        in_file = self.in_edit.text().strip()
        reg_file = self.reg_combo.currentText().strip()

        if not in_file or not os.path.isfile(in_file):
            QMessageBox.critical(self, APP_TITLE, "Please choose a valid input workbook.")
            return
        if not reg_file or not os.path.isfile(reg_file):
            QMessageBox.critical(self, APP_TITLE, "Please choose a valid grading regulation file.")
            return

        self.last_input_file = in_file

        self.run_btn.setEnabled(False)
        self.run_btn.setText("Processing...")
        self.save_btn.setEnabled(False)
        self.status_label.setText("")
        self.progress.setRange(0, 0)  # indeterminate/busy

        self.thread = QThread()
        self.worker = Worker(in_file, reg_file, write_intermediate=self.intermediate_checkbox.isChecked())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self._log)
        self.worker.finished.connect(self._on_process_success)
        self.worker.error.connect(self._on_process_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.thread.finished.connect(self._cleanup_thread)

        self.thread.start()

    def _cleanup_thread(self):
        if self.thread is not None:
            self.thread.deleteLater()
        if self.worker is not None:
            self.worker.deleteLater()
        self.thread = None
        self.worker = None

    def _reset_run_controls(self):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.run_btn.setEnabled(True)
        self.run_btn.setText("Process")

    def _on_process_success(self, df: pd.DataFrame):
        self.last_result_df = df
        self._populate_table(df)
        self.save_btn.setEnabled(True)
        self.status_label.setText("✓ Done")
        self.status_label.setStyleSheet("color: #2fa84f;")
        self._reset_run_controls()

    def _on_process_error(self, error: str):
        self.status_label.setText("✗ Failed")
        self.status_label.setStyleSheet("color: #d9453d;")
        self._reset_run_controls()
        QMessageBox.critical(self, APP_TITLE, f"Processing failed:\n{error}")

    def _on_save_as(self):
        if self.last_result_df is None:
            QMessageBox.warning(self, APP_TITLE, "Nothing to save yet — run Process first.")
            return

        input_stem = Path(self.last_input_file).stem if self.last_input_file else "output"
        default_dir = Path("output") / input_stem
        default_dir.mkdir(parents=True, exist_ok=True)
        default_path = str(default_dir / f"{input_stem}.xlsx")

        path, _ = QFileDialog.getSaveFileName(
            self, "Save results as", default_path, "Excel files (*.xlsx)"
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"

        try:
            self.last_result_df.to_excel(path, index=False, header=True)
            self._log(f"Saved results to {path}")
            QMessageBox.information(self, APP_TITLE, f"Saved to {path}")
        except Exception as exc:
            QMessageBox.critical(self, APP_TITLE, f"Failed to save file:\n{exc}")


def _anchor_working_directory():
    """When frozen (PyInstaller), relative paths like grade_rules/ and intermediate/
    should live next to the executable, not whatever directory launched it."""
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)


ICON_PATH = Path("icons/app.png")


def main():
    _anchor_working_directory()
    app = QApplication(sys.argv)
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = GradeApp()
    if ICON_PATH.is_file():
        window.setWindowIcon(QIcon(str(ICON_PATH)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
