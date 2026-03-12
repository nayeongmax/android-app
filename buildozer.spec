[app]

# 앱 이름 및 패키지 정보
title = SurveyCrossSection
package.name = surveycrosssection
package.domain = org.survey

# 소스
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# 버전
version = 1.0

# requirements - android 모듈은 p4a가 자동 제공하므로 명시하지 않음
requirements = python3,kivy==2.3.0,pillow,matplotlib,numpy

# matplotlib 환경변수
android.env_vars = MPLBACKEND=Agg

# 화면 방향 (가로)
orientation = landscape

# 권한
android.permissions = READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android 설정
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a

# 풀스크린
fullscreen = 0

# 로그 레벨
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
