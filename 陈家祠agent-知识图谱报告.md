# 陈家祠智能系统｜知识图谱报告

> 项目名称：scenic-agent
>
> 负责模块：知识图谱构建
>
> 负责人：谢佩珈
>
> 最终交付：`neo4j-2026-08-26T11-43-39.dump`
>
> 仓库地址：`kloaria/scenic-agent`（`module4` 分支）

---

## 一、项目简介

### 1.1 项目背景

陈家祠（陈氏书院）是岭南建筑艺术的集大成者，也是广州重要的文化旅游地标。本项目旨在构建一个基于大语言模型的智能旅游 Agent（scenic-agent），为游客提供景点推荐、行程规划、展品讲解和个性化旅游辅助服务。其中，陈家祠导览子系统支持用户通过上传展品图片，由 AI 进行图像识别并自动匹配知识图谱中的对应展品实体，返回结构化的展品讲解信息。


### 1.2 图谱信息


Name: scenic‑csv‑test-6

Connection URI: neo4j://127.0.0.1:7687

Version: 2026.07.1

Database user: neo4j

Password: 12345678

---





## 二、最终成果与交付

###  交付文件

最终交付物已全部上传至 GitHub 仓库 `kloaria/scenic-agent` 的 `module4` 分支：

| 文件名 | 类型 | 说明 |
|--------|------|------|
| `neo4j-2026-08-26T11-43-39.dump` | 数据库备份 | 包含全部业务实体与同义词本体的最终 Neo4j 数据库备份，可直接导入部署 |
| `architectural_visual_features.csv` | 图谱导入 | 建筑装饰展品视觉特征表（281条） |
| `collection_visual_features.csv` | 图谱导入 | 馆藏文物视觉特征表（48条） |
| `visual_features.csv` | 图谱导入 | 通用视觉特征词表（1000条） |
| `nodes.csv` | 图谱导入 | 全量核心实体节点表 |
| `semantic_relations.csv` | 图谱导入 | 语义关系表 |
| `relationships_check.csv` | 图谱导入 | 关系校验表 |
| `entities.json` | 源数据 | 实体数据 JSON（后端组员提供） |
| `entity_schema.json` | 源数据 | 实体 Schema 定义 JSON（后端组员提供） |
| `relationships.json` | 源数据 | 关系数据 JSON（后端组员提供） |
| `README.md` | 项目文档 | scenic-agent 项目总介绍 |
| `.gitignore` | Git 配置 | Git 忽略规则 |




## 三、后续维护与优化方向

### 3.1 同义词持续扩充

根据实际图片识别测试结果，持续收集未命中的识别词，补充对应的变体词映射。可通过以下 Cypher 语句快速新增：

```cypher
MERGE (ft:FeatureTerm{name:"标准词"})
MERGE (vs:VisualSynonym{name:"新变体词"})
MERGE (ft)-[:HAS_SYNONYM]->(vs);
```

### 3.2 数据库约束完善

在确定部署环境的 Neo4j 版本后，可为 `FeatureTerm.name` 和 `VisualSynonym.name` 添加唯一约束，从数据库层面保证节点不重复。

### 3.3 模糊匹配增强

对于未命中同义词映射的识别词，可引入字符串相似度算法（如 Levenshtein 编辑距离、Jaccard 相似度）进行模糊匹配，进一步提升召回率。

### 3.4 低视觉特征展品处理

当前所有展品均带有非空 `visual_keywords`。如后续新增无视觉关键词的展品，可启用 `LowVisualFeature` 标签，在检索时对该类展品做降权处理。

### 3.5 图谱可视化维护

可利用 Neo4j Bloom 构建同义词本体的可视化视图，直观展示标准词与变体词的映射网络，便于后续维护和团队展示