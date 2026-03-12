"""
현장 횡단면 실측 도면 작성 프로그램 - Android (Kivy)

★ 핵심: matplotlib를 모듈 레벨에서 import하지 않음
  Android에서 앱 시작 전 matplotlib import 시 font cache,
  native library 초기화 과정에서 크래시 발생하므로
  실제 그리기 시점까지 import를 완전히 지연함
"""
import os
import io
import sys
import platform
import traceback

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserListView
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.logger import Logger


# =====================================================
# matplotlib 완전 지연 로딩 시스템
# =====================================================
_mpl_plt = None
_mpl_fm = None
_mpl_initialized = False
_mpl_error = None


def _get_safe_config_dir():
    """matplotlib 설정 디렉토리를 안전하게 결정"""
    candidates = []

    # 1) Android 앱 전용 저장소
    try:
        from android.storage import app_storage_path
        candidates.append(os.path.join(app_storage_path(), '.matplotlib'))
    except Exception:
        pass

    # 2) 앱 실행 디렉토리
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(app_dir, '.matplotlib'))
    except Exception:
        pass

    # 3) 홈 디렉토리
    try:
        candidates.append(os.path.join(os.path.expanduser('~'), '.matplotlib'))
    except Exception:
        pass

    # 4) 기타 폴백
    candidates.extend([
        '/data/local/tmp/.matplotlib',
        '/tmp/.matplotlib',
    ])

    for config_dir in candidates:
        try:
            parent = os.path.dirname(config_dir)
            if os.path.isdir(parent):
                os.makedirs(config_dir, exist_ok=True)
                # 쓰기 가능 테스트
                test_file = os.path.join(config_dir, '.test')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return config_dir
        except Exception:
            continue

    return '.'


def _init_matplotlib():
    """matplotlib를 최초 사용 시점에 안전하게 초기화"""
    global _mpl_plt, _mpl_fm, _mpl_initialized, _mpl_error

    if _mpl_initialized:
        return _mpl_error is None

    _mpl_initialized = True

    try:
        Logger.info('MPL: matplotlib 초기화 시작...')

        # 환경변수 설정 (import 전에 반드시)
        config_dir = _get_safe_config_dir()
        os.environ['MPLCONFIGDIR'] = config_dir
        os.environ['MPLBACKEND'] = 'Agg'
        Logger.info(f'MPL: MPLCONFIGDIR = {config_dir}')

        # matplotlib import
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        # 한국어 폰트 설정
        _setup_font(plt, fm)

        _mpl_plt = plt
        _mpl_fm = fm
        Logger.info('MPL: matplotlib 초기화 성공')
        return True

    except Exception as e:
        _mpl_error = str(e)
        Logger.error(f'MPL: matplotlib 초기화 실패: {e}')
        Logger.error(traceback.format_exc())
        return False


def _setup_font(plt, fm):
    """한국어 폰트 설정"""
    try:
        system = platform.system()
        if system == 'Windows':
            plt.rcParams['font.family'] = 'Malgun Gothic'
        elif system == 'Darwin':
            plt.rcParams['font.family'] = 'AppleGothic'
        else:
            android_fonts = [
                '/system/fonts/NotoSansCJK-Regular.ttc',
                '/system/fonts/NotoSansCJKkr-Regular.otf',
                '/system/fonts/NotoSansCJKjp-Regular.otf',
                '/system/fonts/DroidSansFallback.ttf',
                '/system/fonts/Roboto-Regular.ttf',
            ]
            for font_path in android_fonts:
                if os.path.exists(font_path):
                    try:
                        prop = fm.FontProperties(fname=font_path)
                        plt.rcParams['font.family'] = prop.get_name()
                        break
                    except Exception:
                        continue
            else:
                plt.rcParams['font.family'] = 'sans-serif'
    except Exception:
        pass
    plt.rcParams['axes.unicode_minus'] = False


# =====================================================
# 앱 데이터
# =====================================================
DEFAULT_DATA = [
    ["좌측경계",   -8000,   500, "용지경계"],
    ["좌측법면끝",  2500,  -500, ""],
    ["좌측측구",    700,  -400, "U형측구"],
    ["좌측길어깨",  800,   400, ""],
    ["좌측차로끝", 2500,     0, ""],
    ["도로중심",   1500,     0, "기준점"],
    ["우측차로끝", 1500,     0, ""],
    ["우측길어깨", 2500,     0, ""],
    ["우측측구",    800,  -400, "U형측구"],
    ["우측법면끝",  700,   400, ""],
    ["우측경계",   2500,   500, "용지경계"],
]

PRESET_NAMES = ["도로중심", "차도끝", "길어깨끝", "측구", "다이크",
                "법면시작", "법면끝", "용지경계", "수로", "소단"]


class AppData:
    table_data = [list(row) for row in DEFAULT_DATA]
    sections   = [{'image': None, 'photos': [], 'photo_idx': 0} for _ in range(10)]
    current_no = 0
    opt_labels = True
    opt_dims   = True
    opt_grid   = True
    opt_hatch  = True
    unit       = 'mm'
    title_text = '횡단면도'


