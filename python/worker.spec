# PyInstaller spec: LMS 자동화 worker 패키지를 배포용 exe(worker.exe)로 묶는다.
#
# 실행 방법 (반드시 python/ 폴더에서, 배포 대상과 동일한 Windows에서 실행):
#   pip install -r requirements.txt pyinstaller
#   pyinstaller worker.spec
#
# 결과물: python/dist/worker/ 폴더 전체 (worker.exe + 필요한 dll/데이터).
# onefile이 아니라 onedir(폴더) 방식을 쓰는 이유: onefile은 실행할 때마다
# 임시 폴더에 압축을 풀어야 해서 매번 느려지고, selenium/chromedriver와
# 얽혔을 때 임시 경로 문제가 생기기 더 쉽다.

import sys

from PyInstaller.utils.hooks import collect_submodules

sys.setrecursionlimit(5000)

block_cipher = None

# selenium은 webdriver.Chrome처럼 쓸 때 필요한 서브모듈(selenium.webdriver.chrome.webdriver 등)을
# selenium.webdriver.__getattr__로 그때그때 지연 임포트한다. 이런 지연 임포트는 PyInstaller가
# 정적 분석만으로는 찾지 못해서 몇 개만 hiddenimports에 적어두면 꼭 빠지는 게 생긴다.
# collect_submodules로 selenium 패키지 전체를 통째로 포함시켜 이 문제를 근본적으로 막는다.
hiddenimports = collect_submodules('selenium') + [
    'gspread',
    'google.auth',
    'google.auth.transport.requests',
    'google.oauth2.service_account',
    'dotenv',
    'pyperclip',
]

a = Analysis(
    ['run_worker.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='worker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='worker',
)
