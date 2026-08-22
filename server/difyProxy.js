export function buildDifyRequest({ question, user, conversationId }) {
  const request = {
    inputs: {},
    query: question,
    response_mode: 'blocking',
    user
  };

  if (conversationId) {
    request.conversation_id = conversationId;
  }

  return request;
}

export function extractDifyAnswer(data) {
  if (!data || typeof data.answer !== 'string') {
    throw new Error('Dify 响应中没有 answer 字段');
  }

  return data.answer;
}

function sendJson(res, statusCode, body) {
  res.statusCode = statusCode;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.end(JSON.stringify(body));
}

function readRequestBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';

    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => resolve(body));
    req.on('error', reject);
  });
}

function getDifyErrorMessage(data, fallback) {
  return data?.message || data?.error || fallback;
}

export function createDifyProxyMiddleware({
  endpoint,
  apiKey,
  fetchImpl = fetch,
  user = 'chenjiaci-web'
}) {
  return async function difyProxyMiddleware(req, res, next) {
    const pathname = new URL(req.url, 'http://localhost').pathname;

    if (pathname !== '/api/chat') {
      next();
      return;
    }

    if (req.method !== 'POST') {
      sendJson(res, 405, { error: 'Only POST is supported' });
      return;
    }

    if (!apiKey || !endpoint) {
      sendJson(res, 500, { error: 'Dify API 配置缺失，请检查 .env.local' });
      return;
    }

    try {
      const rawBody = await readRequestBody(req);
      const body = JSON.parse(rawBody || '{}');
      const question = typeof body.question === 'string' ? body.question.trim() : '';
      const conversationId =
        typeof body.conversationId === 'string' ? body.conversationId.trim() : '';

      if (!question) {
        sendJson(res, 400, { error: '问题不能为空' });
        return;
      }

      const difyResponse = await fetchImpl(endpoint, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${apiKey}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(buildDifyRequest({ question, user, conversationId }))
      });
      const difyData = await difyResponse.json().catch(() => ({}));

      if (!difyResponse.ok) {
        sendJson(res, difyResponse.status, {
          error: getDifyErrorMessage(difyData, 'Dify 请求失败')
        });
        return;
      }

      sendJson(res, 200, {
        answer: extractDifyAnswer(difyData),
        conversationId: difyData.conversation_id
      });
    } catch (error) {
      sendJson(res, 500, {
        error: error instanceof Error ? error.message : '问答接口请求失败'
      });
    }
  };
}