# =====================================================
# UI 테마 색상
# =====================================================
BG_DARK      = (0.10, 0.12, 0.16, 1)
BG_PANEL     = (0.16, 0.18, 0.24, 1)
BG_ROW_ODD   = (0.20, 0.22, 0.28, 1)
BG_ROW_EVEN  = (0.17, 0.19, 0.25, 1)
BG_ROW_SEL   = (0.22, 0.42, 0.72, 1)
COLOR_BTN    = (0.22, 0.48, 0.82, 1)
COLOR_GREEN  = (0.22, 0.62, 0.32, 1)
COLOR_RED    = (0.72, 0.22, 0.22, 1)
COLOR_TEXT   = (0.95, 0.95, 0.95, 1)
COLOR_HINT   = (0.52, 0.62, 0.78, 1)
COLOR_FIELD  = (0.22, 0.24, 0.30, 1)


# =====================================================
# UI 헬퍼 함수
# =====================================================
def mk_btn(text, clr=None, h=None, **kw):
    return Button(
        text=text,
        size_hint_y=None,
        height=h or dp(44),
        background_normal='',
        background_color=clr or COLOR_BTN,
        color=COLOR_TEXT,
        font_size=sp(14),
        **kw
    )


def mk_lbl(text, **kw):
    return Label(text=text, color=COLOR_TEXT, **kw)


def bg_rect(widget, color):
    with widget.canvas.before:
        Color(*color)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(
        pos=lambda w, v: setattr(rect, 'pos', v),
        size=lambda w, v: setattr(rect, 'size', v),
    )
    return rect


def mk_input(hint='', **kw):
    return TextInput(
        hint_text=hint, multiline=False,
        background_color=COLOR_FIELD,
        foreground_color=COLOR_TEXT,
        hint_text_color=COLOR_HINT,
        font_size=sp(14),
        **kw
    )


def popup_msg(title, msg):
    content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
    content.add_widget(Label(text=msg, color=COLOR_TEXT, halign='center',
                             text_size=(Window.width * 0.75, None)))
    p = Popup(title=title, content=content, size_hint=(0.85, 0.35),
              title_color=COLOR_TEXT, separator_color=COLOR_BTN,
              background='', background_color=(0.13, 0.15, 0.20, 0.97))
    btn = mk_btn("확인", h=dp(42))
    btn.bind(on_press=p.dismiss)
    content.add_widget(btn)
    p.open()


def popup_confirm(title, msg, on_yes):
    content = BoxLayout(orientation='vertical', padding=dp(12), spacing=dp(10))
    content.add_widget(Label(text=msg, color=COLOR_TEXT, halign='center',
                             text_size=(Window.width * 0.75, None)))
    btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
    p = Popup(title=title, content=content, size_hint=(0.85, 0.38),
              title_color=COLOR_TEXT, separator_color=COLOR_RED,
              background='', background_color=(0.13, 0.15, 0.20, 0.97))
    yes = mk_btn("예", clr=COLOR_RED, h=dp(40))
    no  = mk_btn("아니오", h=dp(40))
    yes.bind(on_press=lambda _: (on_yes(), p.dismiss()))
    no.bind(on_press=p.dismiss)
    btns.add_widget(yes)
    btns.add_widget(no)
    content.add_widget(btns)
    p.open()


def get_save_dir():
    try:
        from android.storage import primary_external_storage_path
        ext = primary_external_storage_path()
        dl = os.path.join(ext, 'Download')
        if os.path.isdir(dl):
            return dl
        if os.path.isdir(ext):
            return ext
    except Exception:
        pass
    for d in ['/sdcard/Download', '/storage/emulated/0/Download',
              os.path.expanduser('~'), '/tmp', '.']:
        if os.path.isdir(d):
            return d
    return '.'


# =====================================================
# 데이터 처리
# =====================================================
def get_points():
    pts = []
    cum_l, cum_h = 0.0, 0.0
    prev_dl = 0.0
    for row in AppData.table_data:
        try:
            dl, dh = float(row[1]), float(row[2])
        except (ValueError, IndexError):
            continue
        if row[0] == '도로중심' and dl == 0 and prev_dl > 0:
            cum_l += prev_dl
        else:
            cum_l += dl
        cum_h += dh
        pts.append({'name': row[0], 'l': cum_l, 'h': cum_h,
                    'note': row[3] if len(row) > 3 else ''})
        prev_dl = dl
    center = next((p for p in pts if p['name'] == '도로중심'), None)
    if center:
        offset = center['l']
        for p in pts:
            p['l'] -= offset
    return pts


# =====================================================
# matplotlib 렌더링 (lazy import 사용)
# =====================================================
def place_labels(ax, xs, ys, names, x_span, y_span):
    char_w = x_span * 0.013
    level_right = {}
    for x, y, name in zip(xs, ys, names):
        if not name:
            continue
        hw = char_w * len(name) / 2
        chosen = 7
        for lvl in range(8):
            if x - hw > level_right.get(lvl, -float('inf')) + char_w * 0.5:
                chosen = lvl
                break
        level_right[chosen] = x + hw
        offset_pts = 10 + chosen * 17
        arrow_kw = dict(arrowstyle='-', color='#BBBBBB', lw=0.6) if chosen > 0 else None
        ax.annotate(name, xy=(x, y), xytext=(0, offset_pts),
                    textcoords='offset points', ha='center', va='bottom', fontsize=7.5,
                    arrowprops=arrow_kw,
                    bbox=dict(boxstyle='round,pad=0.25', fc='white',
                              ec='#AAAAAA', alpha=0.88, lw=0.6), zorder=7)


