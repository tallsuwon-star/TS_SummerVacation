// 교재 관리 화면의 "주소 확인" 버튼: LMS에서 긁어온 주소가 실제 존재하는
// 주소인지, 행정안전부(juso.go.kr) 도로명주소 오픈 API로 조회해 대조한다.
// 승인키(confmKey)는 사용자가 https://www.juso.go.kr 에서 직접 발급받아
// 설정에 입력해야 한다 — 여기서는 저장된 키를 그대로 전달만 한다.

const JUSO_API_URL = 'https://www.juso.go.kr/addrlink/addrLinkApi.do';

// LMS 배송정보에는 "( 23242 ) 서울 ..." 처럼 우편번호가 괄호로 앞에 붙어
// 있는데, 도로명주소 API는 우편번호가 아니라 주소 문자열로 검색하므로
// 그 괄호 부분을 떼어내고 나머지로 검색한다.
function stripLeadingZipCode(address) {
  return (address || '').replace(/^\(\s*\d*\s*\)\s*/, '').trim();
}

async function checkRoadAddress(address, apiKey) {
  const key = (apiKey || '').trim();
  if (!key) {
    return { success: false, error: '도로명주소 API 키가 설정되지 않았습니다. 교재 관리 화면 위쪽에 입력해주세요.' };
  }

  const keyword = stripLeadingZipCode(address);
  if (!keyword) {
    return { success: false, error: '확인할 주소가 없습니다.' };
  }

  const params = new URLSearchParams({
    confmKey: key,
    currentPage: '1',
    countPerPage: '5',
    keyword,
    resultType: 'json',
  });

  let response;
  try {
    response = await fetch(`${JUSO_API_URL}?${params.toString()}`);
  } catch (err) {
    return { success: false, error: `도로명주소 API 요청 중 오류: ${err.message || err}` };
  }

  if (!response.ok) {
    return { success: false, error: `도로명주소 API 응답 오류 (HTTP ${response.status})` };
  }

  let data;
  try {
    data = await response.json();
  } catch (err) {
    return { success: false, error: '도로명주소 API 응답을 해석하지 못했습니다.' };
  }

  const common = data?.results?.common;
  if (!common) {
    return { success: false, error: '도로명주소 API 응답 형식이 예상과 다릅니다.' };
  }
  // errorCode "0"이 정상. 그 외(승인키 오류 등)는 그대로 사람이 읽을 메시지로 전달.
  if (common.errorCode !== '0') {
    return { success: false, error: common.errorMessage || `도로명주소 API 오류 (${common.errorCode})` };
  }

  const totalCount = Number(common.totalCount || 0);
  const juso = Array.isArray(data.results.juso) ? data.results.juso : [];

  return {
    success: true,
    matched: totalCount > 0,
    totalCount,
    candidates: juso.map((j) => ({ roadAddr: j.roadAddr, jibunAddr: j.jibunAddr, zipNo: j.zipNo })),
  };
}

module.exports = { checkRoadAddress };
