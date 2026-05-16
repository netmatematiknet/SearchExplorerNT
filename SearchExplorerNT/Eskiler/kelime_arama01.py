import sys
import os
import mimetypes

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox,
    QPushButton, QFileDialog, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor


def human_size(num_bytes: int) -> str:
    """Byte değerini KB/MB olarak okunabilir hale getir."""
    if num_bytes is None:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def truncate_text(text: str, max_len: int = 40) -> str:
    """Tabloda çok uzun metni kısalt, tooltip'te tam halini göstereceğiz."""
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def search_in_file(path: str, query: str, case_sensitive: bool) -> tuple[int, list[int]]:
    """
    Dosya içindeki satırlarda query kaç kez geçiyor ve hangi satırlarda geçiyor?
    - case_sensitive False ise hem satırı hem query'yi lower() yaparız.
    """
    total_count = 0
    line_numbers: list[int] = []

    if not query:
        return 0, []

    # Binary / okunamaz dosyalarda hata olmaması için güvenli açma
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, start=1):
                src_line = line if case_sensitive else line.lower()
                q = query if case_sensitive else query.lower()
                if q in src_line:
                    # Aynı satırda birden fazla geçebilir
                    occurrences = src_line.count(q)
                    total_count += occurrences
                    line_numbers.append(idx)
    except Exception:
        # Okuyamadığımız dosyalar (pdf, exe vs.) için 0 sonucu döneriz
        return 0, []

    return total_count, line_numbers


