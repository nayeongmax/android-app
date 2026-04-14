"""
소주 주량 트래커 (Soju Drinking Capacity Tracker)

소주를 마실 때 자신의 주량을 넘기지 않도록 도와주는 앱.
- 상단에서 자신의 주량(0.5~3병)을 선택
- 한 잔 마실 때마다 버튼을 터치
- 이미지가 점점 어두워지며 주량 도달 시 블랙아웃 + 알림
- 알림음은 사용자가 끄기 전까지 반복 재생
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
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse
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
GLASSES_PER_BOTTLE = 7.2
BOTTLES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]


def limit_glasses(bottles):
    """주량(병) -> 소주잔 수 (반올림)"""
    return round(bottles * GLASSES_PER_BOTTLE)


# ── Alarm sound ─────────────────────────────────────────────
def _make_alarm(path, freq=880, dur=0.6, sr=44100):
    """짧은 비프음 WAV (루프 재생용)"""
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


# ── Blackout scene widget ──────────────────────────────────
class BlackoutView(Widget):
    """술을 마실수록 어두워지는 소주 장면 (밤거리 + 소주병)"""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.darkness = 0.0
        self.bind(size=self._draw, pos=self._draw)

    def _draw(self, *a):
        self.canvas.clear()
        x, y = self.pos
        w, h = self.size
        if w < 2 or h < 2:
            return
        cx = x + w / 2

        with self.canvas:
            # ── 밤하늘 ──
            Color(0.06, 0.08, 0.22, 1)
            Rectangle(pos=(x, y), size=(w, h))

            # ── 별 ──
            Color(1, 1, 0.9, 0.7)
            sr = dp(2)
            for sx, sy in [
                (0.10, 0.92), (0.25, 0.85), (0.45, 0.95), (0.65, 0.88),
                (0.85, 0.93), (0.15, 0.75), (0.55, 0.80), (0.78, 0.72),
                (0.35, 0.70), (0.92, 0.82), (0.05, 0.60), (0.70, 0.65),
            ]:
                Ellipse(pos=(x + w * sx, y + h * sy), size=(sr, sr))

            # ── 달 ──
            Color(1, 1, 0.75, 0.85)
            ms = min(w, h) * 0.10
            Ellipse(pos=(x + w * 0.78, y + h * 0.86), size=(ms, ms))

            # ── 건물 실루엣 ──
            Color(0.08, 0.08, 0.15, 1)
            for bx, bw, bh in [
                (0.0, 0.13, 0.28), (0.11, 0.11, 0.20), (0.20, 0.15, 0.32),
                (0.33, 0.10, 0.18), (0.41, 0.13, 0.35), (0.52, 0.11, 0.22),
                (0.61, 0.14, 0.28), (0.73, 0.11, 0.25), (0.82, 0.13, 0.30),
                (0.93, 0.10, 0.20),
            ]:
                Rectangle(pos=(x + w * bx, y + h * 0.30), size=(w * bw, h * bh))

            # ── 건물 창문 (불빛) ──
            Color(1, 0.9, 0.4, 0.5)
            wd = dp(3)
            for wx, wy in [
                (0.04, 0.38), (0.06, 0.45), (0.24, 0.40), (0.26, 0.50),
                (0.44, 0.42), (0.46, 0.55), (0.48, 0.48), (0.65, 0.38),
                (0.67, 0.48), (0.86, 0.42), (0.88, 0.50), (0.35, 0.35),
                (0.14, 0.36), (0.75, 0.40), (0.63, 0.45),
            ]:
                Rectangle(pos=(x + w * wx, y + h * wy), size=(wd, wd))

            # ── 포장마차 지붕 ──
            Color(0.85, 0.35, 0.15, 1)
            roof_y = y + h * 0.26
            Rectangle(pos=(x + w * 0.15, roof_y), size=(w * 0.70, h * 0.04))

            # 포장마차 천막 줄무늬
            Color(0.95, 0.50, 0.20, 1)
            for i in range(7):
                stripe_x = x + w * 0.15 + (w * 0.70 / 7) * i
                Rectangle(pos=(stripe_x, roof_y), size=(w * 0.70 / 14, h * 0.04))

            # ── 테이블 ──
            Color(0.50, 0.32, 0.18, 1)
            ty = y + h * 0.10
            Rectangle(pos=(x + w * 0.12, ty), size=(w * 0.76, h * 0.035))
            # 다리
            Color(0.42, 0.26, 0.14, 1)
            Rectangle(pos=(x + w * 0.16, y + h * 0.01), size=(w * 0.035, h * 0.09))
            Rectangle(pos=(x + w * 0.80, y + h * 0.01), size=(w * 0.035, h * 0.09))

            # ── 소주병 (가운데) ──
            bw_ = w * 0.10
            bh_ = h * 0.20
            bx_ = cx - bw_ / 2
            by_ = ty + h * 0.035

            Color(0.20, 0.55, 0.30, 1)
            RoundedRectangle(pos=(bx_, by_), size=(bw_, bh_), radius=[dp(4)])
            # 병목
            nw = bw_ * 0.45
            RoundedRectangle(
                pos=(bx_ + (bw_ - nw) / 2, by_ + bh_),
                size=(nw, h * 0.06), radius=[dp(3)],
            )
            # 병뚜껑
            Color(0.25, 0.65, 0.35, 1)
            cw = nw * 1.2
            Ellipse(
                pos=(bx_ + (bw_ - cw) / 2, by_ + bh_ + h * 0.055),
                size=(cw, dp(5)),
            )
            # 라벨
            Color(1, 1, 1, 0.8)
            lw, lh = bw_ * 0.6, bh_ * 0.22
            Rectangle(
                pos=(bx_ + (bw_ - lw) / 2, by_ + bh_ * 0.32),
                size=(lw, lh),
            )

            # ── 왼쪽 소주잔 ──
            gw, gh = w * 0.065, h * 0.065
            gx_l = cx - w * 0.20
            gy = ty + h * 0.035
            Color(0.75, 0.82, 0.90, 0.55)
            RoundedRectangle(pos=(gx_l, gy), size=(gw, gh), radius=[dp(2)])
            Color(0.80, 0.90, 0.80, 0.35)
            RoundedRectangle(
                pos=(gx_l + dp(2), gy + dp(2)),
                size=(gw - dp(4), gh * 0.5), radius=[dp(2)],
            )

            # ── 오른쪽 소주잔 ──
            gx_r = cx + w * 0.14
            Color(0.75, 0.82, 0.90, 0.55)
            RoundedRectangle(pos=(gx_r, gy), size=(gw, gh), radius=[dp(2)])
            Color(0.80, 0.90, 0.80, 0.35)
            RoundedRectangle(
                pos=(gx_r + dp(2), gy + dp(2)),
                size=(gw - dp(4), gh * 0.5), radius=[dp(2)],
            )

            # ── 안주 접시 (왼쪽) ──
            Color(0.85, 0.85, 0.80, 0.7)
            Ellipse(pos=(cx - w * 0.38, gy + gh * 0.1), size=(w * 0.09, h * 0.03))
            Color(0.75, 0.30, 0.20, 1)  # 김치 색
            Ellipse(pos=(cx - w * 0.37, gy + gh * 0.15), size=(w * 0.03, h * 0.015))
            Ellipse(pos=(cx - w * 0.34, gy + gh * 0.12), size=(w * 0.025, h * 0.015))

            # ── 안주 접시 (오른쪽) ──
            Color(0.85, 0.85, 0.80, 0.7)
            Ellipse(pos=(cx + w * 0.26, gy + gh * 0.1), size=(w * 0.09, h * 0.03))
            Color(0.55, 0.75, 0.35, 1)  # 파 색
            Ellipse(pos=(cx + w * 0.28, gy + gh * 0.12), size=(w * 0.025, h * 0.018))
            Ellipse(pos=(cx + w * 0.31, gy + gh * 0.15), size=(w * 0.02, h * 0.012))

            # ══════════════════════════════════════════════
            #  블랙아웃 오버레이 (점점 어두워짐)
            # ══════════════════════════════════════════════
            Color(0, 0, 0, self.darkness)
            Rectangle(pos=(x, y), size=(w, h))

    def set_darkness(self, ratio):
        """0.0 (맑은 의식) ~ 1.0 (블랙아웃)"""
        self.darkness = max(0.0, min(1.0, ratio))
        self._draw()


# ── Main tracker widget ─────────────────────────────────────
class SojuTracker(BoxLayout):

    def __init__(self, **kw):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(4), **kw)

        self.sel = None        # 선택된 주량 (병)
        self.limit = 0         # 잔 수 한도
        self.count = 0         # 현재 마신 잔 수
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
            "자신의 주량을 선택하세요",
            fs=13, color=C_DIM, size_hint_y=None, height=dp(22),
        ))

        # 주량 선택 버튼 (3x2)
        grid = GridLayout(cols=3, spacing=dp(5), size_hint_y=None, height=dp(90))
        for b in BOTTLES:
            g = limit_glasses(b)
            btn = _btn(f"{b:g}병\n({g}잔)", fs=13)
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
                             size_hint_y=None, height=dp(20))
        self.drink_box.add_widget(self.info_lbl)

        # 블랙아웃 이미지 (유동 크기)
        self.blackout = BlackoutView(size_hint_y=1)
        self.drink_box.add_widget(self.blackout)

        # 잔 수 표시
        self.frac_lbl = _lbl("", fs=14, color=C_DIM,
                             size_hint_y=None, height=dp(20))
        self.drink_box.add_widget(self.frac_lbl)

        # 한 잔 버튼
        self.drink_btn = _btn(
            "한 잔!", fs=24, bold=True, bg=C_GREEN,
            size_hint_y=None, height=dp(60),
        )
        self.drink_btn.bind(on_release=self._drink)
        self.drink_box.add_widget(self.drink_btn)

        # 하단 버튼 (초기화 / 주량 변경)
        row = BoxLayout(spacing=dp(5), size_hint_y=None, height=dp(38))
        rb = _btn("초기화", fs=12, bg=(0.4, 0.18, 0.18, 1))
        rb.bind(on_release=self._reset)
        cb = _btn("주량 변경", fs=12)
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
        for v, b in self._cap_btns.items():
            b.background_color = C_BTN_SEL if v == bottles else C_BTN
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
            self.alarmed = True
            Clock.schedule_once(lambda dt: self._alarm(), 0.05)
        elif self.count > self.limit:
            Clock.schedule_once(lambda dt: self._extra_warning(), 0.05)

    # ── 화면 갱신 ──
    def _refresh(self):
        c, lim = self.count, self.limit
        self.info_lbl.text = f"주량: {self.sel:g}병 ({lim}잔)"
        self.frac_lbl.text = f"{c} / {lim} 잔"

        # 블랙아웃 효과: 마신 비율만큼 어두워짐
        ratio = c / lim if lim else 0
        self.blackout.set_darkness(min(1.0, ratio))

        # 버튼 색상 변경
        if c >= lim:
            self.drink_btn.background_color = C_RED
            self.drink_btn.text = "그만 드세요!"
        elif c >= lim * 0.7:
            self.drink_btn.background_color = C_ORANGE
            self.drink_btn.text = "한 잔... (거의 다 찼어요!)"
        else:
            self.drink_btn.background_color = C_GREEN
            self.drink_btn.text = "한 잔!"

    # ── 주량 도달 알람 (블랙아웃!) ──
    def _alarm(self):
        if self._sound:
            try:
                self._sound.loop = True
                self._sound.play()
            except Exception:
                pass
        self._vibrate()

        box = BoxLayout(orientation="vertical", spacing=dp(12), padding=dp(16))
        box.add_widget(_lbl(
            "BLACKOUT!", fs=32, bold=True, color=C_RED,
        ))
        box.add_widget(_lbl(
            f"{self.sel:g}병({self.limit}잔)을\n모두 마셨습니다!\n\n"
            "건강을 위해\n이제 그만 드세요!",
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
        self._refresh()

    # ── 주량 변경 ──
    def _change(self, *_):
        self._stop_sound()
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
