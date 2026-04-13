"""
소주 주량 트래커 (Soju Drinking Capacity Tracker)

소주를 마실 때 자신의 주량을 넘기지 않도록 도와주는 앱.
- 상단에서 자신의 주량(0.5~3병)을 선택
- 한 잔 마실 때마다 버튼을 터치
- 주량에 도달하면 알림음과 함께 경고
"""

import os
import math
import struct
import wave
import tempfile

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.graphics import Color, Rectangle
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

# ── Colors (dark theme) ────────────────────────────────────
C_BG      = (0.08, 0.08, 0.11, 1)
C_BTN     = (0.20, 0.20, 0.26, 1)
C_BTN_SEL = (0.22, 0.48, 0.82, 1)
C_TEXT    = (1, 1, 1, 1)
C_DIM     = (0.55, 0.55, 0.60, 1)
C_GREEN   = (0.18, 0.75, 0.43, 1)
C_ORANGE  = (0.95, 0.65, 0.12, 1)
C_RED     = (0.88, 0.22, 0.22, 1)

# ── Soju math ───────────────────────────────────────────────
# 소주 1병(360ml) = 유리 소주잔(50ml) 기준 7.2잔
GLASSES_PER_BOTTLE = 7.2
BOTTLES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def limit_glasses(bottles):
    """주량(병) -> 소주잔 수 (반올림)"""
    return round(bottles * GLASSES_PER_BOTTLE)


# ── Alarm sound (generated at runtime) ──────────────────────
def _make_alarm(path, freq=880, dur=1.5, sr=44100):
    """비프음 WAV 파일 생성"""
    n = int(sr * dur)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            t = i / sr
            # 0.18초 ON / 0.17초 OFF 반복 패턴
            env = 0.8 if (t % 0.35) < 0.18 else 0.0
            s = int(32767 * env * math.sin(2 * math.pi * freq * t))
            frames += struct.pack("<h", max(-32768, min(32767, s)))
        w.writeframes(bytes(frames))


# ── UI helpers ──────────────────────────────────────────────
def _btn(text, fs=18, bg=C_BTN, color=C_TEXT, bold=False, **kw):
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


