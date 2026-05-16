import os
import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QPushButton, QHBoxLayout, QMenu,
    QApplication
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QSize


# ===========================================================
#  ICON SİSTEMİ (PNG 32px) — FİNAL
# ===========================================================

ICON_FOLDER = "icons_pack"

# def load_icon(name):
    # path = os.path.join(ICON_FOLDER, name)
    # if os.path.isfile(path):
        # return QIcon(path)
    # return QIcon(os.path.join(ICON_FOLDER, "file.png"))
def load_icon(name: str) -> QIcon:
    path = os.path.join(ICON_FOLDER, name)
    if os.path.isfile(path):
        return QIcon(path)
    fallback = os.path.join(ICON_FOLDER, "file.png")
    return QIcon(fallback if os.path.isfile(fallback) else "")


FILE_ICONS = {
    ".py": "terminal.png",
    ".php": "php.png",
    ".js": "js.png",
    ".ts": "js.png",
    ".html": "html.png",
    ".css": "css.png",

    ".json": "table.png",
    ".xml": "table.png",
    ".ini": "table.png",
    ".env": "table.png",

    ".txt": "text.png",
    ".log": "text.png",
    ".md": "markdown.png",
    ".rtf": "text.png",

    ".png": "image.png",
    ".jpg": "image.png",
    ".jpeg": "image.png",
    ".gif": "image.png",
    ".webp": "image.png",

    ".mp3": "music.png",
    ".wav": "music.png",
    ".mp4": "video.png",

    ".pdf": "pdf.png",
    ".docx": "doc.png",
    ".xlsx": "xls.png",
    ".pptx": "ppt.png",

    ".zip": "archive.png",
    ".rar": "archive.png",
    ".7z": "archive.png",

    ".exe": "cpu.png",
    ".dll": "cpu.png",
}


def icon_for_file(path):
    if os.path.isdir(path):
        return load_icon("folder.png")

    ext = os.path.splitext(path)[1].lower()
    icon_name = FILE_ICONS.get(ext, "file.png")
    return load_icon(icon_name)




# ===========================================================
#  AĞAÇ WIDGET — FİNAL SÜRÜM
# ===========================================================