def draw_dims(ax, xs, ys, s, unit, x_span, y_span, ground_bottom):
    fmt = (lambda v: f"{v/s:+,.0f}") if unit == 'mm' else (lambda v: f"{v:+.3f}")
    for x, y in zip(xs, ys):
        if abs(y) < 1e-9:
            continue
        clr = '#CC0000' if y > 0 else '#0044CC'
        ax.annotate('', xy=(x, y), xytext=(x, 0),
                    arrowprops=dict(arrowstyle='<->', color=clr, lw=0.9,
                                    shrinkA=0, shrinkB=0), zorder=6)
        ax.text(x + x_span * 0.012, y / 2,
                fmt(y) + (' mm' if unit == 'mm' else ' m'),
                fontsize=7, color=clr, va='center', zorder=6)
    dim_y  = ground_bottom + y_span * 0.06
    tick_h = y_span * 0.03
    for i in range(len(xs) - 1):
        x0, x1 = xs[i], xs[i + 1]
        ax.annotate('', xy=(x1, dim_y), xytext=(x0, dim_y),
                    arrowprops=dict(arrowstyle='<->', color='#333', lw=0.8,
                                    shrinkA=0, shrinkB=0), zorder=6)
        for xp in (x0, x1):
            ax.plot([xp, xp], [dim_y - tick_h, dim_y + tick_h],
                    color='#333', lw=0.8, zorder=6)
        dist = x1 - x0
        ax.text(x1, dim_y + tick_h * 2.2,
                f"{dist/s:,.0f}" if unit == 'mm' else f"{dist:.3f}",
                ha='center', fontsize=7, color='#222', zorder=6)
    top_y = max(ys) + y_span * 0.30
    ax.annotate('', xy=(xs[-1], top_y), xytext=(xs[0], top_y),
                arrowprops=dict(arrowstyle='<->', color='darkblue', lw=1.1,
                                shrinkA=0, shrinkB=0), zorder=6)
    total = xs[-1] - xs[0]
    ax.text((xs[0] + xs[-1]) / 2, top_y + y_span * 0.04,
            f"전체폭  {total/s:,.0f} mm" if unit == 'mm' else f"전체폭  {total:.3f} m",
            ha='center', fontsize=9, color='darkblue', fontweight='bold', zorder=6)


def render_figure(pts, no_idx, to_file=None, dpi=120):
    """도면 렌더링 - 이 함수에서 최초 matplotlib import 발생"""
    # ★ lazy import: 최초 호출 시에만 matplotlib 로드
    if not _init_matplotlib():
        raise RuntimeError(f"matplotlib 로드 실패: {_mpl_error}")

    plt = _mpl_plt

    unit = AppData.unit
    s    = 0.001 if unit == 'm' else 1.0
    xs   = [p['l'] * s for p in pts]
    ys   = [p['h'] * s for p in pts]
    names = [p['name'] for p in pts]

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    y_span = max(ymax - ymin, 100 * s)
    x_span = xmax - xmin
    ground_bottom = ymin - y_span * 0.35

    fig = plt.figure(figsize=(10, 7.5), facecolor='white')
    gs  = fig.add_gridspec(2, 1, height_ratios=[11, 1], hspace=0.45)
    ax  = fig.add_subplot(gs[0])
    ax_l = fig.add_subplot(gs[1])
    ax_l.axis('off')

    if AppData.opt_hatch:
        ax.fill_between(xs, ground_bottom, ys, color='#C8A96E', alpha=0.55, zorder=1)
        ax.fill_between(xs, ground_bottom - y_span * 0.05, ground_bottom,
                        color='#8B6914', alpha=0.35, zorder=1)

    road_xs = [x for x, y in zip(xs, ys) if abs(y) < 1e-6]
    if len(road_xs) >= 2:
        pave_t = y_span * 0.04
        ax.fill_between([min(road_xs), max(road_xs)], [-pave_t, -pave_t], [0, 0],
                        color='#3A3A3A', alpha=0.85, zorder=2, label='도로 포장면')

    ax.plot(xs, ys, color='#222222', lw=2.5, zorder=4, label='현황지반선')
    ax.plot(xs, ys, 'ko', ms=5, zorder=5)
    ax.axvline(0, color='red', ls='--', lw=1.2, alpha=0.7, label='도로중심선')
    ax.axhline(0, color='royalblue', ls=':', lw=1, alpha=0.6, label='기준고 (H=0)')

    if AppData.opt_labels:
        place_labels(ax, xs, ys, names, x_span, y_span)
    if AppData.opt_dims:
        draw_dims(ax, xs, ys, s, unit, x_span, y_span, ground_bottom)

    xm     = x_span * 0.06
    ym_top = y_span * 0.72
    ax.set_xlim(xmin - xm, xmax + xm)
    ax.set_ylim(ground_bottom - y_span * 0.06, ymax + ym_top)
    ax.grid(AppData.opt_grid, alpha=0.22, linestyle=':')
    ax.set_xlabel(f'수평거리 ({unit})', fontsize=9)
    ax.set_ylabel(f'높이 ({unit})', fontsize=9)
    ax.set_title(f'{AppData.title_text}  [NO.{no_idx + 1}]',
                 fontsize=13, fontweight='bold')

    handles, lbls = ax.get_legend_handles_labels()
    ax_l.legend(handles, lbls, loc='center', ncol=4, fontsize=9,
                framealpha=0.95, fancybox=True, edgecolor='#888888')
    fig.tight_layout(pad=1.5)

    if to_file:
        fig.savefig(to_file, dpi=dpi, bbox_inches='tight')
        plt.close(fig)
        return None

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return CoreImage(buf, ext='png').texture


