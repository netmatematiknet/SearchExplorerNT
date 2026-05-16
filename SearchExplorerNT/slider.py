# ======================================================================
# slider.py — BASİT, AÇIK, CONSTANT'LARLA KONTROLLÜ SLAYTER
# ======================================================================

import json
import requests
from PyQt5.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QGraphicsDropShadowEffect
)
from PyQt5.QtGui import QPixmap, QDesktopServices, QColor
from PyQt5.QtCore import (
    Qt, QTimer, QUrl, QPropertyAnimation, QEasingCurve, QPoint
)

# ===============================================================
# 🔥 SABİTLER — TEK YERDEN KONTROL (Değiştirmesi ÇOK KOLAY)
# ===============================================================

# 1. SLAYTER GENİŞLİĞİ
SLIDER_WIDTH = 1200
SLIDER_HEIGHT = 150

# 3. EKRANDA AYNI ANDA GÖRÜNEN BANNER SAYISI - İSTEK 5: Bu değişebilir
VISIBLE_COUNT = 3  # Örnek: 3, 4, 5 yapabilirsiniz

# 4. BUFFER (ÖNBELLEK) BANNER SAYISI - İSTEK 2,5: Görünenler + Buffer
BUFFER_COUNT = 1   # Örnek: 1 veya 2 yapabilirsiniz

# 5. TOPLAM YÜKLENECEK BANNER SAYISI = Görünen + Buffer
TOTAL_VISIBLE = VISIBLE_COUNT + BUFFER_COUNT

# 2. BANNER BOYUTLARI - Tek bir bannerın genişlik/yükseklik oranı
BANNER_WIDTH = 150
BANNER_HEIGHT = 100
# BANNER_WIDTH = int(SLIDER_WIDTH / VISIBLE_COUNT) - 20
# BANNER_HEIGHT = SLIDER_HEIGHT - 20


# 6. DİĞER AYARLAR
SPACING = 2                    # Bannerlar arası boşluk
BTN_WIDTH = 40                 # Ok buton genişliği
AUTO_SPEED = 4000              # Otomatik kaydırma hızı (ms)
ANIM_DURATION = 450            # Animasyon süresi (ms)
HOVER_PAUSE = True             # Mouse üstünde durdur
ENABLE_SHADOW = True           # Gölge efekti
ENABLE_TINT_HOVER = True       # Hover efekti

# 7. MARGIN AYARLARI - Kenar boşlukları
LEFT_MARGIN = 0
RIGHT_MARGIN = 0
TOP_MARGIN = 0
BOTTOM_MARGIN = 0

# 8. DOSYA AYARLARI
FALLBACK_IMAGE = "icons_pack/fallback.png"
JSON_URL = "https://quickguidehub.com/wp-content/uploads/2025/11/banners.json"

# 9. GÖLGE AYARLARI
SHADOW_BLUR = 20
SHADOW_OFFSET_X = 0
SHADOW_OFFSET_Y = 4

# ======================================================================
# 🎯 SLAYTER SINIFI - TÜM MANTIK BUARADA
# ======================================================================

