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

# ------------------------------
# (YENİ → İKON + THREAD EKLEMESİ)
# ------------------------------
from PyQt5.QtGui import QIcon                  # ➕ Uygulama ikonu
from PyQt5.QtCore import QObject, pyqtSignal, QThread   # ➕ Thread sistemi

# ------------------------------------------------------------
# PDF çıktısı için ReportLab (opsiyonel)
# ------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False



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



# Worker Sınıfı
class SearchWorker(QObject):
    progress = pyqtSignal(dict)
    finished = pyqtSignal(int, int)

    def __init__(self, folder, query, case_sensitive, search_in_name, search_in_content):
        super().__init__()
        self.folder = folder
        self.query = query
        self.case_sensitive = case_sensitive
        self.search_in_name = search_in_name
        self.search_in_content = search_in_content

    def run(self):
        total_files = 0
        matched = 0

        for root_dir, dirs, files in os.walk(self.folder):

            # KLASÖR ARAMA
            if self.search_in_name:
                for dirname in dirs:
                    src = dirname if self.case_sensitive else dirname.lower()
                    q = self.query if self.case_sensitive else self.query.lower()
                    if q in src:
                        full_dir_path = os.path.join(root_dir, dirname)
                        try:
                            mtime = os.path.getmtime(full_dir_path)
                        except:
                            mtime = None
                        self.progress.emit({
                            "filename": dirname,
                            "file_type": "",
                            "folder_name": os.path.basename(root_dir),
                            "full_path": full_dir_path,
                            "size": None,
                            "mtime": mtime,
                            "is_dir": True,
                            "line": None,
                        })
                        matched += 1

            # DOSYA ARAMA
            for filename in files:
                total_files += 1
                full_path = os.path.join(root_dir, filename)
                ext = os.path.splitext(filename)[1].lower()
                mime, _ = mimetypes.guess_type(full_path)
                file_type = ext if ext else mime or ""

                # Boyut + tarih
                try:
                    size_bytes = os.path.getsize(full_path)
                except:
                    size_bytes = None

                try:
                    mtime = os.path.getmtime(full_path)
                except:
                    mtime = None

                # Dosya adı eşleşmesi
                name_match = False
                if self.search_in_name:
                    src = filename if self.case_sensitive else filename.lower()
                    q = self.query if self.case_sensitive else self.query.lower()
                    if q in src:
                        name_match = True

                # İçerik arama
                line_numbers = []
                if self.search_in_content:
                    line_numbers = search_in_file(full_path, self.query, self.case_sensitive)

                if line_numbers:
                    for ln in line_numbers:
                        self.progress.emit({
                            "filename": filename,
                            "file_type": file_type,
                            "folder_name": os.path.basename(root_dir),
                            "full_path": full_path,
                            "size": size_bytes,
                            "mtime": mtime,
                            "is_dir": False,
                            "line": ln,
                        })
                        matched += 1

                elif name_match:
                    self.progress.emit({
                        "filename": filename,
                        "file_type": file_type,
                        "folder_name": os.path.basename(root_dir),
                        "full_path": full_path,
                        "size": size_bytes,
                        "mtime": mtime,
                        "is_dir": False,
                        "line": None,
                    })
                    matched += 1

        self.finished.emit(total_files, matched)







# ------------------------------------------------------------
# ANA PENCERE
# ------------------------------------------------------------