# =====================================================
# 화면 클래스들
# =====================================================
class InputScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._sel_idx = -1
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(4))
        bg_rect(root, BG_DARK)

        hdr = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6), padding=(dp(4), dp(3)))
        bg_rect(hdr, BG_PANEL)
        hdr.add_widget(mk_lbl("측점 데이터 입력", font_size=sp(16),
                               bold=True, size_hint_x=0.65,
                               halign='left', valign='middle'))
        btn_def = mk_btn("기본값 로드", h=dp(38), size_hint_x=0.35)
        btn_def.bind(on_press=self._load_defaults)
        hdr.add_widget(btn_def)
        root.add_widget(hdr)

        th = GridLayout(cols=4, size_hint_y=None, height=dp(30), spacing=dp(1))
        bg_rect(th, (0.13, 0.32, 0.58, 1))
        for t in ["측점명", "DL(mm)", "DH(mm)", "비고"]:
            lbl = mk_lbl(t, font_size=sp(12), bold=True,
                         halign='center', valign='middle')
            lbl.bind(size=lbl.setter('text_size'))
            th.add_widget(lbl)
        root.add_widget(th)

        sv = ScrollView(size_hint=(1, 1))
        self.table = GridLayout(cols=4, size_hint_y=None, spacing=dp(1))
        self.table.bind(minimum_height=self.table.setter('height'))
        sv.add_widget(self.table)
        root.add_widget(sv)

        form = BoxLayout(orientation='vertical', size_hint_y=None,
                         height=dp(240), spacing=dp(4), padding=(dp(4), dp(4)))
        bg_rect(form, BG_PANEL)

        grid = GridLayout(cols=2, size_hint_y=None, height=dp(96), spacing=dp(4))
        self.inp_name = mk_input('측점명')
        self.inp_dl   = mk_input('DL (mm)', input_filter='float')
        self.inp_dh   = mk_input('DH (mm)', input_filter='float')
        self.inp_note = mk_input('비고')
        for w in [self.inp_name, self.inp_dl, self.inp_dh, self.inp_note]:
            grid.add_widget(w)
        form.add_widget(grid)

        pg = GridLayout(cols=5, size_hint_y=None, height=dp(58), spacing=dp(2))
        for name in PRESET_NAMES:
            b = mk_btn(name, clr=(0.18, 0.38, 0.62, 1), h=dp(26), font_size=sp(11))
            b.bind(on_press=lambda _, n=name: setattr(self.inp_name, 'text', n))
            pg.add_widget(b)
        form.add_widget(pg)

        br1 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for txt, clr, fn in [
            ("추가", COLOR_GREEN, self._add),
            ("수정", COLOR_BTN,   self._edit),
            ("삭제", COLOR_RED,   self._delete),
            ("전체삭제", (0.50, 0.18, 0.18, 1), self._clear),
        ]:
            b = mk_btn(txt, clr=clr, h=dp(36))
            b.bind(on_press=fn)
            br1.add_widget(b)
        form.add_widget(br1)

        br2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
        for txt, fn in [("UP", self._move_up), ("DOWN", self._move_down)]:
            b = mk_btn(txt, clr=(0.28, 0.42, 0.62, 1), h=dp(36))
            b.bind(on_press=fn)
            br2.add_widget(b)
        form.add_widget(br2)

        root.add_widget(form)
        self.add_widget(root)
        self._refresh()

    def on_enter(self):
        self._refresh()

    def _refresh(self):
        self.table.clear_widgets()
        for idx, row in enumerate(AppData.table_data):
            is_sel = (idx == self._sel_idx)
            bg = BG_ROW_SEL if is_sel else (BG_ROW_ODD if idx % 2 else BG_ROW_EVEN)
            for val in row:
                lbl = Label(text=str(val), size_hint_y=None, height=dp(34),
                            font_size=sp(11), color=COLOR_TEXT,
                            halign='center', valign='middle')
                lbl.bind(size=lbl.setter('text_size'))
                bg_rect(lbl, bg)
                lbl.bind(on_touch_down=lambda w, t, i=idx:
                         self._select(i) if w.collide_point(*t.pos) else None)
                self.table.add_widget(lbl)

    def _select(self, idx):
        self._sel_idx = idx
        row = AppData.table_data[idx]
        self.inp_name.text = str(row[0])
        self.inp_dl.text   = str(row[1])
        self.inp_dh.text   = str(row[2])
        self.inp_note.text = str(row[3])
        self._refresh()

    def _parse_dlh(self):
        try:
            dl = float(self.inp_dl.text or '0')
            dh = float(self.inp_dh.text or '0')
            return dl, dh
        except ValueError:
            popup_msg("입력 오류", "DL, DH는 숫자로 입력하세요.")
            return None, None

    def _add(self, *_):
        dl, dh = self._parse_dlh()
        if dl is None:
            return
        AppData.table_data.append([
            self.inp_name.text,
            int(dl) if dl == int(dl) else dl,
            int(dh) if dh == int(dh) else dh,
            self.inp_note.text,
        ])
        self.inp_name.text = ''
        self.inp_note.text = ''
        self._sel_idx = len(AppData.table_data) - 1
        self._refresh()

    def _edit(self, *_):
        if self._sel_idx < 0:
            popup_msg("안내", "수정할 행을 선택하세요.")
            return
        dl, dh = self._parse_dlh()
        if dl is None:
            return
        AppData.table_data[self._sel_idx] = [
            self.inp_name.text,
            int(dl) if dl == int(dl) else dl,
            int(dh) if dh == int(dh) else dh,
            self.inp_note.text,
        ]
        self._refresh()

    def _delete(self, *_):
        if self._sel_idx < 0:
            popup_msg("안내", "삭제할 행을 선택하세요.")
            return
        AppData.table_data.pop(self._sel_idx)
        self._sel_idx = max(-1, min(self._sel_idx, len(AppData.table_data) - 1))
        self._refresh()

    def _clear(self, *_):
        popup_confirm("전체 삭제", "모든 측점을 삭제하시겠습니까?",
                      lambda: (AppData.table_data.clear(),
                               setattr(self, '_sel_idx', -1),
                               self._refresh()))

    def _move_up(self, *_):
        i = self._sel_idx
        if i <= 0:
            return
        AppData.table_data[i], AppData.table_data[i - 1] = \
            AppData.table_data[i - 1], AppData.table_data[i]
        self._sel_idx = i - 1
        self._refresh()

    def _move_down(self, *_):
        i = self._sel_idx
        if i < 0 or i >= len(AppData.table_data) - 1:
            return
        AppData.table_data[i], AppData.table_data[i + 1] = \
            AppData.table_data[i + 1], AppData.table_data[i]
        self._sel_idx = i + 1
        self._refresh()

    def _load_defaults(self, *_):
        AppData.table_data = [list(r) for r in DEFAULT_DATA]
        self._sel_idx = -1
        self._refresh()


class DrawScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(4))
        bg_rect(root, BG_DARK)

        tb = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6), padding=dp(4))
        bg_rect(tb, BG_PANEL)

        self.no_spin = Spinner(
            text='NO.1', values=[f'NO.{i+1}' for i in range(10)],
            size_hint=(0.28, 1), background_normal='',
            background_color=(0.18, 0.38, 0.62, 1),
            color=COLOR_TEXT, font_size=sp(14))
        self.no_spin.bind(text=self._on_no)
        tb.add_widget(self.no_spin)

        btn_draw = mk_btn("그리기", clr=COLOR_GREEN, h=dp(44), size_hint=(0.36, 1))
        btn_draw.bind(on_press=self._start_draw)
        tb.add_widget(btn_draw)

        btn_save = mk_btn("저장", h=dp(44), size_hint=(0.36, 1))
        btn_save.bind(on_press=self._save_png)
        tb.add_widget(btn_save)
        root.add_widget(tb)

        opt = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(3), padding=(dp(4), 0))
        self._opt_btns = {}
        opt_map = {'labels': '측점명', 'dims': '치수선', 'grid': '격자', 'hatch': '해치'}
        for key, txt in opt_map.items():
            val = getattr(AppData, f'opt_{key}')
            b = Button(
                text=f'[v]{txt}' if val else txt,
                background_normal='',
                background_color=(0.22, 0.48, 0.36, 1) if val else (0.26, 0.28, 0.36, 1),
                color=COLOR_TEXT, font_size=sp(11))
            b.bind(on_press=lambda _, k=key: self._toggle(k))
            self._opt_btns[key] = b
            opt.add_widget(b)
        self.unit_btn = Button(
            text='mm', size_hint_x=0.5,
            background_normal='', background_color=(0.38, 0.28, 0.52, 1),
            color=COLOR_TEXT, font_size=sp(11))
        self.unit_btn.bind(on_press=self._toggle_unit)
        opt.add_widget(self.unit_btn)
        root.add_widget(opt)

        img_box = BoxLayout()
        bg_rect(img_box, (0.06, 0.08, 0.12, 1))
        self.draw_img = KivyImage(allow_stretch=True, keep_ratio=True)
        self._no_img_lbl = mk_lbl("NO.를 선택하고\n[그리기]를 누르세요",
                                  font_size=sp(16), halign='center', valign='middle')
        self._no_img_lbl.bind(size=self._no_img_lbl.setter('text_size'))
        img_box.add_widget(self._no_img_lbl)
        self._img_box = img_box
        root.add_widget(img_box)

        self.status = mk_lbl("", size_hint_y=None, height=dp(26),
                              font_size=sp(11), color=COLOR_HINT,
                              halign='left', valign='middle')
        self.status.bind(size=self.status.setter('text_size'))
        root.add_widget(self.status)

        self.add_widget(root)

    def on_enter(self):
        sec = AppData.sections[AppData.current_no]
        if sec['image']:
            self._show_texture(sec['image'])
            self.no_spin.text = f'NO.{AppData.current_no + 1}'

    def _on_no(self, _, text):
        AppData.current_no = int(text.replace('NO.', '')) - 1
        sec = AppData.sections[AppData.current_no]
        if sec['image']:
            self._show_texture(sec['image'])
        else:
            self._img_box.clear_widgets()
            self._img_box.add_widget(self._no_img_lbl)

    def _toggle(self, key):
        val = not getattr(AppData, f'opt_{key}')
        setattr(AppData, f'opt_{key}', val)
        opt_map = {'labels': '측점명', 'dims': '치수선', 'grid': '격자', 'hatch': '해치'}
        b = self._opt_btns[key]
        b.text = f'[v]{opt_map[key]}' if val else opt_map[key]
        b.background_color = (0.22, 0.48, 0.36, 1) if val else (0.26, 0.28, 0.36, 1)

    def _toggle_unit(self, *_):
        AppData.unit = 'm' if AppData.unit == 'mm' else 'mm'
        self.unit_btn.text = AppData.unit

    def _start_draw(self, *_):
        pts = get_points()
        if len(pts) < 2:
            popup_msg("데이터 부족", "측점이 2개 이상 필요합니다.")
            return
        self.status.text = '그리는 중...'
        Clock.schedule_once(lambda dt: self._do_render(pts), 0.1)

    def _do_render(self, pts):
        try:
            no = AppData.current_no
            tex = render_figure(pts, no, dpi=110)
            AppData.sections[no]['image'] = tex
            self._show_texture(tex)
            unit = AppData.unit
            s    = 0.001 if unit == 'm' else 1.0
            xs   = [p['l'] * s for p in pts]
            total_w = (max(xs) - min(xs)) / s
            self.status.text = (f"[NO.{no+1}]  측점 {len(pts)}개 | "
                                f"전체폭 {total_w:,.0f} mm | 완료")
        except Exception as e:
            self.status.text = f'오류: {e}'
            Logger.error(f'Render: {traceback.format_exc()}')

    def _show_texture(self, tex):
        self._img_box.clear_widgets()
        self.draw_img.texture = tex
        self._img_box.add_widget(self.draw_img)

    def _save_png(self, *_):
        pts = get_points()
        if len(pts) < 2:
            popup_msg("안내", "먼저 [그리기]를 실행하세요.")
            return
        import datetime
        fname = (f'cross_section_NO{AppData.current_no+1}_'
                 f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.png')
        path = os.path.join(get_save_dir(), fname)
        try:
            render_figure(pts, AppData.current_no, to_file=path, dpi=150)
            popup_msg("저장 완료", f"저장됨:\n{path}")
        except Exception as e:
            popup_msg("오류", str(e))


class PhotoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=dp(3), padding=dp(4))
        bg_rect(root, BG_DARK)

        top = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(6), padding=dp(4))
        bg_rect(top, BG_PANEL)
        self.no_spin = Spinner(
            text='NO.1', values=[f'NO.{i+1}' for i in range(10)],
            size_hint=(0.32, 1), background_normal='',
            background_color=(0.18, 0.38, 0.62, 1),
            color=COLOR_TEXT, font_size=sp(14))
        self.no_spin.bind(text=self._on_no)
        top.add_widget(self.no_spin)
        self.counter = mk_lbl("사진 없음", font_size=sp(12),
                               color=COLOR_HINT, size_hint=(0.68, 1),
                               halign='left', valign='middle')
        self.counter.bind(size=self.counter.setter('text_size'))
        top.add_widget(self.counter)
        root.add_widget(top)

        self._img_box = BoxLayout()
        bg_rect(self._img_box, (0.04, 0.06, 0.10, 1))
        self.photo_img = KivyImage(allow_stretch=True, keep_ratio=True)
        self._placeholder = mk_lbl("사진을 추가하려면\n아래 버튼을 누르세요",
                                   font_size=sp(15), halign='center', valign='middle')
        self._placeholder.bind(size=self._placeholder.setter('text_size'))
        self._img_box.add_widget(self._placeholder)
        root.add_widget(self._img_box)

        memo_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(4),
                             padding=(dp(4), dp(2)))
        self.memo_inp = mk_input("사진 메모")
        btn_memo = mk_btn("저장", h=dp(40), size_hint_x=0.25)
        btn_memo.bind(on_press=self._save_memo)
        memo_row.add_widget(self.memo_inp)
        memo_row.add_widget(btn_memo)
        root.add_widget(memo_row)

        nav = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4),
                        padding=(dp(4), 0))
        for txt, fn, clr in [
            ("< 이전", self._prev, COLOR_BTN),
            ("다음 >", self._next, COLOR_BTN),
            ("삭제", self._delete, COLOR_RED),
        ]:
            b = mk_btn(txt, clr=clr, h=dp(40))
            b.bind(on_press=fn)
            nav.add_widget(b)
        root.add_widget(nav)

        act = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4),
                        padding=(dp(4), dp(2)))
        btn_add = mk_btn("사진 추가", clr=COLOR_GREEN, h=dp(44))
        btn_add.bind(on_press=self._add)
        act.add_widget(btn_add)
        root.add_widget(act)

        self.add_widget(root)

    def on_enter(self):
        self.no_spin.text = f'NO.{AppData.current_no + 1}'
        self._refresh()

    def _on_no(self, _, text):
        AppData.current_no = int(text.replace('NO.', '')) - 1
        self._refresh()

    def _sec(self):
        return AppData.sections[AppData.current_no]

    def _refresh(self):
        sec    = self._sec()
        photos = sec['photos']
        if not photos:
            self.counter.text = '사진 없음'
            self.memo_inp.text = ''
            self._img_box.clear_widgets()
            self._img_box.add_widget(self._placeholder)
            return
        idx   = sec['photo_idx']
        entry = photos[idx]
        self.counter.text  = f'[{idx+1}/{len(photos)}]  {os.path.basename(entry["path"])}'
        self.memo_inp.text = entry['note']
        try:
            from PIL import Image as PIL_Img
            img = PIL_Img.open(entry['path'])
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            tex = CoreImage(buf, ext='png').texture
            self.photo_img.texture = tex
            self._img_box.clear_widgets()
            self._img_box.add_widget(self.photo_img)
        except Exception as e:
            self.counter.text = f'로드 실패: {e}'

    def _prev(self, *_):
        sec = self._sec()
        if not sec['photos']:
            return
        sec['photo_idx'] = (sec['photo_idx'] - 1) % len(sec['photos'])
        self._refresh()

    def _next(self, *_):
        sec = self._sec()
        if not sec['photos']:
            return
        sec['photo_idx'] = (sec['photo_idx'] + 1) % len(sec['photos'])
        self._refresh()

    def _delete(self, *_):
        sec = self._sec()
        if not sec['photos']:
            return
        def do():
            sec['photos'].pop(sec['photo_idx'])
            sec['photo_idx'] = max(0, min(sec['photo_idx'], len(sec['photos']) - 1))
            self._refresh()
        popup_confirm("삭제 확인", "현재 사진을 삭제하시겠습니까?", do)

    def _save_memo(self, *_):
        sec = self._sec()
        if sec['photos']:
            sec['photos'][sec['photo_idx']]['note'] = self.memo_inp.text

    def _add(self, *_):
        self._show_filechooser()

    def _show_filechooser(self):
        content = BoxLayout(orientation='vertical', spacing=dp(4))
        fc = FileChooserListView(
            filters=['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.webp'],
            multiselect=True,
            path=get_save_dir(),
        )
        content.add_widget(fc)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50),
                            spacing=dp(6), padding=dp(4))
        p = Popup(title='사진 선택', content=content, size_hint=(0.96, 0.88),
                  title_color=COLOR_TEXT, background='',
                  background_color=(0.12, 0.14, 0.20, 0.97))
        def sel(*_):
            if fc.selection:
                sec = self._sec()
                for path in fc.selection:
                    if os.path.exists(path):
                        sec['photos'].append({'path': path, 'note': ''})
                if sec['photos']:
                    sec['photo_idx'] = max(0, len(sec['photos']) - len(fc.selection))
                self._refresh()
            p.dismiss()
        ok  = mk_btn("선택", clr=COLOR_GREEN, h=dp(44))
        cxl = mk_btn("취소", h=dp(44))
        ok.bind(on_press=sel)
        cxl.bind(on_press=p.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cxl)
        content.add_widget(btn_row)
        p.open()


class ExportScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', spacing=dp(8),
                         padding=(dp(12), dp(8)))
        bg_rect(root, BG_DARK)

        root.add_widget(mk_lbl("저장 / 내보내기", font_size=sp(18),
                                bold=True, size_hint_y=None, height=dp(44),
                                halign='center', valign='middle'))

        trow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        trow.add_widget(mk_lbl("도면명:", size_hint_x=0.28, font_size=sp(14),
                                halign='right', valign='middle'))
        self.title_inp = mk_input()
        self.title_inp.text = AppData.title_text
        self.title_inp.bind(text=lambda _, v: setattr(AppData, 'title_text', v))
        trow.add_widget(self.title_inp)
        root.add_widget(trow)

        nrow = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
        nrow.add_widget(mk_lbl("저장 NO.:", size_hint_x=0.28, font_size=sp(14),
                                halign='right', valign='middle'))
        self.no_spin = Spinner(
            text='NO.1', values=[f'NO.{i+1}' for i in range(10)],
            size_hint=(0.72, 1), background_normal='',
            background_color=(0.18, 0.38, 0.62, 1),
            color=COLOR_TEXT, font_size=sp(14))
        nrow.add_widget(self.no_spin)
        root.add_widget(nrow)

        root.add_widget(Label(size_hint_y=None, height=dp(6)))

        for txt, fn in [
            ("PNG 이미지 저장",  self._save_png),
            ("PDF 저장 (A3)",    self._save_pdf),
            ("CSV 내보내기",     self._export_csv),
            ("CSV 가져오기",     self._import_csv),
        ]:
            b = mk_btn(txt, h=dp(52), font_size=sp(15))
            b.bind(on_press=fn)
            root.add_widget(b)
            root.add_widget(Label(size_hint_y=None, height=dp(4)))

        root.add_widget(Label())
        self.add_widget(root)

    def on_enter(self):
        self.no_spin.text = f'NO.{AppData.current_no + 1}'
        self.title_inp.text = AppData.title_text

    def _get_no(self):
        return int(self.no_spin.text.replace('NO.', '')) - 1

    def _make_path(self, ext):
        import datetime
        fname = (f'cross_section_NO{self._get_no()+1}_'
                 f'{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.{ext}')
        return os.path.join(get_save_dir(), fname)

    def _save_png(self, *_):
        AppData.current_no = self._get_no()
        pts = get_points()
        if len(pts) < 2:
            popup_msg("안내", "측점 데이터가 없습니다.")
            return
        path = self._make_path('png')
        try:
            render_figure(pts, AppData.current_no, to_file=path, dpi=150)
            popup_msg("저장 완료", f"저장됨:\n{path}")
        except Exception as e:
            popup_msg("오류", str(e))

    def _save_pdf(self, *_):
        AppData.current_no = self._get_no()
        pts = get_points()
        if len(pts) < 2:
            popup_msg("안내", "측점 데이터가 없습니다.")
            return
        path = self._make_path('pdf')
        try:
            if not _init_matplotlib():
                popup_msg("오류", f"matplotlib 로드 실패: {_mpl_error}")
                return
            plt = _mpl_plt
            from matplotlib.backends.backend_pdf import PdfPages
            tmp_png = os.path.join(get_save_dir(), '_tmp_pdf.png')
            with PdfPages(path) as pdf:
                render_figure(pts, AppData.current_no, to_file=tmp_png, dpi=200)
                fig = plt.figure(figsize=(16.54, 11.69))
                ax  = fig.add_axes([0, 0, 1, 1])
                from PIL import Image as PIL_Img
                img = PIL_Img.open(tmp_png)
                ax.imshow(img)
                ax.axis('off')
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
                if os.path.exists(tmp_png):
                    os.remove(tmp_png)
            popup_msg("저장 완료", f"PDF 저장됨:\n{path}")
        except Exception as e:
            popup_msg("오류", str(e))

    def _export_csv(self, *_):
        path = self._make_path('csv')
        try:
            with open(path, 'w', encoding='utf-8-sig') as f:
                f.write("측점명,DL(mm),DH(mm),비고\n")
                for row in AppData.table_data:
                    f.write(','.join(str(x) for x in row) + '\n')
            popup_msg("완료", f"CSV 저장됨:\n{path}")
        except Exception as e:
            popup_msg("오류", str(e))

    def _import_csv(self, *_):
        content = BoxLayout(orientation='vertical', spacing=dp(4))
        fc = FileChooserListView(
            filters=['*.csv', '*.txt'],
            path=get_save_dir(),
        )
        content.add_widget(fc)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50),
                            spacing=dp(6), padding=dp(4))
        p = Popup(title='CSV 파일 선택', content=content, size_hint=(0.96, 0.85),
                  title_color=COLOR_TEXT, background='',
                  background_color=(0.12, 0.14, 0.20, 0.97))
        def sel(*_):
            if fc.selection:
                self._do_import(fc.selection[0])
            p.dismiss()
        ok  = mk_btn("선택", clr=COLOR_GREEN, h=dp(44))
        cxl = mk_btn("취소", h=dp(44))
        ok.bind(on_press=sel)
        cxl.bind(on_press=p.dismiss)
        btn_row.add_widget(ok)
        btn_row.add_widget(cxl)
        content.add_widget(btn_row)
        p.open()

    def _do_import(self, path):
        try:
            count = 0
            with open(path, encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = [x.strip() for x in line.split(',')]
                    if len(parts) < 2:
                        continue
                    try:
                        if len(parts) == 2:
                            name, dl, dh, note = '', float(parts[0]), float(parts[1]), ''
                        else:
                            name = parts[0]
                            dl, dh = float(parts[1]), float(parts[2])
                            note = parts[3] if len(parts) > 3 else ''
                        AppData.table_data.append([
                            name,
                            int(dl) if dl == int(dl) else dl,
                            int(dh) if dh == int(dh) else dh,
                            note,
                        ])
                        count += 1
                    except ValueError:
                        continue
            popup_msg("완료", f"CSV 가져오기 완료:\n{count}개 측점")
        except Exception as e:
            popup_msg("오류", str(e))


# =====================================================
# 메인 앱
# =====================================================
class SurveyCrossSectionApp(App):
    def build(self):
        Window.clearcolor = BG_DARK

        root = BoxLayout(orientation='vertical')

        self.sm = ScreenManager()
        self.sm.add_widget(InputScreen(name='input'))
        self.sm.add_widget(DrawScreen(name='draw'))
        self.sm.add_widget(PhotoScreen(name='photo'))
        self.sm.add_widget(ExportScreen(name='export'))
        root.add_widget(self.sm)

        root.add_widget(self._build_nav())
        return root

    def _build_nav(self):
        nav = BoxLayout(size_hint_y=None, height=dp(56), spacing=dp(1))
        bg_rect(nav, (0.08, 0.10, 0.16, 1))
        self._nav_btns = {}
        items = [
            ('input',  '입력'),
            ('draw',   '그리기'),
            ('photo',  '사진'),
            ('export', '저장'),
        ]
        for scr, txt in items:
            b = Button(
                text=txt,
                background_normal='',
                background_color=(0.16, 0.20, 0.30, 1),
                color=COLOR_HINT,
                font_size=sp(13),
                halign='center', valign='middle',
            )
            b.bind(on_press=lambda _, s=scr: self._goto(s))
            self._nav_btns[scr] = b
            nav.add_widget(b)
        self._update_nav('input')
        return nav

    def _goto(self, scr):
        self.sm.current = scr
        self._update_nav(scr)

    def _update_nav(self, active):
        for name, btn in self._nav_btns.items():
            if name == active:
                btn.background_color = COLOR_BTN
                btn.color = (1, 1, 1, 1)
            else:
                btn.background_color = (0.16, 0.20, 0.30, 1)
                btn.color = COLOR_HINT


if __name__ == '__main__':
    SurveyCrossSectionApp().run()
