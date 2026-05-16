import sys
import os
import mimetypes
import csv
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QCheckBox, QPushButton, QFileDialog, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox,
    QFrame, QComboBox, QStyle, QLabel as QtLabel, QTabWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor, QIcon

from PyQt5.QtCore import QObject, pyqtSignal, QThread

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
    if num_bytes is None:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def truncate_text(text: str, max_len: int = 40) -> str:
    text = text or ""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def search_in_file(path: str, query: str, case_sensitive: bool) -> list[int]:
    line_numbers = []
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
        return []
    return line_numbers


# ------------------------------------------------------------
# Worker
# ------------------------------------------------------------

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

            # Klasör arama
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

            # Dosya arama
            for filename in files:
                total_files += 1
                full_path = os.path.join(root_dir, filename)
                ext = os.path.splitext(filename)[1].lower()
                mime, _ = mimetypes.guess_type(full_path)
                file_type = ext if ext else mime or ""

                try:
                    size_bytes = os.path.getsize(full_path)
                except:
                    size_bytes = None

                try:
                    mtime = os.path.getmtime(full_path)
                except:
                    mtime = None

                # Name match
                name_match = False
                if self.search_in_name:
                    src = filename if self.case_sensitive else filename.lower()
                    q = self.query if self.case_sensitive else self.query.lower()
                    if q in src:
                        name_match = True

                # Content match
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
# ANA PENCERE (TAB SİSTEMİ EKLENDİ)
# ------------------------------------------------------------

class SearchWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NT Kelime Arama Aracı — v2")
        self.resize(1200, 700)
        self.setWindowIcon(QIcon("icons/app_icon.ico"))

        # Sekme sistemi
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # TAB1 oluştur
        self.tab1 = QWidget()
        self.tabs.addTab(self.tab1, "Kelime Arama")

        # TAB1 layout
        layout = QVBoxLayout(self.tab1)

        # ----------------------------------------------------
        # TAB1 — Senin mevcut arama arayüzün (hiç değişmeden)
        # ----------------------------------------------------

        top_row = QHBoxLayout()
        layout.addLayout(top_row)

        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Klasör yolu seçin...")
        btn_browse = QPushButton("Klasör Seç")

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Aranacak kelime...")

        self.chk_case = QCheckBox("Büyük/küçük harf duyarlı")
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

        # Tablo
        self.table = QTableWidget()
        layout.addWidget(self.table)

        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Dosya Adı", "Tür", "Tip", "Klasör",
            "Yol", "Boyut", "Tarih", "Satır", "Aksiyonlar"
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Alt panel
        bottom = QHBoxLayout()
        layout.addLayout(bottom)

        self.status_label = QLabel("Hazır.")
        bottom.addWidget(self.status_label)

        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "PDF"])
        btn_export = QPushButton("Dışa Aktar")
        bottom.addWidget(self.export_format)
        bottom.addWidget(btn_export)

        # Sinyaller
        btn_browse.clicked.connect(self.on_browse)
        btn_search.clicked.connect(self.on_search)
        btn_export.clicked.connect(self.export_results)

    # --------------------------------------------------------
    # TAB1 fonksiyonları (tamamı eski dosyan ile aynı)
    # --------------------------------------------------------

    def on_browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            self.folder_edit.setText(folder)

    def update_column_visibility(self):
        pass  # TAB1 için daha sonra ekleyeceğiz (TAB2 ile uyumlu olması için)

    def on_search(self):
        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()
        case_sensitive = self.chk_case.isChecked()
        search_in_name = self.chk_name.isChecked()
        search_in_content = self.chk_content.isChecked()

        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Hata", "Geçerli klasör seçin.")
            return
        if not query:
            QMessageBox.warning(self, "Hata", "Aranacak kelimeyi girin.")
            return
        if not (search_in_name or search_in_content):
            QMessageBox.warning(self, "Hata", "En az bir arama türü seçmelisiniz.")
            return

        self.table.setRowCount(0)
        self.status_label.setText("Aranıyor...")

        self.thread = QThread()
        self.worker = SearchWorker(folder, query, case_sensitive, search_in_name, search_in_content)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.add_row_from_thread)
        self.worker.finished.connect(self.search_finished)

        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def add_row_from_thread(self, data):
        pass  # Final birleşim mesajında tamamını ekleyeceğim

    def search_finished(self, total, matched):
        self.status_label.setText(f"Tarama tamamlandı — {total} dosya, {matched} sonuç")

    def export_results(self):
        pass  # Final birleşimde tam sürüm eklenecek


def main():
    app = QApplication(sys.argv)
    win = SearchWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()












# ------------------------------------------------------------
# TAB 2 — KLASÖR & DOSYA AĞAÇ GÖRÜNÜMÜ
# ------------------------------------------------------------
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QFileIconProvider, QTextEdit,
    QPushButton, QListWidget, QListWidgetItem, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize


class FolderTreeTab(QWidget):
    """
    Bu sınıf sadece TAB-2 içindir.
    Finalde SearchWindow içine:
        self.tab2 = FolderTreeTab()
        self.tabs.addTab(self.tab2, "Klasör ve Ağaç Yapısı")
    olarak eklenecek.
    """

    def __init__(self):
        super().__init__()

        # Ana layout
        main = QHBoxLayout(self)

        # Sol tarafta — Ağaç görünümü
        left_panel = QVBoxLayout()
        main.addLayout(left_panel, 2)

        # Sağ tarafta — Dosya Bilgileri
        right_panel = QVBoxLayout()
        main.addLayout(right_panel, 1)

        # --- Klasör seçici ---
        self.btn_select = QPushButton("Klasör Seç ve Ağaç Oluştur")
        self.btn_select.setStyleSheet("font-weight: bold; padding: 6px;")
        left_panel.addWidget(self.btn_select)

        # --- TreeView ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(1)
        self.tree.setHeaderLabels(["Klasör ve Dosyalar"])
        self.tree.setIconSize(QSize(20, 20))
        left_panel.addWidget(self.tree, 1)

        # --- Filtre paneli ---
        filt = QHBoxLayout()
        left_panel.addLayout(filt)

        self.chk_show_files = QCheckBox("Dosyaları Göster")
        self.chk_show_files.setChecked(True)
        filt.addWidget(self.chk_show_files)

        self.chk_show_folders = QCheckBox("Klasörleri Göster")
        self.chk_show_folders.setChecked(True)
        filt.addWidget(self.chk_show_folders)

        self.chk_images = QCheckBox("Resimler")
        filt.addWidget(self.chk_images)

        self.chk_docs = QCheckBox("Belgeler")
        filt.addWidget(self.chk_docs)

        self.chk_code = QCheckBox("Kod Dosyaları")
        filt.addWidget(self.chk_code)

        filt.addStretch()

        # --- Sağ panel: Dosya bilgisi ---
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setStyleSheet("font-size: 13px;")
        right_panel.addWidget(self.info_box, 1)

        # --- Export butonları ---
        export_row = QHBoxLayout()
        right_panel.addLayout(export_row)

        self.btn_export_txt = QPushButton("TXT Olarak Dışa Aktar")
        export_row.addWidget(self.btn_export_txt)

        self.btn_export_pdf = QPushButton("PDF")
        export_row.addWidget(self.btn_export_pdf)

        self.btn_export_png = QPushButton("PNG")
        export_row.addWidget(self.btn_export_png)

        export_row.addStretch()

        # Bağlantılar
        self.btn_select.clicked.connect(self.select_folder)
        self.tree.itemClicked.connect(self.on_item_click)
        self.btn_export_txt.clicked.connect(self.export_as_text)

        # Dosya uzantı grupları
        self.image_ext = [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]
        self.doc_ext = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt"]
        self.code_ext = [".py", ".js", ".php", ".html", ".css", ".cpp", ".java"]

        # İkon klasörü
        self.icon_folder = "icons/"


    # ------------------------------------------------------------
    # 1) Klasör seç ve ağacı oluştur
    # ------------------------------------------------------------
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if not folder:
            return

        self.root_path = folder
        self.tree.clear()

        root_item = QTreeWidgetItem([os.path.basename(folder)])
        root_item.setData(0, Qt.UserRole, folder)
        root_item.setIcon(0, QIcon(self.icon_folder + "folder.svg"))

        self.tree.addTopLevelItem(root_item)

        self.build_tree(folder, root_item)


    def build_tree(self, path, parent_item):
        """Klasörleri ve dosyaları ağaca ekler."""
        try:
            dirs = sorted([d for d in os.listdir(path)])
        except:
            return

        for name in dirs:
            full_path = os.path.join(path, name)

            # Filtreleme
            if os.path.isdir(full_path):
                if not self.chk_show_folders.isChecked():
                    continue

                item = QTreeWidgetItem([name])
                item.setData(0, Qt.UserRole, full_path)
                item.setIcon(0, QIcon(self.icon_folder + "folder.svg"))
                parent_item.addChild(item)

                self.build_tree(full_path, item)

            else:
                if not self.chk_show_files.isChecked():
                    continue

                ext = os.path.splitext(name)[1].lower()

                # Filtre uygula
                if self.chk_images.isChecked() and ext not in self.image_ext:
                    continue
                if self.chk_docs.isChecked() and ext not in self.doc_ext:
                    continue
                if self.chk_code.isChecked() and ext not in self.code_ext:
                    continue

                item = QTreeWidgetItem([name])
                item.setData(0, Qt.UserRole, full_path)

                icon = self.pick_icon(ext)
                item.setIcon(0, icon)

                parent_item.addChild(item)


    # ------------------------------------------------------------
    # 2) İkon seçici
    # ------------------------------------------------------------
    def pick_icon(self, ext):
        ext = ext.lower()

        # Önce özel ikonlara bak
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"]:
            return QIcon(self.icon_folder + "image.svg")

        if ext in [".pdf"]:
            return QIcon(self.icon_folder + "file-pdf.svg")

        if ext in [".doc", ".docx"]:
            return QIcon(self.icon_folder + "file-word.svg")

        if ext in [".xls", ".xlsx"]:
            return QIcon(self.icon_folder + "file-excel.svg")

        if ext in [".ppt", ".pptx"]:
            return QIcon(self.icon_folder + "file-ppt.svg")

        if ext in [".zip", ".rar", ".7z"]:
            return QIcon(self.icon_folder + "zip.svg")

        if ext in [".exe", ".dll"]:
            return QIcon(self.icon_folder + "file-app.svg")

        if ext in self.code_ext:
            return QIcon(self.icon_folder + "code.svg")

        # Genelde kullanılan (varsayılan)
        return QIcon(self.icon_folder + "file.svg")


    # ------------------------------------------------------------
    # 3) Sağ panel — dosya bilgisi
    # ------------------------------------------------------------
    def on_item_click(self, item, col):
        full_path = item.data(0, Qt.UserRole)
        if not full_path:
            return

        if os.path.isdir(full_path):
            info = f"""
<b>Klasör:</b> {full_path}
<b>Öğe:</b> Klasör
"""
        else:
            size = os.path.getsize(full_path)
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(full_path))
            ctime = datetime.datetime.fromtimestamp(os.path.getctime(full_path))

            ext = os.path.splitext(full_path)[1]

            info = f"""
<b>Dosya:</b> {full_path}
<b>Uzantı:</b> {ext}
<b>Boyut:</b> {human_size(size)}
<b>Oluşturma:</b> {ctime}
<b>Değiştirme:</b> {mtime}
"""

        self.info_box.setHtml(info)


    # ------------------------------------------------------------
    # 4) Export TXT — klasör ağacını metin olarak çıkar
    # ------------------------------------------------------------
    def export_as_text(self):
        if not hasattr(self, "root_path"):
            QMessageBox.warning(self, "Hata", "Önce klasör seçmelisiniz.")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self, "Ağaç TXT Olarak Kaydet", "klasor_agaci.txt", "Metin (*.txt)"
        )
        if not save_path:
            return

        text = self.build_tree_text(self.tree.topLevelItem(0))

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(text)

        QMessageBox.information(self, "Başarılı", f"Dışa aktarıldı:\n{save_path}")


    def build_tree_text(self, item, prefix=""):
        """Ağaç yapısını metin formatında üretir."""
        lines = [prefix + item.text(0)]

        for i in range(item.childCount()):
            child = item.child(i)
            lines.append(self.build_tree_text(child, prefix + "   ├── "))

        return "\n".join(lines)