class SliderWidget(QWidget):
    def __init__(self):
        super().__init__()

        # 1. SLAYTER BOYUTU - İSTEK 1: 1200px genişlik
        # self.setFixedSize(SLIDER_WIDTH, SLIDER_HEIGHT)    # Sabit 
        
        # Dinamik yükseklik olsun istiyorsan flexible
        self.setMinimumSize(SLIDER_WIDTH, SLIDER_HEIGHT)
        self.setMaximumHeight(SLIDER_HEIGHT)


        
         # 🔥 YENİ EKLENEN: 2px SİYAH ÇERÇEVE - Slayt alanını görmek için
        self.setStyleSheet("border: 2px solid black;")

        # 2. ANA LAYOUT - Kenar boşlukları sıfır
        main = QHBoxLayout(self)
        main.setContentsMargins(LEFT_MARGIN, TOP_MARGIN, RIGHT_MARGIN, BOTTOM_MARGIN)
        main.setSpacing(SPACING)

        # 3. SOL OK BUTONU
        self.btn_left = QPushButton("◀")
        self.btn_left.setFixedWidth(BTN_WIDTH)
        self.btn_left.clicked.connect(self.prev_banner)
        self.btn_left.hide()  # Başlangıçta gizli
        main.addWidget(self.btn_left)

        # 4. BANNER ALANI - Görünen + Buffer kadar banner olacak
        self.banner_area = QWidget()
        self.banner_layout = QHBoxLayout(self.banner_area)
        self.banner_layout.setContentsMargins(0, 0, 0, 0)
        self.banner_layout.setSpacing(SPACING)

        # 5. BANNER LABELLARI OLUŞTUR - TOPLAM_VISIBLE kadar (Görünen + Buffer)
        self.labels = []
        for i in range(TOTAL_VISIBLE):
            lbl = QLabel()
            # lbl.setFixedSize(BANNER_WIDTH, BANNER_HEIGHT)
            
            # Label boyutları (banner görselleri) — slider yüksekliğine göre otomatik ayarlansın
            lbl.setFixedSize(BANNER_WIDTH, SLIDER_HEIGHT - 20)

            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("background-color: transparent;")

            # Hover efekti
            if ENABLE_TINT_HOVER:
                lbl.setStyleSheet("""
                    QLabel {
                        background-color: transparent;
                        border-radius: 6px;
                    }
                    QLabel:hover {
                        background-color: rgba(255,255,255,40);
                        border-radius: 6px;
                    }
                """)

            # Gölge efekti
            if ENABLE_SHADOW:
                shadow = QGraphicsDropShadowEffect()
                shadow.setBlurRadius(SHADOW_BLUR)
                shadow.setOffset(SHADOW_OFFSET_X, SHADOW_OFFSET_Y)
                shadow.setColor(QColor(0, 0, 0, 160))
                lbl.setGraphicsEffect(shadow)

            self.banner_layout.addWidget(lbl)
            self.labels.append(lbl)

        main.addWidget(self.banner_area)

        # 6. SAĞ OK BUTONU
        self.btn_right = QPushButton("▶")
        self.btn_right.setFixedWidth(BTN_WIDTH)
        self.btn_right.clicked.connect(self.next_banner)
        self.btn_right.hide()  # Başlangıçta gizli
        main.addWidget(self.btn_right)

        # 7. VERİ VE DURUM DEĞİŞKENLERİ
        self.banners = []       # Tüm banner listesi
        self.current_index = 0  # Şu anki başlangıç index'i
        self.anim_running = False  # Animasyon kontrolü

        # 8. VERİYİ YÜKLE VE GÖRÜNTÜYÜ GÜNCELLE
        self.load_json()
        self.update_view()

        # 9. OTOMATİK KAYDIRMA ZAMANLAYICISI
        self.timer = QTimer()
        self.timer.timeout.connect(self.next_banner)
        self.timer.start(AUTO_SPEED)

        # 10. HOVER KONTROLÜ
        if HOVER_PAUSE:
            self.banner_area.installEventFilter(self)
            self.installEventFilter(self)

        # 11. MOUSE TAKİBİ
        self.setMouseTracking(True)
        self.banner_area.setMouseTracking(True)

    # ============================================================
    # 📥 JSON VERİSİNİ YÜKLE
    # ============================================================
    def load_json(self):
        try:
            # İnternetten JSON'u çek
            r = requests.get(JSON_URL, timeout=3)
            data = json.loads(r.text)
            self.banners = data["banners"]
        except:
            # İnternet yoksa yedek bannerları kullan
            self.banners = [
                {"image": "icons_pack/quickguidehub_400.webp", "url": "#"},
                {"image": "icons_pack/mobilprogramlar_400.webp", "url": "#"},
                {"image": "icons_pack/ossmatematik_400.webp", "url": "#"},
                {"image": "icons_pack/products.quickguidehub_400.webp", "url": "#"},
                {"image": "icons_pack/webp.quickguidehub_400.webp", "url": "#"},
            ]

    # ============================================================
    # 🖼️ BANNERLARI GÜNCELLE - EN ÖNEMLİ KISIM!
    # ============================================================
    def update_view(self):
        """
        İSTEK 2,3,4,5: Sonsuz döngü mantığı
        - Görünen kadar banner + buffer kadar banner yüklenir
        - Örnek: 3 görünen + 1 buffer = 4 banner yüklenir
        - Buffer, döngüdeki sıradaki bannerı önceden yükler
        """
        
        # TOPLAM_VISIBLE kadar banner yükle (Görünen + Buffer)
        for i in range(TOTAL_VISIBLE):
            # İSTEK 4: Sonsuz döngü için modulo kullan
            banner_index = (self.current_index + i) % len(self.banners)
            banner = self.banners[banner_index]
            
            # Resmi yükle
            pix = self.load_pixmap_safe(banner["image"])
            
            # Banner'a resmi yerleştir
            self.labels[i].setPixmap(
                # pix.scaled(BANNER_WIDTH, BANNER_HEIGHT, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                pix.scaled(BANNER_WIDTH, SLIDER_HEIGHT - 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)       # Pixmap scaling
            )

            # Tıklanabilirlik ekle
            self.labels[i].mousePressEvent = (
                lambda e, url=banner["url"]: self.safe_open_url(url)
            )

    # ============================================================
    # 🖼️ GÜVENLİ RESİM YÜKLEME
    # ============================================================
    def load_pixmap_safe(self, path):
        pix = QPixmap()
        try:
            if path.startswith("http"):
                # İnternetten resim yükle
                r = requests.get(path, timeout=3)
                pix.loadFromData(r.content)
            else:
                # Yerel resmi yükle
                pix.load(path)
        except:
            pass  # Hata durumunda boş pixmap

        # Resim yüklenemediyse yedek resmi kullan
        if pix.isNull():
            return QPixmap(FALLBACK_IMAGE)

        return pix

    # ============================================================
    # 🔗 GÜVENLİ URL AÇMA
    # ============================================================
    def safe_open_url(self, url):
        if url and url != "#":
            QTimer.singleShot(10, lambda: QDesktopServices.openUrl(QUrl(url)))

    # ============================================================
    # 🎬 ANİMASYONLU KAYDIRMA
    # ============================================================
    def animate_slide(self, direction):
        if self.anim_running:
            return

        self.anim_running = True

        anim = QPropertyAnimation(self.banner_area, b"pos")
        anim.setDuration(ANIM_DURATION)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        start = self.banner_area.pos()
        end = QPoint(start.x() - direction * (BANNER_WIDTH + SPACING), start.y())

        anim.setStartValue(start)
        anim.setEndValue(end)

        anim.finished.connect(lambda: self.finish_slide(direction))
        anim.start()

        self.anim = anim

    def finish_slide(self, direction):
        # İSTEK 3,4: Sonsuz döngü - 1 kaydırma yap
        self.current_index = (self.current_index + direction) % len(self.banners)
        
        # Görünümü güncelle (Buffer dahil)
        self.update_view()
        
        # Banner alanını sıfırla
        self.banner_area.move(0, self.banner_area.y())
        self.anim_running = False

    # ============================================================
    # ◀▶ İLERİ/GERİ KAYDIRMA
    # ============================================================
    def next_banner(self):
        self.animate_slide(+1)  # +1 = Sağa kaydır

    def prev_banner(self):
        self.animate_slide(-1)  # -1 = Sola kaydır

    # ============================================================
    # 🖱️ HOVER KONTROLÜ
    # ============================================================
    def eventFilter(self, obj, event):
        if event.type() == event.Enter:
            # Mouse üzerine gelince: Durdur + Okları göster
            self.timer.stop()
            self.btn_left.show()
            self.btn_right.show()
        elif event.type() == event.Leave:
            # Mouse ayrılınca: Devam et + Okları gizle
            self.timer.start(AUTO_SPEED)
            self.btn_left.hide()
            self.btn_right.hide()
        return super().eventFilter(obj, event)

    def mouseMoveEvent(self, event):
        # Mouse hareket edince okları göster
        self.btn_left.show()
        self.btn_right.show()
        super().mouseMoveEvent(event)