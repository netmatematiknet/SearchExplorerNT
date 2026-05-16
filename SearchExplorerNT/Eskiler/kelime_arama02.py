import sys
import os
import mimetypes
import csv
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox,
    QPushButton, QFileDialog, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QFrame, QComboBox, QStyle, QLabel as QtLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor


# ------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------

def human_size(num_bytes: int | None) -> str:
    """Byte değerini KB/MB/GB olarak okunabilir hale getir."""
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


def search_in_file(path: str, query: str, case_sensitive: bool) -> list[int]:
    """
    Dosya içinde satır satır arama yap.
    Sonuç: query'nin geçtiği tüm satır numaralarının listesi.
    """
    line_numbers: list[int] = []

    if not query:
        return []

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, start=1):
                src_line = line if case_sensitive else line.lower()
                q = query if case_sensitive else query.lower()
                if q in src_line:
                    line_numbers.append(idx)
    except Exception:
        # PDF, EXE vb. okunamayan dosyalarda hata olmasın
        return []

    return line_numbers


# ------------------------------------------------------------
# ANA PENCERE
# ------------------------------------------------------------

class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NT Kelime Arama Aracı")
        self.resize(1200, 700)

        # Arama geçmişini kaydedeceğimiz dosya
        self.history_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "search_history.log"
        )

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)
        self.setCentralWidget(root)

        # ----------------------------------------------------
        # ÜST PANEL: Klasör + kelime + arama seçenekleri
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # SÜTUN GÖSTER/GİZLE PANELİ
        # ----------------------------------------------------
        column_panel = QHBoxLayout()
        root_layout.addLayout(column_panel)

        column_panel.addWidget(QLabel("Gösterilecek sütunlar:"))

        self.column_checkboxes = []
        # 0..7 indeksleri (Aksiyonlar sabit, gizlenmez)
        self.column_defs = [
            ("Dosya Adı", True),
            ("Tür", True),
            ("Tip", True),
            ("Klasör", True),
            ("Yol", True),
            ("Boyut", True),
            ("Tarih", True),
            ("Satır", True),
        ]

        for name, default_visible in self.column_defs:
            cb = QCheckBox(name)
            cb.setChecked(default_visible)
            cb.stateChanged.connect(self.update_column_visibility)
            self.column_checkboxes.append(cb)
            column_panel.addWidget(cb)

        column_panel.addStretch()

        # ----------------------------------------------------
        # TABLO
        # ----------------------------------------------------
        self.table = QTableWidget()
        root_layout.addWidget(self.table, 1)

        # Kolonlar:
        # 0: Dosya Adı (+ kopya butonu)
        # 1: Tür (.php, .txt vb.)
        # 2: Tip (Dosya / Klasör)
        # 3: Klasör (+ kopya butonu)
        # 4: Yol (kısaltılmış, tooltip full path)
        # 5: Boyut
        # 6: Tarih
        # 7: Satır (her eşleşme için ayrı satır)
        # 8: Aksiyonlar (Klasörü Aç / Dosyayı Aç)
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Dosya Adı",
            "Tür",
            "Tip",
            "Klasör",
            "Yol",
            "Boyut",
            "Tarih",
            "Satır",
            "Aksiyonlar",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)

        # Seçim ve görünüm ayarları
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setMouseTracking(True)

        # Sütun genişliklerini biraz ayarlayalım
        self.table.setColumnWidth(0, 240)  # Dosya adı
        self.table.setColumnWidth(3, 200)  # Klasör
        self.table.setColumnWidth(4, 280)  # Yol
        self.table.setColumnWidth(8, 230)  # Aksiyonlar

        # Başlangıçta checkbox'lara göre görünürlük
        self.update_column_visibility()

        # ----------------------------------------------------
        # ALT PANEL: Durum + Dışa Aktar
        # ----------------------------------------------------
        bottom_row = QHBoxLayout()
        root_layout.addLayout(bottom_row)

        self.status_label = QLabel("Hazır.")
        self.status_label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        bottom_row.addWidget(self.status_label, 1)

        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "PDF"])
        btn_export = QPushButton("Dışa Aktar")
        bottom_row.addWidget(self.export_format)
        bottom_row.addWidget(btn_export)

        # ----------------------------------------------------
        # Sinyaller
        # ----------------------------------------------------
        btn_browse.clicked.connect(self.on_browse)
        btn_search.clicked.connect(self.on_search)
        btn_export.clicked.connect(self.export_results)

    # --------------------------------------------------------
    # UI Yardımcı Fonksiyonlar
    # --------------------------------------------------------
    def on_browse(self):
        """Klasör seçme iletişim kutusu aç."""
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            self.folder_edit.setText(folder)

    def update_column_visibility(self):
        """Checkbox'lara göre ilk 8 sütunu göster/gizle."""
        for i, cb in enumerate(self.column_checkboxes):
            self.table.setColumnHidden(i, not cb.isChecked())

    # --------------------------------------------------------
    # ARAMA
    # --------------------------------------------------------
    def on_search(self):
        """Klasörde tarama yap ve tabloyu doldur."""
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
            QMessageBox.warning(
                self, "Hata",
                "En az bir arama türü seçmelisiniz (dosya adı / içerik)."
            )
            return

        self.table.setRowCount(0)
        total_files = 0
        matched_rows = 0

        self.status_label.setText("Aranıyor...")
        QApplication.processEvents()

        # Klasör içinde dolaş
        for root_dir, dirs, files in os.walk(folder):

            # --- KLASÖR İSİMLERİNDE ARAMA ---
            if search_in_name:
                for dirname in dirs:
                    full_dir_path = os.path.join(root_dir, dirname)
                    src_name = dirname if case_sensitive else dirname.lower()
                    q = query if case_sensitive else query.lower()

                    if q in src_name:
                        # Klasör için tek satır (içerik araması yok)
                        try:
                            mtime = os.path.getmtime(full_dir_path)
                        except OSError:
                            mtime = None

                        self.add_row(
                            filename=dirname,
                            file_type="",
                            folder_name=os.path.basename(root_dir) or "",
                            full_path=full_dir_path,
                            size_bytes=None,
                            modified_ts=mtime,
                            is_dir=True,
                            line_number=None,
                        )
                        matched_rows += 1

            # --- DOSYALARDA ARAMA ---
            for filename in files:
                total_files += 1
                full_path = os.path.join(root_dir, filename)
                rel_folder = os.path.basename(root_dir)

                # Dosya türü / uzantı
                ext = os.path.splitext(filename)[1].lower()
                mime, _ = mimetypes.guess_type(full_path)
                file_type = ext if ext else (mime or "")

                # Dosya boyutu ve tarih
                try:
                    size_bytes = os.path.getsize(full_path)
                except OSError:
                    size_bytes = None

                try:
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    mtime = None

                # Dosya adında arama
                name_match = False
                if search_in_name:
                    src_name = filename if case_sensitive else filename.lower()
                    q = query if case_sensitive else query.lower()
                    if q in src_name:
                        name_match = True

                # Dosya içinde arama (satır satır)
                line_numbers: list[int] = []
                if search_in_content:
                    line_numbers = search_in_file(full_path, query, case_sensitive)

                # İçerik eşleşmeleri varsa: her satır için ayrı satır
                if line_numbers:
                    for ln in line_numbers:
                        self.add_row(
                            filename=filename,
                            file_type=file_type,
                            folder_name=rel_folder,
                            full_path=full_path,
                            size_bytes=size_bytes,
                            modified_ts=mtime,
                            is_dir=False,
                            line_number=ln,
                        )
                        matched_rows += 1
                # Sadece isim eşleşmesi varsa: tek satır
                elif name_match:
                    self.add_row(
                        filename=filename,
                        file_type=file_type,
                        folder_name=rel_folder,
                        full_path=full_path,
                        size_bytes=size_bytes,
                        modified_ts=mtime,
                        is_dir=False,
                        line_number=None,
                    )
                    matched_rows += 1

        # Arama geçmişine kayıt
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.history_path, "a", encoding="utf-8") as f:
                f.write(f"{ts}\t{folder}\t{query}\n")
        except Exception:
            pass  # Geçmiş yazılamasa bile uygulama devam etsin

        self.status_label.setText(
            f"Tarama tamamlandı. Toplam dosya: {total_files}, "
            f"Eşleşen satır/öge: {matched_rows}"
        )

    # --------------------------------------------------------
    # TABLOYA SATIR EKLEME
    # --------------------------------------------------------
    def add_row(
        self,
        filename: str,
        file_type: str,
        folder_name: str,
        full_path: str,
        size_bytes: int | None,
        modified_ts: float | None,
        is_dir: bool,
        line_number: int | None,
    ):
        """
        Tabloya bir satır ekle.
        is_dir = True ise Tip 'Klasör', False ise 'Dosya'.
        line_number None ise (sadece isim eşleşmesi) Satır sütunu boş kalır.
        """
        row = self.table.rowCount()
        self.table.insertRow(row)

        # ---------- 0. Sütun: Dosya Adı + Kopya Butonu ----------
        # Asıl veri QTableWidgetItem'ta saklanıyor (export için),
        # görsel olarak hücrede küçük bir layout kullanıyoruz.
        item_name = QTableWidgetItem(filename)
        self.table.setItem(row, 0, item_name)

        name_widget = QWidget()
        name_layout = QHBoxLayout(name_widget)
        name_layout.setContentsMargins(2, 0, 2, 0)
        name_layout.setSpacing(4)

        lbl_name = QtLabel(truncate_text(filename, 30))
        lbl_name.setToolTip(filename)

        btn_copy_name = QPushButton()
        btn_copy_name.setToolTip("Dosya adını kopyala")
        btn_copy_name.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        btn_copy_name.setFixedWidth(24)
        btn_copy_name.setStyleSheet("QPushButton { padding: 0; }")
        btn_copy_name.setCursor(QCursor(Qt.PointingHandCursor))
        btn_copy_name.clicked.connect(
            lambda _, n=filename: self.copy_name_or_folder(n, is_folder=False)
        )

        name_layout.addWidget(lbl_name)
        name_layout.addWidget(btn_copy_name)
        name_layout.addStretch(1)

        self.table.setCellWidget(row, 0, name_widget)

        # ---------- 1. Sütun: Tür ----------
        item_type = QTableWidgetItem(file_type)
        item_type.setToolTip(file_type)
        self.table.setItem(row, 1, item_type)

        # ---------- 2. Sütun: Tip (Dosya / Klasör) ----------
        tip_str = "Klasör" if is_dir else "Dosya"
        item_tip = QTableWidgetItem(tip_str)
        self.table.setItem(row, 2, item_tip)

        # ---------- 3. Sütun: Klasör Adı + Kopya Butonu ----------
        item_folder = QTableWidgetItem(folder_name)
        self.table.setItem(row, 3, item_folder)

        folder_widget = QWidget()
        folder_layout = QHBoxLayout(folder_widget)
        folder_layout.setContentsMargins(2, 0, 2, 0)
        folder_layout.setSpacing(4)

        lbl_folder = QtLabel(truncate_text(folder_name, 30))
        lbl_folder.setToolTip(folder_name)

        btn_copy_folder = QPushButton()
        btn_copy_folder.setToolTip("Klasör adını kopyala")
        btn_copy_folder.setIcon(self.style().standardIcon(QStyle.SP_FileDialogNewFolder))
        btn_copy_folder.setFixedWidth(24)
        btn_copy_folder.setStyleSheet("QPushButton { padding: 0; }")
        btn_copy_folder.setCursor(QCursor(Qt.PointingHandCursor))
        btn_copy_folder.clicked.connect(
            lambda _, n=folder_name: self.copy_name_or_folder(n, is_folder=True)
        )

        folder_layout.addWidget(lbl_folder)
        folder_layout.addWidget(btn_copy_folder)
        folder_layout.addStretch(1)

        self.table.setCellWidget(row, 3, folder_widget)

        # ---------- 4. Sütun: Yol (kısaltılmış, tooltip'te tam) ----------
        short_path = truncate_text(full_path, 60)
        item_path = QTableWidgetItem(short_path)
        item_path.setToolTip(full_path)
        self.table.setItem(row, 4, item_path)

        # ---------- 5. Sütun: Boyut ----------
        item_size = QTableWidgetItem(human_size(size_bytes))
        item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 5, item_size)

        # ---------- 6. Sütun: Tarih ----------
        if modified_ts is not None:
            dt_str = datetime.datetime.fromtimestamp(modified_ts).strftime(
                "%Y-%m-%d %H:%M"
            )
        else:
            dt_str = ""
        item_date = QTableWidgetItem(dt_str)
        self.table.setItem(row, 6, item_date)

        # ---------- 7. Sütun: Satır ----------
        if line_number is not None:
            line_str = str(line_number)
        else:
            line_str = ""
        item_line = QTableWidgetItem(line_str)
        item_line.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.table.setItem(row, 7, item_line)

        # ---------- 8. Sütun: Aksiyonlar (Klasörü Aç / Dosyayı Aç) ----------
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(2, 0, 2, 0)
        actions_layout.setSpacing(4)

        btn_open_folder = QPushButton()
        btn_open_folder.setText("Klasörü Aç")
        btn_open_folder.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        btn_open_folder.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open_folder.setStyleSheet(
            "QPushButton { padding: 3px 6px; font-size: 10px; "
            "background-color: #e8f5e9; }"
        )

        btn_open_file = QPushButton()
        btn_open_file.setText("Dosyayı Aç")
        btn_open_file.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))
        btn_open_file.setCursor(QCursor(Qt.PointingHandCursor))
        btn_open_file.setStyleSheet(
            "QPushButton { padding: 3px 6px; font-size: 10px; "
            "background-color: #e3f2fd; }"
        )

        btn_open_folder.clicked.connect(
            lambda _, p=full_path: self.open_folder(p)
        )
        btn_open_file.clicked.connect(
            lambda _, p=full_path, d=is_dir: self.open_file(p, is_dir=d)
        )

        actions_layout.addWidget(btn_open_folder)
        if not is_dir:  # klasör için "dosyayı aç" mantıklı değil
            actions_layout.addWidget(btn_open_file)
        actions_layout.addStretch(1)

        self.table.setCellWidget(row, 8, actions_widget)

    # --------------------------------------------------------
    # AKSİYONLAR
    # --------------------------------------------------------
    def copy_name_or_folder(self, name: str, is_folder: bool):
        """Dosya veya klasör adını panoya kopyala."""
        if not name:
            return
        cb = QApplication.clipboard()
        cb.setText(name)
        tip = "Klasör adı" if is_folder else "Dosya adı"
        self.status_label.setText(f"{tip} kopyalandı: {name}")

    def open_folder(self, full_path: str):
        """Seçilen dosyanın bulunduğu klasörü aç."""
        folder = full_path if os.path.isdir(full_path) else os.path.dirname(full_path)
        try:
            if os.path.isdir(folder):
                os.startfile(folder)  # Windows
            else:
                QMessageBox.warning(self, "Hata", "Klasör bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Klasör açılamadı:\n{e}")

    def open_file(self, full_path: str, is_dir: bool):
        """Dosyayı varsayılan programla aç (klasörse yok say)."""
        if is_dir:
            return
        try:
            if os.path.isfile(full_path):
                os.startfile(full_path)
            else:
                QMessageBox.warning(self, "Hata", "Dosya bulunamadı.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Dosya açılamadı:\n{e}")

    # --------------------------------------------------------
    # DIŞA AKTAR (CSV / PDF)
    # --------------------------------------------------------
    def export_results(self):
        """Tablo sonuçlarını CSV veya PDF olarak dışa aktar."""
        row_count = self.table.rowCount()
        if row_count == 0:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak sonuç yok.")
            return

        fmt = self.export_format.currentText()
        if fmt not in ("CSV", "PDF"):
            return

        # Kullanıcıdan dosya adı iste
        default_ext = "csv" if fmt == "CSV" else "pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Dışa Aktar",
            f"sonuclar.{default_ext}",
            "CSV Dosyası (*.csv);;PDF Dosyası (*.pdf);;Tüm Dosyalar (*.*)",
        )
        if not path:
            return

        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if fmt == "CSV":
            try:
                with open(path, "w", encoding="utf-8", newline="") as f:
                    w = csv.writer(f, delimiter=";")

                    # Üst bilgi satırları
                    w.writerow([f"Aranan Kelime: {query}"])
                    w.writerow([f"Klasör: {folder}"])
                    w.writerow([f"Tarih: {now_str}"])
                    w.writerow([])

                    # Başlık satırı
                    w.writerow([
                        "Dosya Adı",
                        "Tür",
                        "Tip",
                        "Klasör",
                        "Yol",
                        "Boyut",
                        "Tarih",
                        "Satır",
                    ])

                    # Satırlar
                    for row in range(row_count):
                        def get(col):
                            item = self.table.item(row, col)
                            return item.text() if item is not None else ""

                        # Yol için tooltip'te full path var
                        path_item = self.table.item(row, 4)
                        full_path = (
                            path_item.toolTip()
                            if path_item is not None and path_item.toolTip()
                            else get(4)
                        )

                        w.writerow([
                            get(0),          # Dosya adı (tam)
                            get(1),          # Tür
                            get(2),          # Tip
                            get(3),          # Klasör adı
                            full_path,       # Tam yol
                            get(5),          # Boyut
                            get(6),          # Tarih
                            get(7),          # Satır
                        ])

                QMessageBox.information(self, "Bilgi", f"Sonuçlar CSV olarak kaydedildi:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"CSV yazılırken hata oluştu:\n{e}")

        else:  # PDF
            QMessageBox.information(
                self,
                "Bilgi",
                "PDF çıktısı için harici bir kütüphane (ör. reportlab) gerekir.\n"
                "Şimdilik CSV formatını kullanabilirsiniz."
            )


# ------------------------------------------------------------
# main
# ------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    win = SearchWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