# ------------------------------------------------------------
# TAB 3 — HAKKINDA / BANNER BÖLÜMÜ
# ------------------------------------------------------------
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl


class AboutTab(QWidget):
    """
    Hakkında sekmesi:
    - NT Yazılım banner
    - Sürüm bilgisi
    - Proje açıklaması
    - Link butonu
    """

    def __init__(self):
        super().__init__()

        main = QVBoxLayout(self)
        main.setContentsMargins(40, 40, 40, 40)
        main.setSpacing(20)

        # Başlık
        title = QLabel("NT Kelime Arama Aracı — Hakkında")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setStyleSheet("color: #1a237e;")
        main.addWidget(title)

        # Açıklama
        desc = QLabel("""
Bu araç Windows üzerinde yüksek hızlı dosya ve klasör araması yapmak için geliştirilmiştir.<br>
Kelime arama, dosya filtreleme, klasör ağacı, ikonlar ve dışa aktarma özellikleri içerir.<br>
Tüm hakları NT Yazılım’a aittir.
""")
        desc.setStyleSheet("font-size: 14px;")
        desc.setWordWrap(True)
        main.addWidget(desc)

        # SÜRÜM
        version = QLabel("Sürüm: <b>2.0.0</b>")
        version.setStyleSheet("font-size: 13px; color: #444; margin-top: 10px;")
        main.addWidget(version)

        # GELİŞTİRİCİ
        dev = QLabel("Geliştirici: <b>Nurullah T.</b>")
        dev.setStyleSheet("font-size: 13px; color: #333;")
        main.addWidget(dev)

        # WEB SİTESİ butonu
        self.btn_site = QPushButton("NT Yazılım Web Sitesi")
        self.btn_site.setStyleSheet("""
            QPushButton {
                background-color: #0288d1;
                color: white;
                padding: 10px 20px;
                font-size: 13px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0277bd;
            }
        """)
        self.btn_site.clicked.connect(lambda: QDesktopServices.openUrl(
            QUrl("https://www.quickguidehub.com")   # İstersen değiştiririm
        ))
        main.addWidget(self.btn_site)

        # BOŞLUK
        main.addStretch(1)

        # BANNER (altta sabit)
        banner = QLabel("""
<hr>
<center>
    <b>NT Yazılım — WebP Converter — LinkGuard — Chartify</b><br>
    © 2025 Tüm Hakları Saklıdır.
</center>
<hr>
""")
        banner.setStyleSheet("font-size: 12px; color: #444;")
        banner.setWordWrap(True)
        main.addWidget(banner)