class AgacWidget(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # ÜST MENÜ
        top = QHBoxLayout()
        self.btn_select = QPushButton("📁 Klasör Seç")
        self.btn_expand = QPushButton("➕ Genişlet")
        self.btn_collapse = QPushButton("➖ Daralt")
        self.btn_export_txt = QPushButton("📄 TXT Kaydet")
        self.btn_export_png = QPushButton("📷 PNG Kaydet")

        top.addWidget(self.btn_select)
        top.addWidget(self.btn_expand)
        top.addWidget(self.btn_collapse)
        top.addWidget(self.btn_export_txt)
        top.addWidget(self.btn_export_png)

        layout.addLayout(top)

        # AĞAÇ
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Ad", "Tür", "Boyut", "Oluşturma", "Değiştirme"])
        self.tree.setSortingEnabled(True)
        self.tree.setColumnWidth(0, 360)
        self.tree.setIndentation(22)
        self.tree.setAnimated(True)
        self.tree.setIconSize(QSize(24, 24))
        # 🔥 32px ikon
        self.tree.setIconSize(QSize(32, 32))

        layout.addWidget(self.tree)

        # EVENTS
        self.btn_select.clicked.connect(self.select_folder)
        self.btn_expand.clicked.connect(self.tree.expandAll)
        self.btn_collapse.clicked.connect(self.tree.collapseAll)
        self.btn_export_txt.clicked.connect(self.export_tree_txt)
        self.btn_export_png.clicked.connect(self.export_tree_png)

        # Sağ tık menü
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_menu)
        
        # SIRALAMA
        self.sort_state = {}     # kolon → asc/desc
        self.tree.header().sectionClicked.connect(self.sort_column)



    # =======================================================
    #  KLASÖR SEÇ
    # =======================================================
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Klasör Seç")
        if folder:
            self.build_tree(folder)



    # =======================================================
    #  AĞAÇ OLUŞUMU
    # =======================================================
    def build_tree(self, root):
        self.tree.clear()

        root_item = QTreeWidgetItem([
            os.path.basename(root),
            "Klasör",
            "",
            ""
        ])
        root_item.setIcon(0, load_icon("folder.png"))
        root_item.setData(0, Qt.UserRole, root)
        root_item.setForeground(0, QColor("#000000"))

        self.tree.addTopLevelItem(root_item)
        self.add_items(root_item, root)

        self.tree.expandToDepth(1)



    # =======================================================
    #  ALT ÖĞELERİ EKLE - AĞAÇ İÇERİĞİ EKLE
    # =======================================================
    def add_items(self, parent_item, path):
        try:
            items = sorted(os.listdir(path), key=str.lower)
        except:
            return

        for name in items:
            full = os.path.join(path, name)

            if os.path.isdir(full):
                ftype = "Klasör"
                size = ""
            else:
                ftype = os.path.splitext(full)[1].upper()
                try:
                    size = self.format_size(os.path.getsize(full))
                except:
                    size = ""

            # Tarih
            try:
                ctime = datetime.datetime.fromtimestamp(
                    os.path.getctime(full)
                ).strftime("%Y-%m-%d %H:%M")
            except:
                ctime = ""
                
            try:
                mtime = datetime.datetime.fromtimestamp(
                    os.path.getmtime(full)
                ).strftime("%Y-%m-%d %H:%M")
            except:
                mtime = ""

            item = QTreeWidgetItem([name, ftype, size, ctime, mtime])
            item.setIcon(0, icon_for_file(full))
            item.setData(0, Qt.UserRole, full)
            
            # Satır rengi → klasör gri, dosya beyaz  RENK İSTEMEZSEN BU 4 SATIRI SİL
            if os.path.isdir(full):
                item.setForeground(0, QColor("#444444"))
            else:
                item.setForeground(0, QColor("#000000"))

            parent_item.addChild(item)

            # Alt klasörleri devam ettir
            if os.path.isdir(full):
                self.add_items(item, full)


    # =======================================================
    #  SAĞ TIK MENÜ
    # =======================================================
    def open_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        full = item.data(0, Qt.UserRole)
        if not full:
            return

        menu = QMenu(self)
        act_open_folder = menu.addAction("📂 Klasörü Aç")
        act_open_file = menu.addAction("📄 Dosyayı Aç")
        act_copy_path = menu.addAction("🔗 Yolu Kopyala")
        act_copy_name = menu.addAction("📝 Adı Kopyala")

        action = menu.exec_(self.tree.viewport().mapToGlobal(pos))

        if action == act_open_folder:
            self.open_folder(full)
        elif action == act_open_file:
            self.open_file(full)
        elif action == act_copy_path:
            QApplication.clipboard().setText(full)
        elif action == act_copy_name:
            QApplication.clipboard().setText(os.path.basename(full))

    def open_file(self, path):
        if os.path.isfile(path):
            os.startfile(path)

    def open_folder(self, path):
        folder = path if os.path.isdir(path) else os.path.dirname(path)
        if os.path.isdir(folder):
            os.startfile(folder)

    # =======================================================
    #  BOYUT FORMAT
    # =======================================================
    def format_size(self, num):
        for u in ["B", "KB", "MB", "GB"]:
            if num < 1024:
                return f"{num:.1f} {u}"
            num /= 1024
        return f"{num:.1f} TB"
        
    # =======================================================
    #  SIRALAMA → ASC / DESC DEĞİŞİMİ
    # =======================================================
    def sort_column(self, col):
        prev = self.sort_state.get(col, None)

        if prev is None:
            order = Qt.AscendingOrder
        elif prev == Qt.AscendingOrder:
            order = Qt.DescendingOrder
        else:
            order = Qt.AscendingOrder

        self.tree.sortItems(col, order)
        self.sort_state[col] = order

    # =======================================================
    #  TXT EXPORT — ÇİZGİLİ AĞAÇ
    # =======================================================
    def export_tree_txt(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "TXT Kaydet", "klasor_agaci.txt", "Metin Dosyası (*.txt)"
        )
        if not path:
            return

        with open(path, "w", encoding="utf-8") as f:
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                self.write_item_txt(f, item, "", True)

    def write_item_txt(self, file, item, prefix, is_last):
        connector = "└── " if is_last else "├── "
        file.write(prefix + connector + item.text(0) + "\n")

        new_prefix = prefix + ("    " if is_last else "│   ")

        count = item.childCount()
        for i in range(count):
            child = item.child(i)
            self.write_item_txt(file, child, new_prefix, i == count - 1)

    # =======================================================
    #  PNG EXPORT — TÜM AĞACI KUSURSUZ RENDER EDEN FİNAL SÜRÜM
    # =======================================================
    def export_tree_png(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "PNG Kaydet", "klasor_agaci.png", "PNG Dosyası (*.png)"
        )
        if not path:
            return

        # 1 TÜM AĞACI AÇ → YÜKSEKLİK HESABI DOĞRU OLSUN
        self.tree.expandAll()
        QApplication.processEvents()  # UI güncellenmesini bekle

        # 2 TÜM SATIR YÜKSEKLİĞİ + HEADER YÜKSEKLİĞİ - VIEWPORT DEĞİL → TÜM SATIR YÜKSEKLİĞİNİ TOPLUYORUZ
        total_rows = self.count_items()
        row_h = self.tree.sizeHintForRow(0)
        height = (total_rows * (row_h + 2)) + self.tree.header().height()

        # 3 GENİŞLİK → HEADER uzunluğu + küçük margin
        width = self.tree.header().length() + 40

        # 4 DEV BİR QPixmap OLUŞTUR
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)

        # 5 QTreeWidget’i geçici olarak tam boyut yap
        old_size = self.tree.size()
        self.tree.resize(width, height)             # AĞACI SONSUZ YÜKSEKLİĞE BÜYÜTÜYORUZ
        QApplication.processEvents()

        # 6 TAM RENDER
        painter = QPainter(pixmap)
        self.tree.render(painter)                   # QTreeWidget’i DEV WIDGET GİBİ KULLANIP TAMAMINI RENDER EDİYORUZ
        painter.end()

        # 7 AĞACI ORİJİNAL BOYUTUNA GERİ DÖNDÜR
        self.tree.resize(old_size)

        # 8 PNG OLARAK KAYDET
        pixmap.save(path, "PNG")



    def count_items(self):
        def _count(item):
            s = 1
            for i in range(item.childCount()):
                s += _count(item.child(i))
            return s

        total = 0
        for i in range(self.tree.topLevelItemCount()):
            total += _count(self.tree.topLevelItem(i))
        return total

    # =======================================================
    #  CTRL + MOUSE ZOOM (WEB / WORD GİBİ)
    # =======================================================
    def wheelEvent(self, event):
        if QApplication.keyboardModifiers() == Qt.ControlModifier:
            delta = event.angleDelta().y()
            font = self.tree.font()
            size = font.pointSize()

            size += 1 if delta > 0 else -1
            size = max(8, min(40, size))

            font.setPointSize(size)
            self.tree.setFont(font)
        else:
            super().wheelEvent(event)
