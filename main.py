"""
소주 주량 트래커 (Soju Drinking Capacity Tracker)

- 상단에서 주량 선택
- 귀여운 남자 얼굴이 한 잔마다 점점 빨개짐
- 주량 도달 시 개 얼굴로 변신 + 알림음 반복
- 소주잔 이미지 버튼으로 음주 기록
"""

import os
import math
import struct
import wave
import tempfile

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import platform

# ── Korean Font ─────────────────────────────────────────────
_FONT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "fonts", "NotoSansKR-Regular.ttf"
)
if os.path.exists(_FONT_PATH):
    LabelBase.register(name="NotoSansKR", fn_regular=_FONT_PATH)
    FONT = "NotoSansKR"
else:
    FONT = "Roboto"

# ── Colors (warm cute theme) ───────────────────────────────
C_BG      = (0.14, 0.14, 0.19, 1)
C_BTN_SEL = (0.35, 0.75, 0.55, 1)
C_TEXT    = (1, 1, 1, 1)
C_DIM     = (0.65, 0.65, 0.72, 1)
C_GREEN   = (0.30, 0.72, 0.50, 1)
C_ORANGE  = (0.95, 0.65, 0.25, 1)
C_RED     = (0.90, 0.30, 0.30, 1)

# 주량 버튼 파스텔 색상 (각각 다른 색)
CAP_COLORS = [
    (0.55, 0.75, 0.92, 1),   # 0.5병 - 하늘
    (0.55, 0.82, 0.65, 1),   # 1병   - 민트
    (0.90, 0.75, 0.55, 1),   # 1.5병 - 살구
    (0.80, 0.60, 0.80, 1),   # 2병   - 보라
    (0.92, 0.65, 0.65, 1),   # 2.5병 - 코랄
    (0.65, 0.65, 0.88, 1),   # 3병   - 라벤더
]

# ── Soju math ───────────────────────────────────────────────
GLASSES_PER_BOTTLE = 7.2
BOTTLES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def limit_glasses(bottles):
    return round(bottles * GLASSES_PER_BOTTLE)


