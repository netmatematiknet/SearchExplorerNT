import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QDesktopServices
from PyQt5.QtCore import Qt, QUrl, QTimer
import webbrowser

from arama import AramaWidget
from agac import AgacWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("NT Arama ve Klasör Aracı")
        self.setWindowIcon(QIcon("icons_pack/logom_64.ico"))
        
        # İSTEK 1: 1200px genişlik - isterseniz burayı değiştirebilirsiniz
        self.resize(1200, 850)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tabs.setTabsClosable(False)
        self.tabs.addTab(AramaWidget(), QIcon("icons_pack/search.svg"), "Kelime Arama")
        self.tabs.addTab(AgacWidget(),  QIcon("icons_pack/tree.svg"),   "Klasör Ağacı")

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)

        main_layout.addWidget(self.tabs)

        # ----------------------------
        # GÜVENLİ URL AÇMA
        # ----------------------------
        def safe_open(url):
            QTimer.singleShot(50, lambda: QDesktopServices.openUrl(QUrl(url)))

        # ----------------------------
        # ÜSTTEKİ SABİT BANNERLAR
        # ----------------------------
        banner_layout = QHBoxLayout()

        def make_clickable(label, url):
            label.setCursor(QCursor(Qt.PointingHandCursor))
            label.mousePressEvent = lambda event, u=url: safe_open(u)

        # Banner 1
        banner1 = QLabel()
        banner1.setPixmap(QPixmap("icons_pack/quickguidehub_400.webp").scaledToHeight(60, Qt.SmoothTransformation))
        make_clickable(banner1, "https://www.quickguidehub.com")
        banner_layout.addWidget(banner1)

        # Banner 2
        banner2 = QLabel()
        banner2.setPixmap(QPixmap("icons_pack/mobilprogramlar_400.webp").scaledToHeight(60, Qt.SmoothTransformation))
        make_clickable(banner2, "https://www.mobilprogramlar.com/")
        banner_layout.addWidget(banner2)

        # Banner 3
        banner3 = QLabel()
        banner3.setPixmap(QPixmap("icons_pack/ossmatematik_400.webp").scaledToHeight(60, Qt.SmoothTransformation))
        make_clickable(banner3, "https://www.ossmatematik.com.tr/")
        banner_layout.addWidget(banner3)

        # Banner 4
        banner4 = QLabel()
        banner4.setPixmap(QPixmap("icons_pack/webp.quickguidehub_400.webp").scaledToHeight(60, Qt.SmoothTransformation))
        make_clickable(banner4, "https://webp.quickguidehub.com/index.php/ana-sayfa/")
        banner_layout.addWidget(banner4)

        # Banner 5
        banner5 = QLabel()
        banner5.setPixmap(QPixmap("icons_pack/products.quickguidehub_400.webp").scaledToHeight(60, Qt.SmoothTransformation))
        make_clickable(banner5, "https://products.quickguidehub.com/")
        banner_layout.addWidget(banner5)

        banner_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(banner_layout)

        # -----------------------------------
        # SLAYTER - 1200px GENİŞLİKTE
        # -----------------------------------
        # from slider import SliderWidget
        # self.slider = SliderWidget()
        # main_layout.addWidget(self.slider)
        # self.setCentralWidget(main_widget)
        
        from slider import SliderWidget
        self.slider = SliderWidget()        
        # YENİ: Slider'ı ortalamak için bir yatay layout içine alalım
        slider_container = QWidget()
        slider_container_layout = QHBoxLayout()
        slider_container_layout.setContentsMargins(0, 0, 0, 0)
        slider_container_layout.addWidget(self.slider)
        slider_container.setLayout(slider_container_layout)        
        main_layout.addWidget(slider_container, alignment=Qt.AlignCenter)  # Ortala
        self.setCentralWidget(main_widget)
        
        



def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()