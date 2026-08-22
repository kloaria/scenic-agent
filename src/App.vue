<script setup>
import { computed, nextTick, ref } from 'vue';
import { askQuestion } from './api/chat';
import { getRandomQuestions } from './data/quickQuestions';
import { renderMarkdown } from './utils/markdown';

const input = ref('');
const isLoading = ref(false);
const messages = ref([]);
const displayedQuestions = ref(getRandomQuestions());
const messageList = ref(null);
const activeTurnId = ref('');
const hasStarted = computed(() => messages.value.length > 0);
const conversationTurns = computed(() =>
  messages.value
    .filter((message) => message.role === 'user')
    .map((userMessage) => {
      const assistantMessage = messages.value.find(
        (message) => message.role === 'assistant' && message.turnId === userMessage.turnId
      );

      return {
        id: userMessage.turnId,
        question: userMessage.content,
        answer: assistantMessage?.content || '正在生成回答...'
      };
    })
);

function scrollToBottom() {
  nextTick(() => {
    messageList.value?.scrollTo({
      top: messageList.value.scrollHeight,
      behavior: 'smooth'
    });
  });
}

function refreshQuickQuestions() {
  displayedQuestions.value = getRandomQuestions();
}

function summarize(text, length = 72) {
  return text.length > length ? `${text.slice(0, length)}...` : text;
}

function scrollToTurn(turnId) {
  activeTurnId.value = turnId;

  nextTick(() => {
    const target = messageList.value?.querySelector(`[data-turn-id="${turnId}"]`);
    target?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  });
}

async function sendQuestion(question = input.value) {
  const normalizedQuestion = question.trim();

  if (!normalizedQuestion || isLoading.value) {
    return;
  }

  const turnId = crypto.randomUUID();

  input.value = '';
  messages.value.push({
    id: crypto.randomUUID(),
    turnId,
    role: 'user',
    content: normalizedQuestion
  });
  activeTurnId.value = turnId;
  isLoading.value = true;
  scrollToBottom();

  try {
    const answer = await askQuestion(normalizedQuestion);

    messages.value.push({
      id: crypto.randomUUID(),
      turnId,
      role: 'assistant',
      content: answer
    });
    refreshQuickQuestions();
  } catch (error) {
    messages.value.push({
      id: crypto.randomUUID(),
      turnId,
      role: 'assistant',
      content: `抱歉，问答接口暂时不可用：${error instanceof Error ? error.message : '未知错误'}`
    });
  } finally {
    isLoading.value = false;
    scrollToBottom();
  }
}
</script>

<template>
  <main class="page-shell">
    <section class="chat-app" :class="{ 'has-chat': hasStarted }" aria-label="陈家祠讲解机器人">
      <header class="app-header">
        <div>
          <p class="eyebrow">Chen Clan Ancestral Hall</p>
          <h1>陈家祠讲解机器人</h1>
        </div>
      </header>

      <section v-if="!hasStarted" class="empty-state" aria-label="开始问答">
        <div class="empty-content">
          <h2>准备好了，随时开始</h2>

          <form class="composer center-composer" @submit.prevent="sendQuestion()">
            <input
              v-model="input"
              type="text"
              placeholder="输入你想了解的陈家祠问题..."
              autocomplete="off"
              :disabled="isLoading"
            />
            <button type="submit" class="send-button" title="发送" :disabled="!input.trim() || isLoading">
              <svg class="send-icon" viewBox="-24 -24 48 48" aria-hidden="true" focusable="false">
                <circle cx="0" cy="0" r="23" />
                <path d="M 0 9 L 0 -9" />
                <path d="M -7 -2 L 0 -9 L 7 -2" />
              </svg>
            </button>
          </form>

          <section class="quick-panel empty-quick-panel" aria-label="快捷问题">
            <div class="quick-panel-header">
              <span>猜你想问</span>
              <button type="button" class="icon-button" title="换一批问题" @click="refreshQuickQuestions">
                ↻
              </button>
            </div>
            <div class="quick-list">
              <button
                v-for="question in displayedQuestions"
                :key="question"
                type="button"
                class="quick-question"
                :disabled="isLoading"
                @click="sendQuestion(question)"
              >
                {{ question }}
              </button>
            </div>
          </section>
        </div>
      </section>

      <template v-else>
        <section class="conversation-area" aria-label="对话内容">
          <nav class="turn-index" aria-label="对话索引">
            <button
              v-for="turn in conversationTurns"
              :key="turn.id"
              type="button"
              class="turn-marker"
              :class="{ 'is-active': turn.id === activeTurnId }"
              :aria-label="`跳转到问题：${turn.question}`"
              @click="scrollToTurn(turn.id)"
            >
              <span></span>
              <div class="turn-preview" role="tooltip">
                <strong>{{ summarize(turn.question, 26) }}</strong>
                <p>{{ summarize(turn.answer) }}</p>
              </div>
            </button>
          </nav>

          <div ref="messageList" class="messages" aria-live="polite">
            <article
              v-for="message in messages"
              :key="message.id"
              class="message-row"
              :class="`is-${message.role}`"
              :data-turn-id="message.role === 'user' ? message.turnId : null"
            >
              <div class="avatar" aria-hidden="true">
                {{ message.role === 'assistant' ? 'AI' : '我' }}
              </div>
              <div
                v-if="message.role === 'assistant'"
                class="bubble markdown-body"
                v-html="renderMarkdown(message.content)"
              ></div>
              <p v-else class="bubble">{{ message.content }}</p>
            </article>

            <article v-if="isLoading" class="message-row is-assistant">
              <div class="avatar" aria-hidden="true">AI</div>
              <p class="bubble typing">
                <span></span>
                <span></span>
                <span></span>
              </p>
            </article>
          </div>
        </section>

        <section class="quick-panel" aria-label="快捷问题">
          <div class="quick-panel-header">
            <span>猜你想问</span>
            <button type="button" class="icon-button" title="换一批问题" @click="refreshQuickQuestions">
              ↻
            </button>
          </div>
          <div class="quick-list">
            <button
              v-for="question in displayedQuestions"
              :key="question"
              type="button"
              class="quick-question"
              :disabled="isLoading"
              @click="sendQuestion(question)"
            >
              {{ question }}
            </button>
          </div>
        </section>

        <form class="composer bottom-composer" @submit.prevent="sendQuestion()">
          <input
            v-model="input"
            type="text"
            placeholder="继续提问..."
            autocomplete="off"
            :disabled="isLoading"
          />
          <button type="submit" class="send-button" title="发送" :disabled="!input.trim() || isLoading">
            <svg class="send-icon" viewBox="-24 -24 48 48" aria-hidden="true" focusable="false">
              <circle cx="0" cy="0" r="23" />
              <path d="M 0 9 L 0 -9" />
              <path d="M -7 -2 L 0 -9 L 7 -2" />
            </svg>
          </button>
        </form>
      </template>
    </section>
  </main>
</template>
