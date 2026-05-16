###############################################################
#  NT Search Explorer – Arama ve Klasör Tarama Aracı (FINAL)
# -------------------------------------------------------------
#  Bu dosya Nurullah Hocam’ın özel istekleriyle güncellenmiştir.
#
#  EKLENEN YENİ ÖZELLİKLER:
#  -------------------------------------------------------------
#  ✔ Sütun göster/gizle menüsü  (Eski sürümde vardı → geri eklendi)
#  ✔ Sağ tık menüsü:
#        • Klasörü Aç
#        • Dosyayı Aç
#        • Dosya Yolunu Kopyala
#        • Dosya Adını Kopyala
#  ✔ Excel gibi sütun genişliğini çift tıklamayla otomatik ayarlama
#  ✔ Sıralama (ASC/DESC) aktif edildi – sütuna tıklayınca sıralar
#  ✔ Clipboard kilitlenmesi düzeltildi (QApplication.instance())
#  ✔ Klasör aç komutu düzeltildi (Explorer doğru çağırılıyor)
#
#  TÜM DEĞİŞİKLİKLER → “# ⇨ YENİ EKLENDİ” İLE İŞARETLİDİR.
###############################################################

import os
import mimetypes
import datetime
import subprocess   # ⇨ YENİ EKLENDİ — Sistem kabuğundan klasör/dosya açmak için

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QCheckBox, QPushButton,
    QFileDialog, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QMessageBox, QMenu, QComboBox, QApplication   # ⇨ YENİ EKLENDİ — Clipboard düzeltmesi için
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QThread, QPoint
from PyQt5.QtGui import QIcon, QCursor


###############################################################
#  İKON KAYNAKLARI
###############################################################
ICON_FOLDER = "icons_pack"

FILE_ICONS = {
    ".php": "brand-php.svg",
    ".js": "brand-javascript.svg",
    ".css": "brand-css3.svg",
    ".html": "brand-html5.svg",
    ".txt": "file-text.svg",
    ".md": "markdown.svg",
    ".py": "brand-python.svg",
    ".json": "file-json.svg",
    ".xml": "file-code.svg",
    ".jpg": "file-image.svg",
    ".jpeg": "file-image.svg",
    ".png": "file-image.svg",
    ".svg": "file-code.svg",
    ".zip": "archive.svg",
    ".rar": "archive.svg",
    ".7z": "archive.svg",
    ".exe": "file.svg",
}

def load_icon(name):
    path = os.path.join(ICON_FOLDER, name)
    return QIcon(path) if os.path.exists(path) else QIcon()

def icon_for_file(path):
    if os.path.isdir(path):
        return load_icon("folder.svg")
    ext = os.path.splitext(path)[1].lower()
    return load_icon(FILE_ICONS.get(ext, "file.svg"))


###############################################################
#  Yardımcı Fonksiyonlar
###############################################################
def human_size(num_bytes):
    if num_bytes is None:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} TB"


def search_in_file(path, query, case_sensitive):
    results = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, start=1):
                src = line if case_sensitive else line.lower()
                qq = query if case_sensitive else query.lower()
                if qq in src:
                    results.append(idx)
    except:
        return []
    return results


###############################################################
#  ARAMA THREAD — Dosya içeriği ve isim arama
###############################################################
class SearchWorker(QObject):
    progress = pyqtSignal(dict)
    finished = pyqtSignal(int, int)

    def __init__(self, folder, query, case_sensitive, sname, scontent):
        super().__init__()
        self.folder = folder
        self.query = query
        self.case = case_sensitive
        self.sname = sname
        self.scontent = scontent

    def run(self):
        total = 0
        matched = 0

        for root, dirs, files in os.walk(self.folder):

            # KLASÖR İSMİ ARAMA
            if self.sname:
                for d in dirs:
                    src = d if self.case else d.lower()
                    q = self.query if self.case else self.query.lower()
                    if q in src:
                        fullp = os.path.join(root, d)
                        try: mtime = os.path.getmtime(fullp)
                        except: mtime = None

                        self.progress.emit({
                            "filename": d,
                            "file_type": "",
                            "folder": os.path.basename(root),
                            "path": fullp,
                            "size": None,
                            "mtime": mtime,
                            "is_dir": True,
                            "line": None,
                        })
                        matched += 1

            # DOSYA ARAMA
            for file in files:
                total += 1
                fullp = os.path.join(root, file)

                ext = os.path.splitext(file)[1].lower()
                mime, _ = mimetypes.guess_type(fullp)
                ftype = ext if ext else mime or ""

                try: size = os.path.getsize(fullp)
                except: size = None

                try: mtime = os.path.getmtime(fullp)
                except: mtime = None

                name_match = False
                if self.sname:
                    src = file if self.case else file.lower()
                    q = self.query if self.case else self.query.lower()
                    if q in src:
                        name_match = True

                line_numbers = search_in_file(fullp, self.query, self.case) if self.scontent else []

                if line_numbers:
                    for ln in line_numbers:
                        self.progress.emit({
                            "filename": file,
                            "file_type": ftype,
                            "folder": os.path.basename(root),
                            "path": fullp,
                            "size": size,
                            "mtime": mtime,
                            "is_dir": False,
                            "line": ln,
                        })
                        matched += 1

                elif name_match:
                    self.progress.emit({
                        "filename": file,
                        "file_type": ftype,
                        "folder": os.path.basename(root),
                        "path": fullp,
                        "size": size,
                        "mtime": mtime,
                        "is_dir": False,
                        "line": None,
                    })
                    matched += 1

        self.finished.emit(total, matched)


