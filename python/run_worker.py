"""PyInstaller로 exe를 만들 때 쓰는 진입점.

worker/main.py를 PyInstaller에 직접 넘기면 그 파일이 __main__으로 실행되어
안의 상대 import(from .control import ControlState 등)가 깨진다. 이 파일을
통해 worker를 '패키지'로 임포트해서 실행해야 상대 import가 정상 동작한다.

빌드 방법 (python/ 폴더에서, 실제 배포 대상과 동일한 OS/아키텍처에서 실행):
    pyinstaller worker.spec
"""

from worker.main import main

if __name__ == "__main__":
    main()
