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

sys.setrecursionlimit(5000)

block_cipher = None

a = Analysis(
    ['run_worker.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'selenium',
        'selenium.webdriver',
        'selenium.webdriver.chrome.options',
        'selenium.webdriver.chrome.service',
        'selenium.webdriver.common.by',
        'selenium.webdriver.common.keys',
        'selenium.webdriver.support.ui',
        'selenium.webdriver.support.expected_conditions',
        'gspread',
        'google.auth',
        'google.auth.transport.requests',
        'google.oauth2.service_account',
        'dotenv',
        'pyperclip',
    ],
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
