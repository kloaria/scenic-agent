let currentConversationId = '';

export async function askQuestion(question) {
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      question,
      ...(currentConversationId ? { conversationId: currentConversationId } : {})
    })
  });
  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `问答接口请求失败：${response.status}`);
  }

  if (typeof data.conversationId === 'string' && data.conversationId) {
    currentConversationId = data.conversationId;
  }

  return data.answer;
}
