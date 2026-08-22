import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildDifyRequest, extractDifyAnswer } from './difyProxy.js';

test('buildDifyRequest maps a front-end question to Dify chat-messages format', () => {
  const request = buildDifyRequest({
    question: '陈家祠有什么建筑特色？',
    user: 'chenjiaci-web'
  });

  assert.deepEqual(request, {
    inputs: {},
    query: '陈家祠有什么建筑特色？',
    response_mode: 'blocking',
    user: 'chenjiaci-web'
  });
});

test('buildDifyRequest includes the conversation id for follow-up questions', () => {
  const request = buildDifyRequest({
    question: '继续说说木雕',
    user: 'chenjiaci-web',
    conversationId: 'conversation-001'
  });

  assert.equal(request.conversation_id, 'conversation-001');
});

test('extractDifyAnswer returns the Dify answer text', () => {
  assert.equal(
    extractDifyAnswer({ answer: '陈家祠以木雕、砖雕、石雕见长。' }),
    '陈家祠以木雕、砖雕、石雕见长。'
  );
});

test('extractDifyAnswer rejects malformed Dify responses', () => {
  assert.throws(() => extractDifyAnswer({}), /Dify 响应中没有 answer 字段/);
});
