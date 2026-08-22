export const quickQuestions = [
  '陈家祠的开放时间是什么？',
  '第一次去陈家祠推荐怎么看？',
  '陈家祠最值得看的建筑细节有哪些？',
  '陈家祠为什么被称为岭南建筑艺术明珠？',
  '陈家祠有哪些展厅？',
  '游览陈家祠大概需要多长时间？',
  '陈家祠在哪里，怎么去比较方便？',
  '陈家祠适合拍照的地方有哪些？',
  '陈家祠和广东民间工艺博物馆是什么关系？',
  '陈家祠的木雕、砖雕和石雕有什么特点？',
  '陈家祠适合亲子游览吗？',
  '陈家祠附近还有哪些地方可以一起逛？'
];

export function getRandomQuestions() {
  const count = Math.random() > 0.5 ? 4 : 3;

  return [...quickQuestions]
    .sort(() => Math.random() - 0.5)
    .slice(0, count);
}