# ── Main tracker widget ────────────────────────────────────
class SojuTracker(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=dp(16), spacing=dp(10), **kw)

        # State
        self.sel = None        # 선택된 주량 (병)
        self.limit = 0         # 잔 수 한도
        self.count = 0         # 현재 마신 잔 수
        self.alarmed = False   # 알람 발생 여부
        self._cap_btns = {}

        # Alarm sound
        self._sound = self._load_sound()

        # Background
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
            return SoundLoader.load(p)
        except Exception:
            return None

    # ── UI 구성 ──
    def _build(self):
        # 제목
        self.add_widget(_lbl(
            "소주 주량 트래커", fs=28, bold=True,
            size_hint_y=None, height=dp(44),
        ))
        self.add_widget(_lbl(
            "1병(360ml) = 소주잔(50ml) x 7.2잔",
            fs=12, color=C_DIM, size_hint_y=None, height=dp(22),
        ))

        # 주량 선택 안내
        self.add_widget(_lbl(
            "자신의 주량을 선택하세요",
            fs=15, color=C_DIM, size_hint_y=None, height=dp(30),
        ))

        # 주량 선택 버튼 (3x2 그리드)
        grid = GridLayout(cols=3, spacing=dp(8), size_hint_y=None, height=dp(120))
        for b in BOTTLES:
            g = limit_glasses(b)
            btn = _btn(f"{b:g}병\n({g}잔)", fs=15)
            btn.halign = "center"
            btn.bind(on_release=lambda _, v=b: self._pick(v))
            self._cap_btns[b] = btn
            grid.add_widget(btn)
        self.add_widget(grid)

        # 음주 기록 영역 (선택 전에는 숨김)
        self.drink_box = BoxLayout(
            orientation="vertical", spacing=dp(10),
            opacity=0, disabled=True,
        )

        # 주량 정보 라벨
        self.info_lbl = _lbl("", fs=15, color=C_DIM,
                             size_hint_y=None, height=dp(26))
        self.drink_box.add_widget(self.info_lbl)

        # 큰 숫자 카운트
        self.cnt_lbl = _lbl("0", fs=90, bold=True, color=C_GREEN)
        self.drink_box.add_widget(self.cnt_lbl)

        # n / limit 잔 표시
        self.frac_lbl = _lbl("", fs=17, color=C_DIM,
                             size_hint_y=None, height=dp(26))
        self.drink_box.add_widget(self.frac_lbl)

        # 진행 바
        self.prog = ProgressBar(max=100, value=0,
                                size_hint_y=None, height=dp(18))
        self.drink_box.add_widget(self.prog)

        # 한 잔 버튼 (크게!)
        self.drink_btn = _btn(
            "한 잔!", fs=30, bold=True, bg=C_GREEN,
            size_hint_y=None, height=dp(90),
        )
        self.drink_btn.bind(on_release=self._drink)
        self.drink_box.add_widget(self.drink_btn)

        # 하단 버튼 (초기화 / 주량 변경)
        row = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(46))
        rb = _btn("초기화", fs=14, bg=(0.4, 0.18, 0.18, 1))
        rb.bind(on_release=self._reset)
        cb = _btn("주량 변경", fs=14)
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

        # 선택된 버튼 하이라이트
        for v, b in self._cap_btns.items():
            b.background_color = C_BTN_SEL if v == bottles else C_BTN

        # 음주 기록 영역 표시
        self.drink_box.opacity = 1
        self.drink_box.disabled = False
        self._refresh()

    # ── 한 잔 마심 ──
    def _drink(self, *_):
        if self.sel is None:
            return
        self.count += 1
        self._refresh()

        if self.count >= self.limit and not self.alarmed:
            # 주량 도달 -> 첫 알람
            self.alarmed = True
            Clock.schedule_once(lambda dt: self._alarm(), 0.05)
        elif self.count > self.limit:
            # 주량 초과 -> 추가 경고
            Clock.schedule_once(lambda dt: self._extra_warning(), 0.05)

    # ── 화면 갱신 ──
    def _refresh(self):
        c, lim = self.count, self.limit

        self.info_lbl.text = f"주량: {self.sel:g}병 ({lim}잔)"
        self.cnt_lbl.text = str(c)
        self.frac_lbl.text = f"{c} / {lim} 잔"
        self.prog.value = min(c / lim * 100, 100) if lim else 0

        # 상태별 색상 변경
        if c >= lim:
            self.cnt_lbl.color = C_RED
            self.drink_btn.background_color = C_RED
            self.drink_btn.text = "그만 드세요!"
        elif c >= lim * 0.7:
            self.cnt_lbl.color = C_ORANGE
            self.drink_btn.background_color = C_ORANGE
            self.drink_btn.text = "한 잔... (거의 다 찼어요!)"
        else:
            self.cnt_lbl.color = C_GREEN
            self.drink_btn.background_color = C_GREEN
            self.drink_btn.text = "한 잔!"

    # ── 주량 도달 알람 ──
    def _alarm(self):
        self._play_sound()
        self._vibrate()

        box = BoxLayout(orientation="vertical", spacing=dp(14), padding=dp(20))
        box.add_widget(_lbl(
            "주량 도달!", fs=30, bold=True, color=C_RED,
        ))
        box.add_widget(_lbl(
            f"{self.sel:g}병({self.limit}잔)을\n모두 마셨습니다!\n\n"
            "건강을 위해\n이제 그만 드세요!",
            fs=18, halign="center",
        ))
        ok = _btn("알겠습니다", fs=18, bg=C_RED,
                  size_hint_y=None, height=dp(50))
        box.add_widget(ok)

        pop = Popup(
            title="", separator_height=0, content=box,
            size_hint=(0.88, 0.55), auto_dismiss=False,
            background_color=(0.05, 0.05, 0.05, 0.97),
        )
        ok.bind(on_release=pop.dismiss)
        pop.open()

    # ── 주량 초과 추가 경고 ──
    def _extra_warning(self):
        self._play_sound()
        self._vibrate()

        over = self.count - self.limit
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(16))
        box.add_widget(_lbl(
            f"주량 초과! (+{over}잔)\n정말 그만 드세요!",
            fs=20, bold=True, color=C_RED, halign="center",
        ))
        ok = _btn("네...", fs=16, bg=C_RED,
                  size_hint_y=None, height=dp(44))
        box.add_widget(ok)

        pop = Popup(
            title="", separator_height=0, content=box,
            size_hint=(0.8, 0.35), auto_dismiss=True,
            background_color=(0.05, 0.05, 0.05, 0.95),
        )
        ok.bind(on_release=pop.dismiss)
        pop.open()

    def _play_sound(self):
        if self._sound:
            try:
                self._sound.play()
            except Exception:
                pass

    def _vibrate(self):
        try:
            if platform == "android":
                from plyer import vibrator
                vibrator.vibrate(time=1)
        except Exception:
            pass

    # ── 초기화 ──
    def _reset(self, *_):
        if self.sel is None:
            return
        self.count = 0
        self.alarmed = False
        self._refresh()

    # ── 주량 변경 ──
    def _change(self, *_):
        self.sel = None
        self.count = 0
        self.alarmed = False
        self.drink_box.opacity = 0
        self.drink_box.disabled = True
        for b in self._cap_btns.values():
            b.background_color = C_BTN


# ── App ─────────────────────────────────────────────────────
class SojuTrackerApp(App):
    def build(self):
        self.title = "소주 주량 트래커"
        Window.clearcolor = C_BG
        return SojuTracker()


if __name__ == "__main__":
    SojuTrackerApp().run()