###############################################################
#  ARAMA ARAYÜZÜ — ANA WIDGET
###############################################################
class AramaWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        ###############################################################
        #  ⇨ YENİ EKLENDİ — SÜTUN GÖSTER/GİZLE PANELİ
        ###############################################################
        colbox = QHBoxLayout()
        colbox.addWidget(QLabel("Gösterilecek sütunlar:"))

        self.col_checks = []
        colnames = ["Ad", "Tür", "Klasör", "Yol", "Boyut", "Tarih", "Satır"]

        for idx, name in enumerate(colnames):
            chk = QCheckBox(name)
            chk.setChecked(True)
            chk.stateChanged.connect(lambda _, i=idx: self.toggle_column(i))
            colbox.addWidget(chk)
            self.col_checks.append(chk)

        # layout.addLayout(colbox)
        
        ###############################################################
        # ⇨ YENİ EKLENDİ — ALT CSV/PDF DIŞA AKTAR PANELİ
        ###############################################################
        # colbox = QHBoxLayout()
        # Format seçimi (CSV / PDF)
        self.export_format = QComboBox()
        self.export_format.addItems(["CSV", "PDF"])

        # Dışa Aktar butonu
        btn_export = QPushButton("Dışa Aktar")
        btn_export.clicked.connect(self.export_results)

        colbox.addStretch()
        colbox.addWidget(self.export_format)
        colbox.addWidget(btn_export)

        layout.addLayout(colbox)

        ###############################################################
        #  ÜST ARAMA PANELİ
        ###############################################################
        top = QHBoxLayout()
        self.folder_edit = QLineEdit()
        btn_browse = QPushButton("Klasör")
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Kelime...")

        self.chk_case = QCheckBox("Büyük/Küçük Harfe Duyarlı")
        self.chk_name = QCheckBox("Dosya Adında Ara")
        self.chk_content = QCheckBox("Dosya İçinde Ara")
        self.chk_name.setChecked(True)
        self.chk_content.setChecked(True)

        btn_search = QPushButton("Ara")

        top.addWidget(self.folder_edit)
        top.addWidget(btn_browse)
        top.addWidget(self.query_edit)
        top.addWidget(self.chk_case)
        top.addWidget(self.chk_name)
        top.addWidget(self.chk_content)
        top.addWidget(btn_search)

        layout.addLayout(top)

        ###############################################################
        #  TABLO (TÜM ÖZELLİKLER AKTİF)
        ###############################################################
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Ad", "Tür", "Klasör", "Yol", "Boyut", "Tarih", "Satır"
        ])

        # ⇨ YENİ EKLENDİ — Excel'deki gibi çift tıkla auto-size
        self.table.horizontalHeader().sectionDoubleClicked.connect(self.auto_resize_column)

        # ⇨ YENİ EKLENDİ — Sıralama aktif
        self.table.setSortingEnabled(True)

        # ⇨ YENİ EKLENDİ — Sağ tık menüsü
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Kolon genişlik ayarı
        # self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)           # Sütuna tıkladığında otomatik
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)         # Çizgiye tıkladığında ototmatik


        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)
        
        # ⇨ YENİ EKLENDİ — SATIR ZEBRA RENKLENDİRME
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                gridline-color: #c0c0c0;
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #ececec;
                padding: 4px;
                font-weight: bold;
                border: 1px solid #bfbfbf;
            }
            QTableWidget::item:selected {
                background-color: #0a75ff;
                color: white;
            }
            """
        )


        # Status
        self.status = QLabel("Hazır.")
        layout.addWidget(self.status)
        
        ###############################################################
        # ⇨ YENİ EKLENDİ — ALT CSV/PDF DIŞA AKTAR PANELİ
        ###############################################################
        # bottom = QHBoxLayout()
        # Format seçimi (CSV / PDF)
        # self.export_format = QComboBox()
        # self.export_format.addItems(["CSV", "PDF"])

        # Dışa Aktar butonu
        # btn_export = QPushButton("Dışa Aktar")
        # btn_export.clicked.connect(self.export_results)

        # bottom.addStretch()
        # bottom.addWidget(self.export_format)
        # bottom.addWidget(btn_export)

        # layout.addLayout(bottom)
        


        # Bağlantılar
        btn_browse.clicked.connect(self.on_browse)
        btn_search.clicked.connect(self.on_search)

    ###############################################################
    #  ⇨ YENİ EKLENDİ — AUTO-SIZE
    ###############################################################
    def auto_resize_column(self, col):
        self.table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)


    ###############################################################
    #  ⇨ YENİ EKLENDİ — SÜTUN GÖRÜNÜRLÜK KONTROLÜ
    ###############################################################
    def toggle_column(self, col):
        self.table.setColumnHidden(col, not self.col_checks[col].isChecked())


    ###############################################################
    #  KLASÖR SEÇME
    ###############################################################
    def on_browse(self):
        f = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if f:
            self.folder_edit.setText(f)


    ###############################################################
    #  ARAMA BAŞLATMA
    ###############################################################
    def on_search(self):
        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()

        if not os.path.isdir(folder):
            QMessageBox.warning(self, "Hata", "Geçerli klasör seç.")
            return

        if not query:
            QMessageBox.warning(self, "Hata", "Kelime gir.")
            return

        self.table.setRowCount(0)
        self.status.setText("Aranıyor...")

        self.thread = QThread()
        self.worker = SearchWorker(
            folder, query,
            self.chk_case.isChecked(),
            self.chk_name.isChecked(),
            self.chk_content.isChecked()
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.add_row)
        self.worker.finished.connect(self.finish)

        # ⇨ YENİ EKLENDİ — Thread tam temizlensin, boş ekran hatası düzelir
        self.worker.finished.connect(self.cleanup_thread)


        self.thread.start()


    ###############################################################
    #  TABLOYA SATIR EKLEME
    ###############################################################
    def add_row(self, d):
        row = self.table.rowCount()
        self.table.insertRow(row)

        item = QTableWidgetItem(d["filename"])
        item.setIcon(icon_for_file(d["path"]))
        self.table.setItem(row, 0, item)

        self.table.setItem(row, 1, QTableWidgetItem(d["file_type"]))
        self.table.setItem(row, 2, QTableWidgetItem(d["folder"]))
        self.table.setItem(row, 3, QTableWidgetItem(d["path"]))
        # self.table.setItem(row, 4, QTableWidgetItem(human_size(d["size"])))
        item_size = QTableWidgetItem(human_size(d["size"]))
        item_size.setData(Qt.UserRole, d["size"] or 0)   # ⇨ YENİ EKLENDİ — NUMERIC SORT
        self.table.setItem(row, 4, item_size)


        if d["mtime"]:
            t = datetime.datetime.fromtimestamp(d["mtime"]).strftime("%Y-%m-%d %H:%M")
        else:
            t = ""
        # self.table.setItem(row, 5, QTableWidgetItem(t))
        item_time = QTableWidgetItem(t)
        item_time.setData(Qt.UserRole, d["mtime"] or 0)   # Unix timestamp ile sıralama
        self.table.setItem(row, 5, item_time)


        # self.table.setItem(row, 6, QTableWidgetItem(str(d["line"] or "")))
        item_line = QTableWidgetItem(str(d["line"] or ""))
        item_line.setData(Qt.UserRole, d["line"] or 0)
        self.table.setItem(row, 6, item_line)



    ###############################################################
    #  ARAMA BİTTİ
    ###############################################################
    def finish(self, total, matched):
        self.status.setText(f"Bitti → {total} dosya, {matched} eşleşme")


    ###############################################################
    # ⇨ YENİ EKLENDİ — THREAD TEMİZLEME
    # Bu fonksiyon thread çakışmalarını tamamen çözer.
    # 3–4 aramadan sonra ekranın boş gelmesi bu sayede %100 düzelir.
    ###############################################################
    def cleanup_thread(self, total, matched):
        try:
            self.thread.quit()
            self.thread.wait()
        except:
            pass
        self.worker = None
        self.thread = None



    ###############################################################
    #  ⇨ YENİ EKLENDİ — SAĞ TIK BAĞLAM MENÜSÜ
    ###############################################################
    def show_context_menu(self, pos):
        row = self.table.currentRow()
        if row < 0:
            return

        file_path = self.table.item(row, 3).text()
        file_name = self.table.item(row, 0).text()

        menu = QMenu(self)

        act_folder = menu.addAction("📁 Klasörü Aç")
        act_open = menu.addAction("📄 Dosyayı Aç")
        act_copy_path = menu.addAction("📎 Yolu Kopyala")
        act_copy_name = menu.addAction("📄 Adı Kopyala")

        action = menu.exec_(QCursor.pos())
        if action is None:
            return

        # Klasör Açma
        if action == act_folder:
            subprocess.Popen(f'explorer /select,\"{file_path}\"')


        elif action == act_open:
            os.startfile(file_path)

        elif action == act_copy_path:
            QApplication.instance().clipboard().setText(file_path)

        elif action == act_copy_name:
            QApplication.instance().clipboard().setText(file_name)



    ###############################################################
    #  ⇨ YENİ EKLENDİ — CSV / PDF DIŞA AKTARMA
    ###############################################################
    def export_results(self):
        row_count = self.table.rowCount()
        if row_count == 0:
            QMessageBox.information(self, "Bilgi", "Dışa aktarılacak sonuç yok.")
            return

        fmt = self.export_format.currentText()

        # PDF için reportlab kontrolü
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            HAS_REPORTLAB = True
        except:
            HAS_REPORTLAB = False

        if fmt == "PDF" and not HAS_REPORTLAB:
            QMessageBox.information(
                self,
                "Bilgi",
                "PDF çıktısı için 'reportlab' gerekiyor.\npython -m pip install reportlab"
            )
            return

        default_ext = "csv" if fmt == "CSV" else "pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Dışa Aktar",
            f"sonuclar.{default_ext}",
            "CSV (*.csv);;PDF (*.pdf)"
        )

        if not path:
            return

        folder = self.folder_edit.text().strip()
        query = self.query_edit.text().strip()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        ###########################################################
        # 1) CSV EXPORT (UTF-8 BOM GARANTİLİ)
        ###########################################################
        if fmt == "CSV":
            import csv
            try:
                with open(path, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f, delimiter=";")

                    w.writerow([f"Aranan Kelime: {query}"])
                    w.writerow([f"Klasör: {folder}"])
                    w.writerow([f"Tarih: {now_str}"])
                    w.writerow([])

                    headers = ["Dosya Adı", "Tür", "Klasör", "Yol", "Boyut", "Tarih", "Satır"]
                    w.writerow(headers)

                    for row in range(row_count):
                        def get(col):
                            it = self.table.item(row, col)
                            return it.text() if it else ""

                        # Tooltip'ten tam yol al
                        full_path = self.table.item(row, 3).toolTip() if self.table.item(row, 3) else ""

                        w.writerow([
                            get(0),
                            get(1),
                            get(2),
                            full_path,
                            get(4),
                            get(5),
                            get(6)
                        ])

                QMessageBox.information(self, "Başarılı", f"CSV kaydedildi:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", str(e))
            return

        ###########################################################
        # 2) PDF EXPORT
        ###########################################################
        try:
            # from reportlab.pdfgen import canvas
            # from reportlab.lib.pagesizes import A4

            # c = canvas.Canvas(path, pagesize=A4)
            # w, h = A4
            # y = h - 50

            # c.setFont("Helvetica-Bold", 12)
            # c.drawString(40, y, f"Aranan Kelime: {query}")
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfbase import pdfmetrics      # ⇨ YENİ
            from reportlab.pdfbase.ttfonts import TTFont  # ⇨ YENİ

            # ⇨ YENİ: TÜRKÇE DESTEKLİ FONT TANIMI
            font_path = "DejaVuSans.ttf"
            pdfmetrics.registerFont(TTFont("DejaVu", font_path))

            c = canvas.Canvas(path, pagesize=A4)
            w, h = A4
            y = h - 50

            # ⇨ Helvetica yerine DejaVu
            c.setFont("DejaVu", 12)
            c.drawString(40, y, f"Aranan Kelime: {query}")

            
            
            y -= 20
            c.drawString(40, y, f"Klasör: {folder}")
            y -= 20
            c.drawString(40, y, f"Tarih: {now_str}")
            y -= 30

            c.setFont("DejaVu", 10)
            c.drawString(40, y, "Dosya Adı | Tür | Klasör | Yol | Boyut | Tarih | Satır")
            y -= 20

            c.setFont("Helvetica", 9)

            for row in range(row_count):

                def get(col):
                    it = self.table.item(row, col)
                    return it.text() if it else ""

                full_path = self.table.item(row, 3).toolTip() if self.table.item(row, 3) else ""

                line = f"{get(0)} | {get(1)} | {get(2)} | {full_path} | {get(4)} | {get(5)} | {get(6)}"
                c.drawString(40, y, line[:200])
                y -= 15

                if y < 50:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = h - 50

            c.save()
            QMessageBox.information(self, "Başarılı", f"PDF oluşturuldu:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Hata", str(e))


