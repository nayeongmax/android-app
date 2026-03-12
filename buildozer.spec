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

# requirements
requirements = python3,kivy==2.3.0,pillow,matplotlib,numpy

# matplotlib 환경변수
android.env_vars = MPLBACKEND=Agg

# 화면 방향 (세로)
orientation = portrait

# 권한
android.permissions = READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Android 설정 (원래 빌드 성공했던 값 유지)
android.api = 35
android.minapi = 24
android.ndk = 25b
android.ndk_api = 24
android.archs = arm64-v8a

# 풀스크린
fullscreen = 0

# 로그 레벨
log_level = 2

[buildozer]
log_level = 2
warn_on_root = 1
