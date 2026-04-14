"""
소주 주량 트래커 (Soju Drinking Capacity Tracker)

소주를 마실 때 자신의 주량을 넘기지 않도록 도와주는 앱.
- 상단에서 자신의 주량(0.5~3병)을 선택
- 자기 얼굴 사진을 추가
- 한 잔 마실 때마다 사진이 점점 어두워짐 (블랙아웃)
- 주량 도달 시 사진 완전 암전 + 알림음 반복
"""

import os
import math
import struct
import wave
import shutil
import tempfile

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.image import Image as KivyImage
from kivy.uix.filechooser import FileChooserListView
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
GLASSES_PER_BOTTLE = 7.2
BOTTLES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]

# ── App data directory ──────────────────────────────────────
_APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".appdata")
os.makedirs(_APP_DIR, exist_ok=True)
_SAVED_PHOTO = os.path.join(_APP_DIR, "my_photo.jpg")


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


# ── Photo + Blackout overlay widget ────────────────────────
class PhotoBlackoutView(RelativeLayout):
    """사용자 사진 위에 블랙아웃 오버레이를 그리는 위젯"""

    def __init__(self, on_tap=None, **kw):
        super().__init__(**kw)
        self.darkness = 0.0
        self._on_tap = on_tap

        # 배경 (사진 없을 때 보이는 색)
        with self.canvas.before:
            Color(0.15, 0.15, 0.20, 1)
            self._bg = Rectangle(pos=self.pos, size=self.size)

        # 플레이스홀더 텍스트
        self.placeholder = Label(
            text="여기를 터치하여\n사진을 추가하세요",
            font_name=FONT, font_size=sp(15),
            color=C_DIM, halign="center", valign="middle",
        )
        self.placeholder.bind(size=self.placeholder.setter("text_size"))
        self.add_widget(self.placeholder)

        # 사진 이미지
        self.img = KivyImage(allow_stretch=True, keep_ratio=True)
        self.img.opacity = 0
        self.add_widget(self.img)

        # 블랙아웃 오버레이 (canvas.after = 자식 위에 그려짐)
        with self.canvas.after:
            self._ov_color = Color(0, 0, 0, 0)
            self._ov_rect = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *a):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._ov_rect.pos = self.pos
        self._ov_rect.size = self.size

    def on_touch_down(self, touch):
        if self.disabled:
            return False
        if self.collide_point(*touch.pos) and self._on_tap:
            self._on_tap()
            return True
        return super().on_touch_down(touch)

    def set_photo(self, path):
        self.img.source = path
        self.img.reload()
        self.img.opacity = 1
        self.placeholder.opacity = 0

    def has_photo(self):
        return self.img.opacity > 0

    def set_darkness(self, ratio):
        self.darkness = max(0.0, min(1.0, ratio))
        self._ov_color.a = self.darkness


