#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
陈家祠知识库 FAISS 向量数据库 —— RAG 大模型集成示例

功能：
1. 加载向量数据库
2. 接收用户提问
3. 通过向量检索获取相关上下文
4. 将上下文注入 Prompt，调用大模型生成回答

运行方式：
    # 1. 设置 API Key（以 OpenAI 为例）
    set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Windows
    export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  # Linux/macOS

    # 2. 运行示例
    python rag_integration_example.py

兼容模型：
    - OpenAI GPT-4 / GPT-3.5
    - DeepSeek-V3 / DeepSeek-R1
    - 智谱 GLM-4
    - 其他兼容 OpenAI API 格式的模型
"""

# ============================================================================
# 强制单线程 + CPU 模式（必须在所有 import 之前设置）
# 避免 PyTorch 在多线程环境下死锁导致程序卡死
# ============================================================================
import os

# 网络镜像源（解决国内下载 HuggingFace 模型超时问题）
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

# 强制单线程模式
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# 模型缓存目录（可选，统一管理缓存文件）
os.environ["HF_HOME"] = r"./huggingface_cache"
os.environ["TRANSFORMERS_CACHE"] = r"./huggingface_cache"

import torch
torch.set_num_threads(1)
torch.set_default_device("cpu")

# ============================================================================
# 标准库导入
# ============================================================================
import json
import shutil
import tempfile
import textwrap
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# 兼容不同版本的 OpenAI SDK
try:
    from openai import OpenAI
except ImportError:
    print("[错误] 未安装 openai 包，请执行: pip install openai>=1.0.0")
    raise

# ============================================================================
# 配置区域 —— 请根据实际情况修改
# ============================================================================

# 向量数据库目录（请替换为实际路径）
DB_DIR = os.path.dirname(os.path.abspath(__file__))

# 大模型 API 配置
LLM_CONFIG = {
    # 方案 1: OpenAI 官方（默认）
    "base_url": "https://api.openai.com/v1",
    "api_key": os.environ.get("OPENAI_API_KEY", ""),
    "model": "gpt-4o-mini",  # 或 "gpt-4", "gpt-3.5-turbo"

    # 方案 2: DeepSeek（取消下面注释即可）
    # "base_url": "https://api.deepseek.com/v1",
    # "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
    # "model": "deepseek-chat",

    # 方案 3: 智谱 GLM（取消下面注释即可）
    # "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    # "api_key": os.environ.get("ZHIPU_API_KEY", ""),
    # "model": "glm-4",
}

# Embedding 模型
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"

# 检索参数
RETRIEVAL_TOP_K = 5           # 检索返回的文档片段数量
MAX_CONTEXT_LENGTH = 3000     # 上下文最大字符数（防止超出模型上下文窗口）


# ============================================================================
# 向量检索模块
# ============================================================================

def load_index_safe(index_path: str):
    """安全加载 FAISS 索引（兼容 Windows 中文路径）。"""
    try:
        return faiss.read_index(index_path)
    except Exception:
        tmp_path = os.path.join(tempfile.gettempdir(), "faiss_tmp_read.index")
        shutil.copy(index_path, tmp_path)
        index = faiss.read_index(tmp_path)
        os.remove(tmp_path)
        return index


def load_vector_db(db_dir: str):
    """加载向量数据库。"""
    index_path = os.path.join(db_dir, "faiss_index.index")
    metadata_path = os.path.join(db_dir, "metadata.json")

    print(f"[加载] 索引: {index_path}")
    index = load_index_safe(index_path)
    print(f"[加载] 索引维度: {index.d}, 向量数: {index.ntotal}")

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    print(f"[加载] 元数据: {len(metadata)} 条")

    return index, metadata


def load_embedding_model(model_name: str = EMBEDDING_MODEL):
    """加载 Embedding 模型（强制 CPU 模式）。"""
    print(f"[加载] Embedding 模型: {model_name}")
    model = SentenceTransformer(model_name, device="cpu")
    print("[加载] 模型加载完成（CPU 模式）")
    return model


def encode_query(model, query: str):
    """
    将查询文本编码为向量（手动归一化，避免额外开销）。
    返回: shape=(1, dim) 的 float32 向量
    """
    vec = model.encode([query], normalize_embeddings=False)
    # 手动归一化（L2 范数）
    vec = vec / np.linalg.norm(vec, axis=1, keepdims=True)
    return vec.astype("float32")


def retrieve_documents(index, metadata, model, query: str, top_k: int = RETRIEVAL_TOP_K):
    """
    向量检索：将查询编码后搜索最相似的文档片段。
    返回: list[dict] 每个元素包含 score, content, source_file, chapter
    """
    query_embedding = encode_query(model, query)
    distances, indices = index.search(query_embedding, top_k)

    docs = []
    for i in range(top_k):
        idx = int(indices[0][i])
        if idx < 0 or idx >= len(metadata):
            continue
        meta = metadata[idx]
        docs.append({
            "score": float(distances[0][i]),
            "content": meta["content"],
            "source_file": meta["source_file"],
            "chapter": meta["chapter"]
        })
    return docs


# ============================================================================
# 大模型调用模块
# ============================================================================

def build_prompt(query: str, retrieved_docs: list) -> str:
    """
    构造 RAG Prompt。
    将检索到的文档片段拼接为参考资料，注入系统提示中。
    """
    # 1. 构建参考资料文本
    context_parts = []
    total_len = 0
    for i, doc in enumerate(retrieved_docs, 1):
        snippet = f"[{i}] 来源: {doc['source_file']} | 章节: {doc['chapter']}\n{doc['content']}\n"
        if total_len + len(snippet) > MAX_CONTEXT_LENGTH:
            break
        context_parts.append(snippet)
        total_len += len(snippet)

    context_text = "\n".join(context_parts)

    # 2. 构造完整 Prompt
    prompt = textwrap.dedent(f"""\
    你是一位广东民间工艺博物馆（陈家祠）的专业导游和知识顾问。
    请严格根据以下参考资料回答用户的问题。如果参考资料中没有相关信息，请诚实说明，不要编造。

    参考资料：
    {context_text}

    用户问题：{query}

    请用中文回答，回答应条理清晰、信息准确。如果涉及展品，请尽量说明其年代、材质和艺术特色。
    """)
    return prompt


def call_llm(prompt: str, config: dict = None) -> str:
    """
    调用大模型 API 生成回答。
    默认使用 OpenAI 兼容格式，可替换为 DeepSeek / 智谱 GLM 等。
    """
    cfg = config or LLM_CONFIG

    api_key = cfg.get("api_key", "")
    if not api_key:
        raise ValueError(
            "API Key 未设置。请设置环境变量: \n"
            "  Windows: set OPENAI_API_KEY=sk-xxxxx\n"
            "  Linux/macOS: export OPENAI_API_KEY=sk-xxxxx"
        )

    client = OpenAI(
        base_url=cfg.get("base_url", "https://api.openai.com/v1"),
        api_key=api_key,
    )

    response = client.chat.completions.create(
        model=cfg.get("model", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "你是一个专业的博物馆知识问答助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,   # 低温度，减少幻觉
        max_tokens=1024,
    )

    return response.choices[0].message.content


# ============================================================================
# RAG 主流程
# ============================================================================

def rag_pipeline(query: str, index, metadata, model, llm_config: dict = None) -> dict:
    """
    完整的 RAG 流程：
    用户提问 -> 向量检索 -> 构造 Prompt -> 调用大模型 -> 返回回答

    返回:
        dict: { "query": str, "retrieved_docs": list, "prompt": str, "answer": str }
    """
    print(f"\n[1/4] 检索相关文档...")
    docs = retrieve_documents(index, metadata, model, query, top_k=RETRIEVAL_TOP_K)
    print(f"      找到 {len(docs)} 条相关文档")
    for d in docs:
        print(f"      - [{d['score']:.4f}] {d['source_file']} / {d['chapter']}")

    print(f"\n[2/4] 构造 Prompt...")
    prompt = build_prompt(query, docs)
    print(f"      Prompt 长度: {len(prompt)} 字符")

    print(f"\n[3/4] 调用大模型...")
    try:
        answer = call_llm(prompt, llm_config)
    except Exception as e:
        answer = f"[错误] 调用大模型失败: {e}"

    print(f"\n[4/4] 完成。")

    return {
        "query": query,
        "retrieved_docs": docs,
        "prompt": prompt,
        "answer": answer,
    }


def print_rag_result(result: dict):
    """格式化打印 RAG 结果。"""
    print("\n" + "=" * 80)
    print("【RAG 问答结果】")
    print("=" * 80)
    print(f"\n❓ 用户问题: {result['query']}")
    print(f"\n📚 检索到的文档片段:")
    for i, doc in enumerate(result["retrieved_docs"], 1):
        preview = doc["content"][:120] + "..." if len(doc["content"]) > 120 else doc["content"]
        print(f"   [{i}] ({doc['score']:.4f}) {preview}")

    print(f"\n🤖 大模型回答:")
    print("-" * 80)
    print(result["answer"])
    print("-" * 80)


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 80)
    print("  陈家祠知识库 RAG 集成示例")
    print("=" * 80)

    # 1. 加载向量数据库
    index, metadata = load_vector_db(DB_DIR)

    # 2. 加载 Embedding 模型（强制 CPU 模式）
    model = load_embedding_model()

    # 3. 定义测试问题
    test_queries = [
        "陈家祠的建筑特色是什么？",
        "聚贤堂有哪些展品？",
        "洗手间在哪里？",
    ]

    # 4. 执行 RAG 流程
    for q in test_queries:
        result = rag_pipeline(q, index, metadata, model)
        print_rag_result(result)

    # 5. 交互式问答
    print("\n" + "=" * 80)
    print("  交互式问答模式（输入 exit 退出）")
    print("=" * 80)

    while True:
        try:
            user_query = input("\n请输入问题: ").strip()
            if user_query.lower() in ("exit", "quit", "退出"):
                break
            if not user_query:
                continue

            result = rag_pipeline(user_query, index, metadata, model)
            print_rag_result(result)

        except KeyboardInterrupt:
            print("\n退出")
            break
        except Exception as e:
            print(f"[错误] {e}")


if __name__ == "__main__":
    main()