class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NT Kelime Arama Aracı")
        self.resize(1200, 700)

        # ➕ UYGULAMA İKONU
        # icons/app_icon.ico dosyasını kullanır
        self.setWindowIcon(QIcon("icons/app_icon.ico"))


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
    # --------------------------------------------------------
    # ARAMA (ARTIK THREAD ÜZERİNDEN, DONMA YOK)
    # --------------------------------------------------------
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
            QMessageBox.warning(self, "Hata", "En az bir arama türü seçmelisiniz.")
            return

        # Tabloyu temizle
        self.table.setRowCount(0)
        self.status_label.setText("Aranıyor...")

        # THREAD
        self.thread = QThread()
        self.worker = SearchWorker(
            folder,
            query,
            case_sensitive,
            search_in_name,
            search_in_content
        )

        self.worker.moveToThread(self.thread)

        # Thread başlasın
        self.thread.started.connect(self.worker.run)

        # Worker UI’ya satır gönderiyor
        self.worker.progress.connect(self.add_row_from_thread)

        # İşlem bitti
        self.worker.finished.connect(self.search_finished)

        # Temizlik
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        # Başlat
        self.thread.start()

    # --------------------------------------------------------
    # THREAD → TABLOYA SATIR EKLER (YENİ)
    # --------------------------------------------------------
    def add_row_from_thread(self, data):
        self.add_row(
            filename=data["filename"],
            file_type=data["file_type"],
            folder_name=data["folder_name"],
            full_path=data["full_path"],
            size_bytes=data["size"],
            modified_ts=data["mtime"],
            is_dir=data["is_dir"],
            line_number=data["line"],
        )

    # --------------------------------------------------------
    # THREAD → ARAMA BİTİNCE ÇALIŞIR (YENİ)
    # --------------------------------------------------------
    def search_finished(self, total, matched):
        self.status_label.setText(
            f"Tarama tamamlandı. Toplam dosya: {total}, Eşleşen: {matched}"
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
        """Tablo sonuçlarını CSV veya PDF olarak dışa aktar (UTF-8 BOM + PDF destekli)."""

        row_count = self.table.rowCount()
        if row_count == 0:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak sonuç yok.")
            return

        fmt = self.export_format.currentText()
        if fmt not in ("CSV", "PDF"):
            return

        # Eğer PDF seçili ve ReportLab yoksa kibarca uyar ve çık
        if fmt == "PDF" and not HAS_REPORTLAB:
            QMessageBox.information(
                self,
                "Bilgi",
                "PDF çıktısı için 'reportlab' kütüphanesi gerekli.\n"
                "Önce şu komutla kurabilirsiniz:\n\n"
                "python -m pip install reportlab\n\n"
                "Şimdilik CSV formatını kullanabilirsiniz."
            )
            return

        # -----------------------------
        # Dosya adı seçtir
        # -----------------------------
        default_ext = "csv" if fmt == "CSV" else "pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Dışa Aktar",
            f"sonuclar.{default_ext}",
            "CSV Dosyası (*.csv);;PDF Dosyası (*.pdf)"
        )

        if not path:
            return

        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ============================================================
        # 1) CSV EXPORT (UTF-8 + BOM → Türkçe karakter garantili)
        # ============================================================
        if fmt == "CSV":

            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f, delimiter=";")

                    # Üst bilgiler
                    writer.writerow([f"Aranan Kelime: {query}"])
                    writer.writerow([f"Klasör: {folder}"])
                    writer.writerow([f"Tarih: {now_str}"])
                    writer.writerow([])

                    # Başlıklar
                    headers = [
                        "Dosya Adı", "Tür", "Tip", "Klasör",
                        "Yol", "Boyut", "Tarih", "Satır"
                    ]
                    writer.writerow(headers)

                    # Satırlar
                    for row in range(row_count):
                        def get(col):
                            item = self.table.item(row, col)
                            return item.text() if item else ""

                        # Yol tam halini tooltip'ten alıyoruz
                        path_item = self.table.item(row, 4)
                        full_path = path_item.toolTip() if path_item else get(4)

                        writer.writerow([
                            get(0),      # Dosya Adı
                            get(1),      # Tür
                            get(2),      # Tip
                            get(3),      # Klasör
                            full_path,   # Tam yol
                            get(5),      # Boyut
                            get(6),      # Tarih
                            get(7),      # Satır
                        ])

                QMessageBox.information(self, "Başarılı", f"CSV kaydedildi:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"CSV yazılırken hata oluştu:\n{e}")
            return

        # ============================================================
        # 2) PDF EXPORT (ReportLab)
        # ============================================================
        try:
            c = canvas.Canvas(path, pagesize=A4)
            w, h = A4
            y = h - 50

            # Üst bilgiler
            c.setFont("Helvetica-Bold", 12)
            c.drawString(40, y, f"Aranan Kelime: {query}")
            y -= 20
            c.drawString(40, y, f"Klasör: {folder}")
            y -= 20
            c.drawString(40, y, f"Tarih: {now_str}")
            y -= 30

            # Başlıklar
            headers = ["Dosya Adı", "Tür", "Tip", "Klasör", "Yol", "Boyut", "Tarih", "Satır"]
            c.setFont("Helvetica-Bold", 10)
            c.drawString(40, y, " | ".join(headers))
            y -= 20

            c.setFont("Helvetica", 9)

            # Satırlar
            for row in range(row_count):

                def get(col):
                    item = self.table.item(row, col)
                    return item.text() if item else ""

                path_item = self.table.item(row, 4)
                full_path = path_item.toolTip() if path_item else get(4)

                row_data = [
                    get(0), get(1), get(2), get(3),
                    full_path, get(5), get(6), get(7)
                ]

                c.drawString(40, y, " | ".join(row_data))
                y -= 15

                # Yeni sayfaya geçme
                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = h - 50

            c.save()
            QMessageBox.information(self, "Başarılı", f"PDF oluşturuldu:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", f"PDF oluşturulamadı:\n{e}")



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

