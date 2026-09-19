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

module.exports = { tidyText };
