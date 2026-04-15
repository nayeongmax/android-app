"""
소주 주량 트래커 (Soju Drinking Capacity Tracker)

- 상단에서 주량 선택
- 얼굴이 한 잔마다 점점 빨개짐
- 주량 도달 시 개로 변신 + 알림음 반복
"""

import os
import math
import struct
import wave

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
from kivy.core.text import LabelBase
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.utils import platform

# ── Korean Font ─────────────────────────────────────────────
try:
    _BASE = os.path.dirname(os.path.abspath(__file__))
except Exception:
    _BASE = os.getcwd()

_FONT_PATH = os.path.join(_BASE, "fonts", "NotoSansKR-Regular.ttf")
if os.path.exists(_FONT_PATH):
    LabelBase.register(name="NotoSansKR", fn_regular=_FONT_PATH)
    FONT = "NotoSansKR"
else:
    FONT = "Roboto"

# ── Colors ──────────────────────────────────────────────────
C_BG      = (0.12, 0.12, 0.16, 1)
C_BTN_SEL = (0.30, 0.70, 0.50, 1)
C_TEXT    = (1, 1, 1, 1)
C_DIM     = (0.60, 0.60, 0.68, 1)
C_GREEN   = (0.25, 0.70, 0.45, 1)
C_ORANGE  = (0.92, 0.62, 0.22, 1)
C_RED     = (0.88, 0.28, 0.28, 1)

