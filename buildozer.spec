[app]

# 앱 이름 및 패키지 정보
title = 횡단면도
package.name = surveycrosssection
package.domain = org.survey

# 소스
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

# 버전
version = 1.0

# requirements - 불필요한 패키지 제거 (requests/urllib3 등은 이 앱에서 미사용)
requirements = python3,kivy==2.3.0,pillow,matplotlib,numpy,android

# matplotlib 환경변수 - MPLCONFIGDIR은 런타임에 앱 저장소로 동적 설정됨
android.env_vars = MPLBACKEND=Agg


# 화면 방향 (가로)
orientation = landscape

# 권한 - Android 13+ (API 33+)와 하위 버전 모두 지원
android.permissions = READ_MEDIA_IMAGES,READ_MEDIA_VIDEO,READ_MEDIA_AUDIO,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

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
