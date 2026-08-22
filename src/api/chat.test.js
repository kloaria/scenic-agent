import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { askQuestion } from './chat.js';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('askQuestion uses the configured Dify web app while keeping the custom UI', async () => {
  const calls = [];

  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });

    if (url.startsWith('https://udify.app/api/passport')) {
      return {
        ok: true,
        json: async () => ({ access_token: 'web-passport-token' })
      };
    }

    return {
      ok: true,
      json: async () => ({
        event: 'message',
        answer: '***陈家祠***是一座__岭南传统建筑__代表。\n**值得参观。**'
      })
    };
  };

  const answer = await askQuestion('陈家祠有什么建筑特色？');

  assert.equal(answer, '陈家祠是一座岭南传统建筑代表。\n值得参观。');
  assert.equal(calls.length, 2);
  const passportUrl = new URL(calls[0].url);
  assert.equal(passportUrl.origin + passportUrl.pathname, 'https://udify.app/api/passport');
  assert.ok(passportUrl.searchParams.get('user_id'));
  assert.equal(calls[0].options.method, 'GET');
  assert.equal(calls[0].options.headers['X-App-Code'], 'G1lXUZh9LgrQ0AsT');
  assert.equal(calls[1].url, 'https://udify.app/api/chat-messages');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.headers['Content-Type'], 'application/json');
  assert.equal(calls[1].options.headers['X-App-Code'], 'G1lXUZh9LgrQ0AsT');
  assert.equal(calls[1].options.headers['X-App-Passport'], 'web-passport-token');
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    inputs: {},
    query: '陈家祠有什么建筑特色？',
    response_mode: 'blocking'
  });
});

test('askQuestion preserves unmatched emphasis punctuation', async () => {
  globalThis.fetch = async (url) => {
    if (url.startsWith('https://udify.app/api/passport')) {
      return {
        ok: true,
        json: async () => ({ access_token: 'web-passport-token' })
      };
    }

    return {
      ok: true,
      json: async () => ({
        event: 'message',
        answer: '**提示***与__说明___'
      })
    };
  };

  assert.equal(await askQuestion('测试强调符号'), '提示*与说明_');
});

test('askQuestion throws a readable error when the Dify web app fails', async () => {
  globalThis.fetch = async (url) => {
    if (url.startsWith('https://udify.app/api/passport')) {
      return {
        ok: true,
        json: async () => ({ access_token: 'web-passport-token' })
      };
    }

    return {
      ok: false,
      status: 502,
      json: async () => ({ message: 'Dify service unavailable' })
    };
  };

  await assert.rejects(
    () => askQuestion('开放时间是什么？'),
    /Dify service unavailable/
  );
});

test('askQuestion sends the previous conversation id on follow-up questions', async () => {
  const bodies = [];
  const passportUserIds = [];

  globalThis.fetch = async (url, options) => {
    if (url.startsWith('https://udify.app/api/passport')) {
      passportUserIds.push(new URL(url).searchParams.get('user_id'));

      return {
        ok: true,
        json: async () => ({ access_token: 'web-passport-token' })
      };
    }

    bodies.push(JSON.parse(options.body));

    return {
      ok: true,
      json: async () => ({
        event: 'message',
        answer: '回答',
        conversation_id: 'conversation-002'
      })
    };
  };

  await askQuestion('第一问');
  await askQuestion('第二问');

  assert.equal(passportUserIds.length, 2);
  assert.ok(passportUserIds[0]);
  assert.equal(passportUserIds[0], passportUserIds[1]);
  assert.deepEqual(bodies, [
    {
      inputs: {},
      query: '第一问',
      response_mode: 'blocking'
    },
    {
      inputs: {},
      query: '第二问',
      response_mode: 'blocking',
      conversation_id: 'conversation-002'
    }
  ]);
});