class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NT Kelime Arama Aracı")
        self.resize(1100, 650)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)
        self.setCentralWidget(root)

        # -----------------------------
        # ÜST PANEL: Klasör + Arama Kutusu + Opsiyonlar
        # -----------------------------
        top_row = QHBoxLayout()
        root_layout.addLayout(top_row)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Klasör yolu seçin...")
        btn_browse = QPushButton("Klasör Seç")

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Aranacak kelime...")
        self.chk_case = QCheckBox("Büyük/küçük harfe duyarlı")
        self.chk_name = QCheckBox("Dosya adında ara")
        self.chk_content = QCheckBox("Dosya içinde ara")
        self.chk_name.setChecked(True)
        self.chk_content.setChecked(True)

        btn_search = QPushButton("Ara")

        top_row.addWidget(QLabel("Klasör:"))
        top_row.addWidget(self.folder_edit, 2)
        top_row.addWidget(btn_browse)
        top_row.addSpacing(10)
        top_row.addWidget(QLabel("Kelime:"))
        top_row.addWidget(self.query_edit, 1)
        top_row.addWidget(self.chk_case)
        top_row.addWidget(self.chk_name)
        top_row.addWidget(self.chk_content)
        top_row.addWidget(btn_search)

        # -----------------------------
        # SÜTUN GÖSTER/GİZLE PANELİ
        # -----------------------------
        column_panel = QHBoxLayout()
        root_layout.addLayout(column_panel)

        column_panel.addWidget(QLabel("Gösterilecek sütunlar:"))

        self.column_checkboxes = []
        self.column_defs = [
            ("Dosya Adı", True),
            ("Tür", True),
            ("Klasör", True),
            ("Yol", True),
            ("Boyut", True),
            ("Geçme Sayısı", True),
            ("Satırlar", True),
        ]

        for idx, (name, default_visible) in enumerate(self.column_defs):
            cb = QCheckBox(name)
            cb.setChecked(default_visible)
            cb.stateChanged.connect(self.update_column_visibility)
            self.column_checkboxes.append(cb)
            column_panel.addWidget(cb)

        column_panel.addStretch()

        # -----------------------------
        # TABLO
        # -----------------------------
        self.table = QTableWidget()
        root_layout.addWidget(self.table, 1)

        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Dosya Adı",
            "Tür",
            "Klasör",
            "Yol",
            "Boyut",
            "Geçme Sayısı",
            "Satırlar",
            "Aksiyonlar",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        # Yol ve dosya adı üzerinde tooltip için mouse ile daha rahat tıklama
        self.table.setMouseTracking(True)

        # -----------------------------
        # ALT PANEL: Durum mesajı
        # -----------------------------
        bottom_row = QHBoxLayout()
        root_layout.addLayout(bottom_row)
        self.status_label = QLabel("Hazır.")
        self.status_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        bottom_row.addWidget(self.status_label)

        # -----------------------------
        # SİNYAL BAĞLANTILARI
        # -----------------------------
        btn_browse.clicked.connect(self.on_browse)
        btn_search.clicked.connect(self.on_search)

    # =========================
    # UI YARDIMCI FONKSİYONLAR
    # =========================
    def on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            self.folder_edit.setText(folder)

    def update_column_visibility(self):
        # Son sütun (Aksiyonlar) sabit, ilk 7 sütun checkbox ile kontrol
        for i, cb in enumerate(self.column_checkboxes):
            self.table.setColumnHidden(i, not cb.isChecked())

    # =========================
    # ARAMA
    # =========================
    def on_search(self):
        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()
        case_sensitive = self.chk_case.isChecked()
        search_in_name = self.chk_name.isChecked()
        search_in_content = self.chk_content.isChecked()

        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Hata", "Lütfen geçerli bir klasör seçin.")
            return

        if not query:
            QMessageBox.warning(self, "Hata", "Lütfen aranacak kelimeyi girin.")
            return

        if not (search_in_name or search_in_content):
            QMessageBox.warning(self, "Hata", "En az bir arama türü seçmelisiniz (dosya adı / içerik).")
            return

        self.table.setRowCount(0)
        total_files = 0
        matched_files = 0

        self.status_label.setText("Aranıyor...")
        QApplication.processEvents()

        # Klasör içini dolaş
        for root_dir, dirs, files in os.walk(folder):
            for filename in files:
                total_files += 1
                full_path = os.path.join(root_dir, filename)
                rel_folder = os.path.basename(root_dir)

                # Dosya türü / uzantı
                ext = os.path.splitext(filename)[1].lower()
                mime, _ = mimetypes.guess_type(full_path)
                file_type = ext if ext else (mime or "")

                # Dosya boyutu
                try:
                    size_bytes = os.path.getsize(full_path)
                except OSError:
                    size_bytes = None

                # Dosya adında arama
                name_match = False
                if search_in_name:
                    src_name = filename if case_sensitive else filename.lower()
                    q = query if case_sensitive else query.lower()
                    if q in src_name:
                        name_match = True

                # Dosya içinde arama
                content_match = False
                match_count = 0
                line_numbers: list[int] = []
                if search_in_content:
                    match_count, line_numbers = search_in_file(full_path, query, case_sensitive)
                    content_match = match_count > 0

                # En az bir yerde eşleşme yoksa bu dosyayı listeleme
                if not (name_match or content_match):
                    continue

                matched_files += 1
                self.add_row(
                    filename=filename,
                    file_type=file_type,
                    folder_name=rel_folder,
                    full_path=full_path,
                    size_bytes=size_bytes,
                    match_count=match_count,
                    line_numbers=line_numbers,
                )

        self.status_label.setText(
            f"Tarama tamamlandı. Toplam dosya: {total_files}, Eşleşen dosya: {matched_files}"
        )

    # =========================
    # TABLOYA SATIR EKLEME
    # =========================
    def add_row(
        self,
        filename: str,
        file_type: str,
        folder_name: str,
        full_path: str,
        size_bytes: int | None,
        match_count: int,
        line_numbers: list[int],
    ):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Dosya Adı
        item_name = QTableWidgetItem(truncate_text(filename, 30))
        item_name.setToolTip(filename)
        self.table.setItem(row, 0, item_name)

        # Tür
        item_type = QTableWidgetItem(file_type)
        item_type.setToolTip(file_type)
        self.table.setItem(row, 1, item_type)

        # Klasör
        item_folder = QTableWidgetItem(folder_name)
        item_folder.setToolTip(folder_name)
        self.table.setItem(row, 2, item_folder)

        # Yol (kısaltılmış)
        short_path = truncate_text(full_path, 50)
        item_path = QTableWidgetItem(short_path)
        item_path.setToolTip(full_path)
        self.table.setItem(row, 3, item_path)

        # Boyut
        item_size = QTableWidgetItem(human_size(size_bytes) if size_bytes is not None else "")
        item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 4, item_size)

        # Geçme Sayısı
        item_count = QTableWidgetItem(str(match_count))
        item_count.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 5, item_count)

        # Satırlar
        if line_numbers:
            lines_str = ", ".join(str(n) for n in line_numbers[:20])
            if len(line_numbers) > 20:
                lines_str += f"... (+{len(line_numbers) - 20})"
            tooltip_lines = ", ".join(str(n) for n in line_numbers)
        else:
            lines_str = ""
            tooltip_lines = ""
        item_lines = QTableWidgetItem(lines_str)
        item_lines.setToolTip(tooltip_lines)
        self.table.setItem(row, 6, item_lines)

        # Aksiyonlar (satır içi butonlar)
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 0, 2, 0)
        actions_layout.setSpacing(4)

        btn_open_folder = QPushButton("Klasörü Aç")
        btn_open_folder.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open_file = QPushButton("Dosyayı Aç")
        btn_open_file.setCursor(QCursor(Qt.PointingHandCursor))
        btn_copy_path = QPushButton("Yolu Kopyala")
        btn_copy_path.setCursor(QCursor(Qt.PointingHandCursor))

        # Daha küçük buton stili
        for b in (btn_open_folder, btn_open_file, btn_copy_path):
            b.setStyleSheet("QPushButton { padding: 3px 16px; font-size: 12px; }")

        actions_layout.addWidget(btn_open_folder)
        actions_layout.addWidget(btn_open_file)
        actions_layout.addWidget(btn_copy_path)
        actions_layout.addStretch(1)

        # Butonların fonksiyonları
        btn_open_folder.clicked.connect(lambda _, p=full_path: self.open_folder(p))
        btn_open_file.clicked.connect(lambda _, p=full_path: self.open_file(p))
        btn_copy_path.clicked.connect(lambda _, p=full_path: self.copy_path(p))

        self.table.setCellWidget(row, 7, actions_widget)

    # =========================
    # AKSİYONLAR
    # =========================
    def open_folder(self, full_path: str):
        folder = os.path.dirname(full_path)
        try:
            if os.path.isdir(folder):
                os.startfile(folder)  # Windows
            else:
                QMessageBox.warning(self, "Hata", "Klasör bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Klasör açılamadı:\n{e}")

    def open_file(self, full_path: str):
        try:
            if os.path.isfile(full_path):
                os.startfile(full_path)
            else:
                QMessageBox.warning(self, "Hata", "Dosya bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı:\n{e}")

    def copy_path(self, full_path: str):
        cb = QApplication.clipboard()
        cb.setText(full_path)
        self.status_label.setText(f"Yol kopyalandı: {full_path}")


def main():
    app = QApplication(sys.argv)
    win = SearchWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
