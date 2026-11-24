const Anthropic = require('@anthropic-ai/sdk');
const store = require('../store');

// 업무보고 "정리하기" 버튼: 사용자가 대충 쓴 메모를 미사여구 없이 간결한
// 개조식으로 정리한다. 내용을 지어내지 않고, 입력에 있는 사실만 다듬는다.
const SYSTEM_PROMPT = `업무보고에 들어갈 메모를 정리하는 도우미다. 규칙:
- 미사여구, 접속사 남발, "~했습니다/~했어요" 같은 장황한 종결어미를 없애고 간결한 명사형/개조식으로 정리한다.
- 각 항목은 짧은 불릿(-)으로 나눠 가독성을 높인다.
- 입력에 없는 내용을 지어내지 않는다. 사실만 정리한다.
- 결과 텍스트만 출력한다. 인사말, 설명, 따옴표를 붙이지 않는다.`;

async function tidyText(rawText) {
  const apiKey = store.get('anthropicApiKey');
  if (!apiKey) {
    return { success: false, error: 'Claude API 키가 설정되지 않았습니다. 위 설정란에 입력해주세요.' };
  }
  if (!rawText || !rawText.trim()) {
    return { success: false, error: '정리할 내용이 없습니다.' };
  }

  const client = new Anthropic({ apiKey });

  try {
    const response = await client.messages.create({
      model: 'claude-opus-5',
      max_tokens: 2000,
      output_config: { effort: 'low' },
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: rawText }],
    });

    const textBlock = response.content.find((block) => block.type === 'text');
    if (!textBlock) {
      return { success: false, error: '응답에서 텍스트를 찾지 못했습니다.' };
    }
    return { success: true, text: textBlock.text.trim() };
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) {
      return { success: false, error: 'Claude API 키가 올바르지 않습니다.' };
    }
    if (err instanceof Anthropic.RateLimitError) {
      return { success: false, error: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.' };
    }
    if (err instanceof Anthropic.APIError) {
      return { success: false, error: `API 오류 (${err.status}): ${err.message}` };
    }
    return { success: false, error: err.message || String(err) };
  }
}

// 요일 표기(영문 약어/한글)를 0(일)~6(토) 숫자로 변환할 때 Claude가 참고할 기준표.
// 사용자가 보내는 메시지마다 "MWF", "TTH", "월수금" 등 표기가 제각각이라, 모델이
// 직접 해석하게 하는 대신 여기서 명확한 매핑을 프롬프트에 박아 넣어 실수를 줄인다.
const WEEKDAY_SCHEDULE_SYSTEM_PROMPT = `강사 스케줄 변경 요청(자유 형식 텍스트, 주로 카카오톡/슬랙에서 복붙한 메시지)을
분석해서, 블랙/화이트 타임으로 바꿔야 할 (강사, 요일, 시작 시각, 상태) 목록을 뽑아내는 도우미다.

요일 숫자 매핑(0=일 1=월 2=화 3=수 4=목 5=금 6=토):
- MWF = [1,3,5], TTH 또는 TuTh = [2,4], MTWTHF = [1,2,3,4,5], 매일/주7일 = [0,1,2,3,4,5,6]
- 한글 요일(월/화/수/목/금/토/일)이 나오면 그대로 숫자로 바꾼다.
- 어느 요일인지 전혀 알 수 없으면 그 항목은 빼고 warnings에 이유를 적는다.

상태(state) 판단:
- "블랙타임", "닫기", "휴강", "수업 안 함"처럼 수업을 막는 맥락이면 "close".
- "화이트타임", "열기", "수업 가능"처럼 수업을 여는 맥락이면 "open".
- 애매하면 "close"로 판단하고 왜 그렇게 봤는지 짧게 warnings에 남긴다.

강사 이름:
- 함께 전달되는 "등록된 강사 명단"에서 가장 비슷한 이름을 찾아 그 명단에 있는
  표기 그대로 사용한다(대소문자 다를 수 있음, 예: LETTIE -> Lettie).
- 명단에서 못 찾겠으면 입력에 쓰인 그대로 쓰고, warnings에 "명단에서 찾지 못함"이라고 남긴다.

시각:
- "14:00KT-14:45KT"처럼 시작~종료가 있으면 시작 시각만 쓴다. "KT"/"KST" 등 시간대
  표기는 버린다.
- 시(hour)는 0~23, 분(minute)은 반드시 0 또는 30 중 하나로 맞춘다. 원문이 그 외
  분(예: 10, 45)이면 가장 가까운 0 또는 30으로 보정하고 warnings에 그 사실을 적는다.

같은 (강사, 요일, 시각, 상태)가 여러 번 나오면(여러 학생이 같은 강사의 같은 시간을
공유하는 경우 등) 한 번만 남긴다.

반드시 아래 JSON 하나만 출력한다(설명, 인사말, 마크다운 코드블록 금지):
{"entries": [{"tutor": "Lettie", "weekdays": [1,3,5], "hour": 14, "startMinute": 0, "state": "close"}, ...],
 "warnings": ["문자열", ...]}
entries가 비어 있으면 빈 배열로 둔다.`;

async function parseTutorScheduleText(rawText, knownTutors) {
  const apiKey = store.get('anthropicApiKey');
  if (!apiKey) {
    return { success: false, error: 'Claude API 키가 설정되지 않았습니다. 위 설정란에 입력해주세요.' };
  }
  if (!rawText || !rawText.trim()) {
    return { success: false, error: '분석할 내용이 없습니다.' };
  }

  const client = new Anthropic({ apiKey });
  const rosterLine = Array.isArray(knownTutors) && knownTutors.length > 0
    ? `등록된 강사 명단: ${knownTutors.join(', ')}`
    : '등록된 강사 명단 정보 없음 (입력에 쓰인 이름 그대로 사용)';

  try {
    const response = await client.messages.create({
      model: 'claude-opus-5',
      max_tokens: 4000,
      output_config: { effort: 'low' },
      system: WEEKDAY_SCHEDULE_SYSTEM_PROMPT,
      messages: [{ role: 'user', content: `${rosterLine}\n\n---\n\n${rawText}` }],
    });

    const textBlock = response.content.find((block) => block.type === 'text');
    if (!textBlock) {
      return { success: false, error: '응답에서 텍스트를 찾지 못했습니다.' };
    }

    // 모델이 그래도 가끔 ```json 코드블록으로 감싸는 경우를 대비해 한 번 벗겨낸다.
    const raw = textBlock.text.trim().replace(/^```(?:json)?\s*/i, '').replace(/```\s*$/i, '');

    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (parseErr) {
      return { success: false, error: `분석 결과를 해석하지 못했습니다: ${parseErr.message}` };
    }

    return {
      success: true,
      entries: Array.isArray(parsed.entries) ? parsed.entries : [],
      warnings: Array.isArray(parsed.warnings) ? parsed.warnings : [],
    };
  } catch (err) {
    if (err instanceof Anthropic.AuthenticationError) {
      return { success: false, error: 'Claude API 키가 올바르지 않습니다.' };
    }
    if (err instanceof Anthropic.RateLimitError) {
      return { success: false, error: '요청이 너무 많습니다. 잠시 후 다시 시도해주세요.' };
    }
    if (err instanceof Anthropic.APIError) {
      return { success: false, error: `API 오류 (${err.status}): ${err.message}` };
    }
    return { success: false, error: err.message || String(err) };
  }
}

module.exports = { tidyText, parseTutorScheduleText };