# ── Main tracker widget ─────────────────────────────────────
class SojuTracker(BoxLayout):

    def __init__(self, **kw):
        # Android 상태바 높이만큼 상단 패딩 추가
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

        # 이전에 저장된 사진이 있으면 자동 로드
        if os.path.exists(_SAVED_PHOTO):
            Clock.schedule_once(lambda dt: self.blackout.set_photo(_SAVED_PHOTO), 0.1)

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

        # 주량 정보 + 사진 추가 버튼
        info_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(5))
        self.info_lbl = _lbl("", fs=13, color=C_DIM)
        photo_btn = _btn("사진 추가", fs=11, bg=(0.30, 0.30, 0.45, 1),
                         size_hint_x=0.35)
        photo_btn.bind(on_release=lambda _: self._open_photo_picker())
        info_row.add_widget(self.info_lbl)
        info_row.add_widget(photo_btn)
        self.drink_box.add_widget(info_row)

        # 사진 + 블랙아웃 뷰 (터치로도 사진 추가 가능)
        self.blackout = PhotoBlackoutView(
            on_tap=self._open_photo_picker,
            size_hint_y=1,
        )
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

    # ── 사진 선택 ──
    def _open_photo_picker(self):
        if platform == "android":
            self._open_android_gallery()
        else:
            self._open_desktop_picker()

    def _open_android_gallery(self):
        """Android 시스템 갤러리에서 사진 선택 (썸네일 표시됨)"""
        try:
            from jnius import autoclass, cast
            from android import activity as android_activity

            Intent = autoclass("android.content.Intent")
            MediaStore = autoclass("android.provider.MediaStore$Images$Media")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            # ACTION_PICK + MediaStore URI → 갤러리 앱이 직접 열림
            intent = Intent(Intent.ACTION_PICK, MediaStore.EXTERNAL_CONTENT_URI)

            android_activity.bind(on_activity_result=self._on_photo_result)

            current = cast("android.app.Activity", PythonActivity.mActivity)
            current.startActivityForResult(intent, 1001)
        except Exception as e:
            # 갤러리 실패 시 에러 팝업 표시
            box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(12))
            box.add_widget(_lbl(
                f"갤러리를 열 수 없습니다\n\n{e}",
                fs=14, color=C_RED, halign="center",
            ))
            ok = _btn("확인", fs=14, bg=C_BTN, size_hint_y=None, height=dp(40))
            box.add_widget(ok)
            pop = Popup(title="오류", title_font=FONT, content=box,
                        size_hint=(0.85, 0.35))
            ok.bind(on_release=pop.dismiss)
            pop.open()

    def _on_photo_result(self, request_code, result_code, intent):
        """Android 갤러리 선택 결과 처리"""
        try:
            from android import activity as android_activity
            android_activity.unbind(on_activity_result=self._on_photo_result)
        except Exception:
            pass

        if request_code != 1001 or intent is None:
            return

        try:
            from jnius import autoclass
            Activity = autoclass("android.app.Activity")
            if result_code != Activity.RESULT_OK:
                return

            uri = intent.getData()
            if uri is None:
                return

            Clock.schedule_once(lambda dt: self._copy_uri_image(uri), 0)
        except Exception:
            pass

    def _copy_uri_image(self, uri):
        """Content URI에서 이미지를 앱 저장소로 복사"""
        dest = os.path.join(_APP_DIR, "my_photo.jpg")

        try:
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            context = PythonActivity.mActivity
            resolver = context.getContentResolver()

            # ParcelFileDescriptor로 효율적 복사
            pfd = resolver.openFileDescriptor(uri, "r")
            fd = pfd.detachFd()

            with os.fdopen(fd, "rb") as src:
                with open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)

            global _SAVED_PHOTO
            _SAVED_PHOTO = dest
            self.blackout.set_photo(dest)
        except Exception:
            # Fallback: InputStream으로 바이트 복사
            try:
                from jnius import autoclass
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                context = PythonActivity.mActivity
                istream = context.getContentResolver().openInputStream(uri)

                BufferedInputStream = autoclass("java.io.BufferedInputStream")
                bis = BufferedInputStream(istream, 16384)
                data = bytearray()
                while True:
                    b = bis.read()
                    if b == -1:
                        break
                    data.append(b & 0xFF)
                bis.close()
                istream.close()

                with open(dest, "wb") as f:
                    f.write(data)

                _SAVED_PHOTO = dest
                self.blackout.set_photo(dest)
            except Exception:
                pass

    def _open_desktop_picker(self):
        """데스크탑용 파일 선택기"""
        content = BoxLayout(orientation="vertical", spacing=dp(5))

        fc = FileChooserListView(
            filters=["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"],
            path=os.path.expanduser("~"),
        )
        content.add_widget(fc)

        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(5))
        sel_btn = _btn("선택", fs=15, bg=C_GREEN)
        cancel_btn = _btn("취소", fs=15, bg=(0.4, 0.18, 0.18, 1))
        btn_row.add_widget(sel_btn)
        btn_row.add_widget(cancel_btn)
        content.add_widget(btn_row)

        pop = Popup(
            title="사진을 선택하세요",
            title_font=FONT, title_size=sp(16),
            content=content,
            size_hint=(0.95, 0.85),
        )

        def on_select(_):
            if fc.selection:
                self._save_and_set_photo(fc.selection[0])
            pop.dismiss()

        sel_btn.bind(on_release=on_select)
        cancel_btn.bind(on_release=pop.dismiss)
        pop.open()

    def _save_and_set_photo(self, src_path):
        """선택한 사진을 앱 저장소에 복사 후 표시"""
        try:
            ext = os.path.splitext(src_path)[1] or ".jpg"
            dest = os.path.join(_APP_DIR, "my_photo" + ext)
            shutil.copy2(src_path, dest)
            # 기존 다른 확장자 파일 정리
            global _SAVED_PHOTO
            _SAVED_PHOTO = dest
            self.blackout.set_photo(dest)
        except Exception:
            self.blackout.set_photo(src_path)

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

        # 블랙아웃 효과
        ratio = c / lim if lim else 0
        self.blackout.set_darkness(min(1.0, ratio))

        # 버튼 색상
        if c >= lim:
            self.drink_btn.background_color = C_RED
            self.drink_btn.text = "그만 드세요!"
        elif c >= lim * 0.7:
            self.drink_btn.background_color = C_ORANGE
            self.drink_btn.text = "한 잔... (거의 다 찼어요!)"
        else:
            self.drink_btn.background_color = C_GREEN
            self.drink_btn.text = "한 잔!"

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