# ── Alarm sound ─────────────────────────────────────────────
def _make_alarm(path, freq=880, dur=0.6, sr=44100):
    n = int(sr * dur)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            env = 0.8 if (t % 0.3) < 0.15 else 0.0
            s = int(32767 * env * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", max(-32768, min(32767, s)))
        w.writeframes(bytes(frames))


# ── UI helpers ──────────────────────────────────────────────
def _btn(text, fs=18, bg=(0.3, 0.3, 0.4, 1), color=C_TEXT, bold=False, **kw):
    return Button(
        text=text, font_name=FONT, font_size=sp(fs),
        color=color, bold=bold,
        background_normal="", background_color=bg,
        **kw,
    )


def _lbl(text, fs=16, color=C_TEXT, bold=False, **kw):
    return Label(
        text=text, font_name=FONT, font_size=sp(fs),
        color=color, bold=bold, markup=True,
        **kw,
    )


# ── Cute face widget ───────────────────────────────────────
class FaceView(Widget):
    """귀여운 남자 얼굴 - 술 마실수록 빨개지고, 주량 도달 시 개로 변신"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.redness = 0.0
        self.is_dog = False
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        if w < 10 or h < 10:
            return
        cx, cy = x + w / 2, y + h / 2
        r = min(w, h) * 0.33

        with self.canvas:
            # Background
            Color(*C_BG)
            Rectangle(pos=(x, y), size=(w, h))

            if self.is_dog:
                self._dog(cx, cy, r)
            else:
                self._man(cx, cy, r)

    def _man(self, cx, cy, r):
        red = self.redness

        # ── Hair (behind head) ──
        Color(0.22, 0.16, 0.10, 1)
        Ellipse(pos=(cx - r * 0.95, cy + r * 0.25), size=(r * 1.9, r * 1.05))

        # ── Head ──
        sg = 0.82 - red * 0.30
        sb = 0.72 - red * 0.42
        Color(1.0, sg, sb, 1)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

        # ── Eyebrows ──
        Color(0.25, 0.18, 0.12, 1)
        brow_y = cy + r * 0.38
        bw, bh = r * 0.22, r * 0.05
        tilt = red * dp(3)
        Ellipse(pos=(cx - r * 0.38 - bw / 2, brow_y + tilt), size=(bw, bh))
        Ellipse(pos=(cx + r * 0.38 - bw / 2, brow_y - tilt), size=(bw, bh))

        # ── Eyes ──
        ey = cy + r * 0.18
        ew = r * 0.17
        eh = r * 0.19 * max(0.25, 1.0 - red * 0.55)

        Color(1, 1, 1, 1)
        Ellipse(pos=(cx - r * 0.33 - ew, ey - eh), size=(ew * 2, eh * 2))
        Ellipse(pos=(cx + r * 0.33 - ew, ey - eh), size=(ew * 2, eh * 2))

        if eh > r * 0.04:
            # Pupils
            pr = min(ew, eh) * 0.55
            Color(0.12, 0.10, 0.08, 1)
            Ellipse(pos=(cx - r * 0.33 - pr, ey - pr), size=(pr * 2, pr * 2))
            Ellipse(pos=(cx + r * 0.33 - pr, ey - pr), size=(pr * 2, pr * 2))
            # Eye highlights
            hr = pr * 0.35
            Color(1, 1, 1, 0.85)
            Ellipse(pos=(cx - r * 0.27, ey + pr * 0.35), size=(hr, hr))
            Ellipse(pos=(cx + r * 0.39, ey + pr * 0.35), size=(hr, hr))

        # ── Cheeks (get redder!) ──
        ca = 0.20 + red * 0.60
        Color(1.0, 0.35, 0.35, ca)
        cr = r * 0.16
        Ellipse(pos=(cx - r * 0.58 - cr, cy - r * 0.12 - cr), size=(cr * 2, cr * 2))
        Ellipse(pos=(cx + r * 0.58 - cr, cy - r * 0.12 - cr), size=(cr * 2, cr * 2))

        # ── Nose ──
        Color(0.92, max(0.65 - red * 0.2, 0.45), max(0.55 - red * 0.3, 0.25), 1)
        nr = r * 0.06
        Ellipse(pos=(cx - nr, cy - r * 0.05 - nr), size=(nr * 2, nr * 2))

        # ── Mouth ──
        mw = r * (0.22 + red * 0.28)
        mh = r * (0.06 + red * 0.16)
        my = cy - r * 0.32
        Color(0.82, 0.22, 0.22, 1)
        Ellipse(pos=(cx - mw / 2, my - mh / 2), size=(mw, mh))
        if mh > r * 0.1:
            Color(0.95, 0.45, 0.45, 1)
            Ellipse(pos=(cx - mw * 0.3, my), size=(mw * 0.6, mh * 0.4))

        # ── Sweat drops when very drunk ──
        if red > 0.6:
            Color(0.6, 0.8, 1.0, 0.7)
            Ellipse(pos=(cx + r * 0.75, cy + r * 0.3), size=(r * 0.08, r * 0.12))
        if red > 0.85:
            Ellipse(pos=(cx - r * 0.82, cy + r * 0.15), size=(r * 0.07, r * 0.10))

    def _dog(self, cx, cy, r):
        # ── Ears (floppy, behind head) ──
        Color(0.58, 0.38, 0.22, 1)
        ew, eh = r * 0.50, r * 0.85
        Ellipse(pos=(cx - r - ew * 0.35, cy - r * 0.05), size=(ew, eh))
        Ellipse(pos=(cx + r - ew * 0.65, cy - r * 0.05), size=(ew, eh))

        # ── Head ──
        Color(0.85, 0.72, 0.50, 1)
        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))

        # ── Muzzle ──
        Color(0.93, 0.83, 0.65, 1)
        mr = r * 0.48
        Ellipse(pos=(cx - mr, cy - r * 0.65), size=(mr * 2, mr * 1.2))

        # ── Eyes (big, cute) ──
        ey = cy + r * 0.22
        er = r * 0.22
        Color(1, 1, 1, 1)
        Ellipse(pos=(cx - r * 0.38 - er, ey - er), size=(er * 2, er * 2))
        Ellipse(pos=(cx + r * 0.38 - er, ey - er), size=(er * 2, er * 2))
        # Pupils
        pr = er * 0.62
        Color(0.08, 0.06, 0.04, 1)
        Ellipse(pos=(cx - r * 0.38 - pr, ey - pr), size=(pr * 2, pr * 2))
        Ellipse(pos=(cx + r * 0.38 - pr, ey - pr), size=(pr * 2, pr * 2))
        # Highlights
        hr = er * 0.28
        Color(1, 1, 1, 0.9)
        Ellipse(pos=(cx - r * 0.30, ey + er * 0.25), size=(hr, hr))
        Ellipse(pos=(cx + r * 0.46, ey + er * 0.25), size=(hr, hr))

        # ── Eyebrows (worried) ──
        Color(0.45, 0.30, 0.18, 1)
        bbw, bbh = r * 0.18, r * 0.04
        Ellipse(pos=(cx - r * 0.42 - bbw / 2, ey + er + r * 0.08), size=(bbw, bbh))
        Ellipse(pos=(cx + r * 0.42 - bbw / 2, ey + er + r * 0.08), size=(bbw, bbh))

        # ── Nose ──
        Color(0.15, 0.10, 0.08, 1)
        nw, nh = r * 0.15, r * 0.10
        Ellipse(pos=(cx - nw, cy - r * 0.18), size=(nw * 2, nh * 2))

        # ── Tongue ──
        Color(1.0, 0.50, 0.50, 1)
        tw, th = r * 0.20, r * 0.38
        RoundedRectangle(
            pos=(cx - tw, cy - r * 0.62), size=(tw * 2, th),
            radius=[dp(2), dp(2), tw, tw],
        )
        Color(0.92, 0.40, 0.40, 1)
        Line(
            points=[cx, cy - r * 0.62, cx, cy - r * 0.62 + th * 0.85],
            width=dp(1),
        )

        # ── Red cheeks ──
        Color(1.0, 0.40, 0.40, 0.40)
        ccr = r * 0.14
        Ellipse(pos=(cx - r * 0.60 - ccr, cy - r * 0.12 - ccr), size=(ccr * 2, ccr * 2))
        Ellipse(pos=(cx + r * 0.60 - ccr, cy - r * 0.12 - ccr), size=(ccr * 2, ccr * 2))

    def set_redness(self, ratio):
        self.redness = max(0.0, min(1.0, ratio))
        self.is_dog = False
        self._draw()

    def show_dog(self):
        self.is_dog = True
        self._draw()

    def reset(self):
        self.redness = 0.0
        self.is_dog = False
        self._draw()


# ── Soju glass button ──────────────────────────────────────
class GlassBtn(RelativeLayout):
    """소주잔 아이콘 + 텍스트 버튼"""

    def __init__(self, text="한 잔!", on_press=None, **kw):
        super().__init__(**kw)
        self._on_press = on_press
        self._color = C_GREEN

        self.label = Label(
            text=text, font_name=FONT, font_size=sp(20),
            bold=True, color=C_TEXT,
            pos_hint={"center_x": 0.58, "center_y": 0.5},
        )
        self.add_widget(self.label)

        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_once(lambda dt: self._draw(), 0)

    def _draw(self, *a):
        self.canvas.before.clear()
        x, y = self.pos
        w, h = self.size

        with self.canvas.before:
            # Background
            Color(*self._color)
            RoundedRectangle(pos=(x, y), size=(w, h), radius=[dp(14)])

            # ── Glass icon (left side) ──
            gx = x + w * 0.08
            gy = y + h * 0.15
            gw = dp(22)
            gh = h * 0.70

            # Glass body
            Color(0.85, 0.90, 0.95, 0.60)
            RoundedRectangle(
                pos=(gx, gy), size=(gw, gh),
                radius=[dp(3), dp(3), dp(1), dp(1)],
            )
            # Liquid
            Color(0.78, 0.92, 0.80, 0.45)
            lh = gh * 0.55
            RoundedRectangle(
                pos=(gx + dp(2), gy + dp(2)),
                size=(gw - dp(4), lh),
                radius=[dp(1)],
            )
            # Sparkle
            Color(1, 1, 1, 0.65)
            Ellipse(pos=(gx + gw * 0.55, gy + gh * 0.65), size=(dp(3), dp(3)))
            Ellipse(pos=(gx + gw * 0.2, gy + gh * 0.45), size=(dp(2), dp(2)))

    def set_state(self, text, color):
        self.label.text = text
        self._color = color
        self._draw()

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        if self.collide_point(*touch.pos) and self._on_press:
            self._on_press()
            return True
        return super().on_touch_down(touch)


# ── Main tracker widget ─────────────────────────────────────
class SojuTracker(BoxLayout):

    def __init__(self, **kw):
        pad_top = dp(28) if platform == "android" else dp(10)
        super().__init__(
            orientation="vertical",
            padding=[dp(10), pad_top, dp(10), dp(10)],
            spacing=dp(4),
            **kw,
        )

        self.sel = None
        self.limit = 0
        self.count = 0
        self.alarmed = False
        self._cap_btns = {}
        self._sound = self._load_sound()

        self._draw_bg()
        self._build()

    def _draw_bg(self):
        with self.canvas.before:
            Color(*C_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

    def _sync_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _load_sound(self):
        try:
            p = os.path.join(tempfile.gettempdir(), "soju_alarm.wav")
            _make_alarm(p)
            snd = SoundLoader.load(p)
            if snd:
                snd.loop = True
            return snd
        except Exception:
            return None

    def _stop_sound(self):
        if self._sound:
            try:
                self._sound.stop()
            except Exception:
                pass

    # ── UI 구성 ──
    def _build(self):
        # 제목
        self.add_widget(_lbl(
            "소주 주량 트래커", fs=22, bold=True,
            size_hint_y=None, height=dp(32),
        ))
        self.add_widget(_lbl(
            "1병(360ml) = 소주잔(50ml) x 7.2잔",
            fs=11, color=C_DIM, size_hint_y=None, height=dp(16),
        ))

        # 주량 선택 안내
        self.add_widget(_lbl(
            "나의 주량을 선택하세요!",
            fs=13, color=C_DIM, size_hint_y=None, height=dp(22),
        ))

        # 주량 선택 버튼 (3x2, 파스텔 색상)
        grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(90))
        for i, b in enumerate(BOTTLES):
            g = limit_glasses(b)
            btn = _btn(f"{b:g}병\n({g}잔)", fs=13, bg=CAP_COLORS[i])
            btn.halign = "center"
            btn.bind(on_release=lambda _, v=b: self._pick(v))
            self._cap_btns[b] = btn
            grid.add_widget(btn)
        self.add_widget(grid)

        # ── 음주 기록 영역 (선택 전 숨김) ──
        self.drink_box = BoxLayout(
            orientation="vertical", spacing=dp(4),
            opacity=0, disabled=True,
        )

        # 주량 정보
        self.info_lbl = _lbl("", fs=13, color=C_DIM,
                             size_hint_y=None, height=dp(22))
        self.drink_box.add_widget(self.info_lbl)

        # 귀여운 얼굴 뷰
        self.face = FaceView(size_hint_y=1)
        self.drink_box.add_widget(self.face)

        # 잔 수 표시
        self.frac_lbl = _lbl("", fs=14, color=C_DIM,
                             size_hint_y=None, height=dp(20))
        self.drink_box.add_widget(self.frac_lbl)

        # 소주잔 버튼
        self.glass_btn = GlassBtn(
            text="한 잔!", on_press=self._drink,
            size_hint_y=None, height=dp(60),
        )
        self.drink_box.add_widget(self.glass_btn)

        # 하단 버튼
        row = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(38))
        rb = _btn("초기화", fs=12, bg=(0.65, 0.35, 0.35, 1))
        rb.bind(on_release=self._reset)
        cb = _btn("주량 변경", fs=12, bg=(0.45, 0.45, 0.60, 1))
        cb.bind(on_release=self._change)
        row.add_widget(rb)
        row.add_widget(cb)
        self.drink_box.add_widget(row)

        self.add_widget(self.drink_box)

    # ── 주량 선택 ──
    def _pick(self, bottles):
        self.sel = bottles
        self.limit = limit_glasses(bottles)
        self.count = 0
        self.alarmed = False

        for i, (v, b) in enumerate(self._cap_btns.items()):
            b.background_color = C_BTN_SEL if v == bottles else CAP_COLORS[i]

        self.drink_box.opacity = 1
        self.drink_box.disabled = False
        self.face.reset()
        self._refresh()

    # ── 한 잔 마심 ──
    def _drink(self):
        if self.sel is None:
            return
        self.count += 1
        self._refresh()
        if self.count >= self.limit and not self.alarmed:
            self.alarmed = True
            Clock.schedule_once(lambda dt: self._alarm(), 0.05)
        elif self.count > self.limit:
            Clock.schedule_once(lambda dt: self._extra_warning(), 0.05)

    # ── 화면 갱신 ──
    def _refresh(self):
        c, lim = self.count, self.limit
        self.info_lbl.text = f"주량: {self.sel:g}병 ({lim}잔)"
        self.frac_lbl.text = f"{c} / {lim} 잔"

        ratio = c / lim if lim else 0

        if c >= lim:
            self.face.show_dog()
            self.glass_btn.set_state("그만 드세요!", C_RED)
        elif c >= lim * 0.7:
            self.face.set_redness(min(1.0, ratio))
            self.glass_btn.set_state("한 잔... (거의 다!)", C_ORANGE)
        else:
            self.face.set_redness(ratio)
            self.glass_btn.set_state("한 잔!", C_GREEN)

    # ── 주량 도달 알람 ──
    def _alarm(self):
        if self._sound:
            try:
                self._sound.loop = True
                self._sound.play()
            except Exception:
                pass
        self._vibrate()

        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        box.add_widget(_lbl("멍! 멍!", fs=32, bold=True, color=C_RED))
        box.add_widget(_lbl(
            f"{self.sel:g}병({self.limit}잔)을\n모두 마셨습니다!\n\n"
            "이제 그만 드세요!",
            fs=16, halign="center",
        ))
        ok = _btn("알림 끄기", fs=18, bg=C_RED,
                  size_hint_y=None, height=dp(50))
        box.add_widget(ok)

        pop = Popup(
            title="", separator_height=0, content=box,
            size_hint=(0.88, 0.50), auto_dismiss=False,
            background_color=(0.05, 0.05, 0.05, 0.97),
        )

        def dismiss(_):
            self._stop_sound()
            pop.dismiss()

        ok.bind(on_release=dismiss)
        pop.open()

    # ── 주량 초과 추가 경고 ──
    def _extra_warning(self):
        if self._sound:
            try:
                self._sound.loop = True
                self._sound.play()
            except Exception:
                pass
        self._vibrate()

        over = self.count - self.limit
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
        box.add_widget(_lbl(
            f"주량 초과! (+{over}잔)\n정말 그만 드세요!",
            fs=20, bold=True, color=C_RED, halign="center",
        ))
        ok = _btn("알림 끄기", fs=16, bg=C_RED,
                  size_hint_y=None, height=dp(44))
        box.add_widget(ok)

        pop = Popup(
            title="", separator_height=0, content=box,
            size_hint=(0.8, 0.35), auto_dismiss=False,
            background_color=(0.05, 0.05, 0.05, 0.95),
        )

        def dismiss(_):
            self._stop_sound()
            pop.dismiss()

        ok.bind(on_release=dismiss)
        pop.open()

    def _vibrate(self):
        try:
            if platform == "android":
                from plyer import vibrator
                vibrator.vibrate(time=2)
        except Exception:
            pass

    # ── 초기화 ──
    def _reset(self, *_):
        if self.sel is None:
            return
        self._stop_sound()
        self.count = 0
        self.alarmed = False
        self.face.reset()
        self._refresh()

    # ── 주량 변경 ──
    def _change(self, *_):
        self._stop_sound()
        self.sel = None
        self.count = 0
        self.alarmed = False
        self.face.reset()
        self.drink_box.opacity = 0
        self.drink_box.disabled = True
        for i, b in enumerate(self._cap_btns.values()):
            b.background_color = CAP_COLORS[i]


# ── App ─────────────────────────────────────────────────────
class SojuTrackerApp(App):
    def build(self):
        self.title = "소주 주량 트래커"
        Window.clearcolor = C_BG
        return SojuTracker()


if __name__ == "__main__":
    SojuTrackerApp().run()
