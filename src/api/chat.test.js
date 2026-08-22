import assert from 'node:assert/strict';
import { afterEach, test } from 'node:test';
import { askQuestion } from './chat.js';

const originalFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = originalFetch;
});

test('askQuestion posts the question to the local chat proxy and returns its answer', async () => {
  const calls = [];

  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });

    return {
      ok: true,
      json: async () => ({ answer: '陈家祠是一座岭南传统建筑代表。' })
    };
  };

  const answer = await askQuestion('陈家祠有什么建筑特色？');

  assert.equal(answer, '陈家祠是一座岭南传统建筑代表。');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/api/chat');
  assert.equal(calls[0].options.method, 'POST');
  assert.equal(calls[0].options.headers['Content-Type'], 'application/json');
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    question: '陈家祠有什么建筑特色？'
  });
});

test('askQuestion throws a readable error when the chat proxy fails', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    json: async () => ({ error: 'Dify service unavailable' })
  });

  await assert.rejects(
    () => askQuestion('开放时间是什么？'),
    /Dify service unavailable/
  );
});

test('askQuestion sends the previous conversation id on follow-up questions', async () => {
  const bodies = [];

  globalThis.fetch = async (_, options) => {
    bodies.push(JSON.parse(options.body));

    return {
      ok: true,
      json: async () => ({
        answer: '回答',
        conversationId: 'conversation-001'
      })
    };
  };

  await askQuestion('第一问');
  await askQuestion('第二问');

  assert.deepEqual(bodies, [
    { question: '第一问' },
    { question: '第二问', conversationId: 'conversation-001' }
  ]);
});
