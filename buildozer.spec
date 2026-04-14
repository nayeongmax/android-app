[app]

# 앱 이름 및 패키지 정보
title = SojuTracker
package.name = sojutracker
package.domain = org.soju

# 소스
source.dir = .
source.include_exts = py,ttf,wav
source.include_patterns = fonts/*.ttf

# 버전
version = 1.0

# requirements
requirements = python3,kivy==2.3.0,plyer

# 화면 방향 (세로)
orientation = portrait

# 권한
android.permissions = VIBRATE

# Android 설정
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
