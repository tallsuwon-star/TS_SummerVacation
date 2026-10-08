"""상담관리 글 상세 페이지에 첨부된 회원 요청 캡처 스크린샷을 찾아 로컬에
저장한다.

서버에서 따로 내려받지 않고 "지금 로그인된 브라우저 세션"으로 fetch()해서
base64로 돌려받는다 — 업로드 이미지 경로가 로그인 세션을 요구할 수 있는데,
별도 requests 세션에 쿠키를 복제하는 것보다 이 방식이 훨씬 간단하고 확실하다.

스크린샷이 아닌 사이트 공통 이미지(로고/아이콘 등)까지 집히지 않도록, 파일
경로에 흔한 "장식용" 키워드가 들어간 이미지와 아주 작게(가로/세로 50px 미만)
명시된 이미지는 후보에서 제외한다. 그래도 무엇이 실제 캡처 스크린샷인지는
짐작일 뿐이라 — 후보를 하나도 못 찾거나 여러 개를 찾으면 그 사실을 그대로
로그로 남겨 사람이 직접 상담관리 화면에서 확인하게 한다."""

import base64
import re
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..utils.progress import emit_log

_FURNITURE_SRC_RE = re.compile(
    r"(logo|icon|btn[_\-]|bullet|spacer|blank\.gif|arrow|/skin/|/common/img/)", re.IGNORECASE
)
_MIN_CONTENT_DIMENSION = 50


class ConsultCaptureError(Exception):
    pass


def find_capture_image_urls(driver) -> list[str]:
    """현재 페이지(detail_url로 이동한 뒤)에서 사이트 공통 이미지로 보이지
    않는 <img> 후보들을, 문서에 나온 순서대로 중복 없이 반환한다."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    candidates: list[str] = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        if _FURNITURE_SRC_RE.search(src):
            continue

        width, height = img.get("width"), img.get("height")
        try:
            if (
                width is not None
                and height is not None
                and int(float(width)) < _MIN_CONTENT_DIMENSION
                and int(float(height)) < _MIN_CONTENT_DIMENSION
            ):
                continue
        except ValueError:
            pass

        candidates.append(urljoin(driver.current_url, src))

    seen: set[str] = set()
    unique: list[str] = []
    for url in candidates:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


def _download_image_via_browser(driver, image_url: str) -> tuple[str, bytes]:
    """지금 브라우저 세션의 인증(쿠키)을 그대로 써서 이미지를 받아온다.
    반환값은 (data URL의 "data:image/png;base64," 부분, 디코딩된 바이트)."""
    data_url = driver.execute_async_script(
        """
        const url = arguments[0];
        const callback = arguments[arguments.length - 1];
        fetch(url, { credentials: 'include' })
          .then((r) => r.blob())
          .then((blob) => {
            const reader = new FileReader();
            reader.onloadend = () => callback(reader.result);
            reader.onerror = () => callback(null);
            reader.readAsDataURL(blob);
          })
          .catch(() => callback(null));
        """,
        image_url,
    )
    if not data_url or "," not in data_url:
        raise ConsultCaptureError(f"이미지를 내려받지 못했습니다: {image_url}")

    header, encoded = data_url.split(",", 1)
    return header, base64.b64decode(encoded)


def _extension_from_data_url_header(header: str) -> str:
    match = re.search(r"image/(\w+)", header)
    if not match:
        return ".png"
    ext = match.group(1).lower()
    return ".jpg" if ext == "jpeg" else f".{ext}"


def _unique_path(output_dir: Path, member_name: str, extension: str) -> Path:
    """같은 날짜 폴더 안에서 같은 회원 이름 파일이 이미 있으면 "회원명2",
    "회원명3"... 식으로 번호를 붙여 겹치지 않게 한다."""
    safe_name = member_name.strip() or "회원"
    candidate = output_dir / f"{safe_name}{extension}"
    if not candidate.exists():
        return candidate

    n = 2
    while True:
        candidate = output_dir / f"{safe_name}{n}{extension}"
        if not candidate.exists():
            return candidate
        n += 1


def save_consult_capture(driver, detail_url: str, member_name: str, output_dir: Path) -> Path | None:
    """detail_url로 이동해 캡처 스크린샷으로 보이는 이미지를 찾아 output_dir에
    member_name 파일명으로 저장한다.

    후보를 하나도 못 찾으면 None을 반환하고 경고 로그만 남긴다 (글에 캡처가
    원래 없었을 수도 있어 실패로 취급하지 않는다). 후보가 여러 개면 첫
    번째만 저장하고, 더 있었다는 사실도 로그로 남겨 사람이 직접 확인하게
    한다."""
    driver.get(detail_url)
    candidates = find_capture_image_urls(driver)

    if not candidates:
        emit_log(f'  ⚠ [{member_name}] 상담 내용에서 캡처 이미지를 찾지 못했습니다. 직접 확인해주세요.', level="warn")
        return None

    if len(candidates) > 1:
        emit_log(
            f"  ⚠ [{member_name}] 이미지 후보가 {len(candidates)}개 발견돼 첫 번째만 저장합니다. 나머지도 확인해보세요.",
            level="warn",
        )

    try:
        header, image_bytes = _download_image_via_browser(driver, candidates[0])
    except ConsultCaptureError as exc:
        emit_log(f"  ⚠ [{member_name}] {exc}", level="warn")
        return None

    output_path = _unique_path(output_dir, member_name, _extension_from_data_url_header(header))
    output_path.write_bytes(image_bytes)
    emit_log(f"  캡처 이미지 저장: {output_path.name}")
    return output_path