CAP_COLORS = [
    (0.50, 0.72, 0.90, 1),
    (0.50, 0.80, 0.62, 1),
    (0.88, 0.72, 0.50, 1),
    (0.78, 0.55, 0.78, 1),
    (0.90, 0.60, 0.60, 1),
    (0.60, 0.60, 0.85, 1),
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
def _btn(text, fs=18, bg=(0.25, 0.25, 0.32, 1), color=C_TEXT, bold=False, **kw):
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


# ── Face display (standard widgets only) ───────────────────
class FaceDisplay(BoxLayout):
    """얼굴 표시 - 배경색이 점점 빨개지고 텍스트 표정이 변함"""

    def __init__(self, **kw):
        super().__init__(orientation="vertical", **kw)

        with self.canvas.before:
            self._bg_color = Color(0.18, 0.18, 0.24, 1)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

        # 얼굴 텍스트
        self.face_lbl = Label(
            text="( ^_^ )", font_name=FONT, font_size=sp(52),
            bold=True, color=(1, 1, 1, 1),
            halign="center", valign="middle",
        )
        self.face_lbl.bind(size=self.face_lbl.setter("text_size"))
        self.add_widget(self.face_lbl)

        # 상태 텍스트
        self.status_lbl = Label(
            text="", font_name=FONT, font_size=sp(15),
            color=C_DIM, halign="center",
            size_hint_y=None, height=dp(28),
        )
        self.add_widget(self.status_lbl)

    def _sync(self, *a):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def set_redness(self, ratio):
        r = max(0.0, min(1.0, ratio))

        # 배경색: 점점 빨개짐
        bg_r = 0.18 + r * 0.42
        bg_g = max(0.18 - r * 0.12, 0.06)
        bg_b = max(0.24 - r * 0.18, 0.06)
        self._bg_color.rgba = (bg_r, bg_g, bg_b, 1)

        # 텍스트 색: 점점 붉어짐
        txt_g = max(1.0 - r * 0.5, 0.5)
        txt_b = max(1.0 - r * 0.6, 0.4)

        if r < 0.15:
            self.face_lbl.text = "( ^_^ )"
            self.status_lbl.text = ""
        elif r < 0.35:
            self.face_lbl.text = "( ^o^ )"
            self.status_lbl.text = "기분 좋다~"
            self.face_lbl.color = (1, txt_g, txt_b, 1)
        elif r < 0.55:
            self.face_lbl.text = "( >v< )"
            self.face_lbl.font_size = sp(54)
            self.status_lbl.text = "조금 취했어..."
            self.face_lbl.color = (1, txt_g, txt_b, 1)
        elif r < 0.75:
            self.face_lbl.text = "( >_< )"
            self.face_lbl.font_size = sp(56)
            self.status_lbl.text = "많이 취했어!!"
            self.face_lbl.color = (1, txt_g, txt_b, 1)
        elif r < 0.95:
            self.face_lbl.text = "( @_@ )"
            self.face_lbl.font_size = sp(58)
            self.status_lbl.text = "위험해!! 거의 다 찼어!"
            self.face_lbl.color = (1, txt_g, txt_b, 1)
        else:
            self.face_lbl.text = "( x_x )"
            self.face_lbl.font_size = sp(60)
            self.status_lbl.text = "한계야!!!"
            self.face_lbl.color = (1, 0.4, 0.35, 1)

    def show_dog(self):
        self._bg_color.rgba = (0.35, 0.22, 0.12, 1)
        self.face_lbl.text = "U^.^U"
        self.face_lbl.font_size = sp(60)
        self.face_lbl.color = (1, 0.88, 0.65, 1)
        self.status_lbl.text = "멍멍!! 그만 마셔!!!"
        self.status_lbl.color = C_RED

    def reset(self):
        self._bg_color.rgba = (0.18, 0.18, 0.24, 1)
        self.face_lbl.text = "( ^_^ )"
        self.face_lbl.font_size = sp(52)
        self.face_lbl.color = (1, 1, 1, 1)
        self.status_lbl.text = ""
        self.status_lbl.color = C_DIM


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

        with self.canvas.before:
            Color(*C_BG)
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self._build()

    def _sync_bg(self, *_):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _load_sound(self):
        try:
            # Android/PC 모두 호환되는 경로 찾기
            for d in [_BASE, os.path.join(_BASE, ".cache")]:
                try:
                    os.makedirs(d, exist_ok=True)
                    p = os.path.join(d, "alarm.wav")
                    _make_alarm(p)
                    snd = SoundLoader.load(p)
                    if snd:
                        snd.loop = True
                        return snd
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def _stop_sound(self):
        if self._sound:
            try:
                self._sound.stop()
            except Exception:
                pass

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
        self.add_widget(_lbl(
            "나의 주량을 선택하세요!",
            fs=13, color=C_DIM, size_hint_y=None, height=dp(22),
        ))

        # 주량 선택 버튼 (파스텔 색상)
        grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(90))
        for i, b in enumerate(BOTTLES):
            g = limit_glasses(b)
            btn = _btn(f"{b:g}병\n({g}잔)", fs=13, bg=CAP_COLORS[i])
            btn.halign = "center"
            btn.bind(on_release=lambda _, v=b: self._pick(v))
            self._cap_btns[b] = btn
            grid.add_widget(btn)
        self.add_widget(grid)

        # ── 음주 기록 영역 ──
        self.drink_box = BoxLayout(
            orientation="vertical", spacing=dp(4),
            opacity=0, disabled=True,
        )

        self.info_lbl = _lbl("", fs=13, color=C_DIM,
                             size_hint_y=None, height=dp(22))
        self.drink_box.add_widget(self.info_lbl)

        # 얼굴 표시 영역
        self.face = FaceDisplay(size_hint_y=1)
        self.drink_box.add_widget(self.face)

        # 잔 수
        self.frac_lbl = _lbl("", fs=15, color=C_DIM,
                             size_hint_y=None, height=dp(22))
        self.drink_box.add_widget(self.frac_lbl)

        # 소주잔 버튼 (일반 Button)
        self.drink_btn = _btn(
            "[ ] 한 잔!", fs=22, bold=True, bg=C_GREEN,
            size_hint_y=None, height=dp(62),
        )
        self.drink_btn.bind(on_release=self._drink)
        self.drink_box.add_widget(self.drink_btn)

        # 하단 버튼
        row = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(38))
        rb = _btn("초기화", fs=12, bg=(0.60, 0.30, 0.30, 1))
        rb.bind(on_release=self._reset)
        cb = _btn("주량 변경", fs=12, bg=(0.40, 0.40, 0.55, 1))
        cb.bind(on_release=self._change)
        row.add_widget(rb)
        row.add_widget(cb)
        self.drink_box.add_widget(row)

        self.add_widget(self.drink_box)

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

    def _drink(self, *_):
        if self.sel is None:
            return
        self.count += 1
        self._refresh()
        if self.count >= self.limit and not self.alarmed:
            self.alarmed = True
            Clock.schedule_once(lambda dt: self._alarm(), 0.05)
        elif self.count > self.limit:
            Clock.schedule_once(lambda dt: self._extra_warning(), 0.05)

    def _refresh(self):
        c, lim = self.count, self.limit
        self.info_lbl.text = f"주량: {self.sel:g}병 ({lim}잔)"
        self.frac_lbl.text = f"{c} / {lim} 잔"
        ratio = c / lim if lim else 0

        if c >= lim:
            self.face.show_dog()
            self.drink_btn.text = "그만 드세요!"
            self.drink_btn.background_color = C_RED
        elif c >= lim * 0.7:
            self.face.set_redness(min(1.0, ratio))
            self.drink_btn.text = "[ ] 한 잔... (거의 다!)"
            self.drink_btn.background_color = C_ORANGE
        else:
            self.face.set_redness(ratio)
            self.drink_btn.text = "[ ] 한 잔!"
            self.drink_btn.background_color = C_GREEN

    def _alarm(self):
        if self._sound:
            try:
                self._sound.loop = True
                self._sound.play()
            except Exception:
                pass
        self._vibrate()

        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        box.add_widget(_lbl("U^.^U  멍! 멍!", fs=28, bold=True, color=C_RED))
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

    def _reset(self, *_):
        if self.sel is None:
            return
        self._stop_sound()
        self.count = 0
        self.alarmed = False
        self.face.reset()
        self._refresh()

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


class SojuTrackerApp(App):
    def build(self):
        self.title = "소주 주량 트래커"
        Window.clearcolor = C_BG
        return SojuTracker()


if __name__ == "__main__":
    SojuTrackerApp().run()
