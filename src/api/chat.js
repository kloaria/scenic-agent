import { createId } from '../utils/id.js';

const DIFY_WEB_APP_URL = 'https://udify.app/chat/G1lXUZh9LgrQ0AsT';
const difyWebApp = new URL(DIFY_WEB_APP_URL);
const DIFY_API_BASE_URL = `${difyWebApp.origin}/api`;
const DIFY_APP_CODE = difyWebApp.pathname.split('/').filter(Boolean).at(-1);
const DIFY_USER_ID = createId();

let currentConversationId = '';

function stripEmphasisMarkers(text) {
  return text.replace(/[*_]+/g, '');
}

async function readDifyResponse(response) {
  const contentType = response.headers?.get?.('content-type') || '';

  if (!contentType.includes('text/event-stream')) {
    return response.json().catch(() => ({}));
  }

  const result = { answer: '', conversation_id: '' };
  const body = await response.text();

  for (const line of body.split(/\r?\n/)) {
    if (!line.startsWith('data:')) {
      continue;
    }

    let event;

    try {
      event = JSON.parse(line.slice(5).trim());
    } catch {
      continue;
    }

    if (typeof event.conversation_id === 'string' && event.conversation_id) {
      result.conversation_id = event.conversation_id;
    }

    if (event.event === 'message' && typeof event.answer === 'string') {
      result.answer += event.answer;
    }

    if (event.event === 'error') {
      throw new Error(event.message || event.error || 'Dify 流式响应失败');
    }
  }

  return result;
}

async function getWebAppPassport() {
  const passportUrl = new URL(`${DIFY_API_BASE_URL}/passport`);
  passportUrl.searchParams.set('user_id', DIFY_USER_ID);

  const response = await fetch(passportUrl.toString(), {
    method: 'GET',
    headers: {
      'X-App-Code': DIFY_APP_CODE
    }
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok || typeof data.access_token !== 'string' || !data.access_token) {
    throw new Error(data.message || data.error || `Dify 访问凭证获取失败：${response.status}`);
  }

  return data.access_token;
}

export async function askQuestion(question) {
  const passport = await getWebAppPassport();
  const response = await fetch(`${DIFY_API_BASE_URL}/chat-messages`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-App-Code': DIFY_APP_CODE,
      'X-App-Passport': passport
    },
    body: JSON.stringify({
      inputs: {},
      query: question,
      response_mode: 'streaming',
      ...(currentConversationId ? { conversation_id: currentConversationId } : {})
    })
  });
  const data = await readDifyResponse(response);

  if (!response.ok) {
    throw new Error(data.message || data.error || `问答接口请求失败：${response.status}`);
  }

  if (typeof data.conversation_id === 'string' && data.conversation_id) {
    currentConversationId = data.conversation_id;
  }

  if (typeof data.answer !== 'string') {
    throw new Error('Dify 响应中没有 answer 字段');
  }

  return stripEmphasisMarkers(data.answer);
}
