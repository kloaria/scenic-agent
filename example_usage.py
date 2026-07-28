#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
陈家祠知识库 FAISS 向量数据库 —— 基础检索示例

功能：
1. 加载 FAISS 索引和元数据
2. 加载 BAAI/bge-large-zh-v1.5 Embedding 模型
3. 执行语义检索，返回最相关的文本片段

运行方式：
    python example_usage.py
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
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ============================================================================
# 配置区域 —— 请根据实际情况修改
# ============================================================================

# 向量数据库所在目录（请替换为实际路径）
# 注意：路径中不能包含中文字符，否则可能会报错，建议保存到英文路径。
# Windows 示例: DB_DIR = r"C:\Users\xxx\陈家祠向量数据库_交付包"
# Linux/macOS 示例: DB_DIR = "/home/xxx/陈家祠向量数据库_交付包"
DB_DIR = os.path.dirname(os.path.abspath(__file__))

INDEX_FILENAME = "faiss_index.index"
METADATA_FILENAME = "metadata.json"

# Embedding 模型名称
EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"

# 默认返回的相似结果数量
DEFAULT_TOP_K = 5


# ============================================================================
# 工具函数
# ============================================================================

def load_index_safe(index_path: str):
    """
    安全加载 FAISS 索引文件。
    针对 Windows 中文路径兼容性问题，自动使用临时文件中转。
    """
    try:
        return faiss.read_index(index_path)
    except Exception as e:
        print(f"  [提示] 直接加载失败，使用临时文件方式: {e}")
        tmp_dir = tempfile.gettempdir()
        tmp_path = os.path.join(tmp_dir, "faiss_tmp_read.index")
        shutil.copy(index_path, tmp_path)
        index = faiss.read_index(tmp_path)
        os.remove(tmp_path)
        return index


def load_vector_db(db_dir: str):
    """
    加载向量数据库（索引 + 元数据）。
    返回: (faiss_index, metadata_list)
    """
    index_path = os.path.join(db_dir, INDEX_FILENAME)
    metadata_path = os.path.join(db_dir, METADATA_FILENAME)

    print(f"[加载] 索引文件: {index_path}")
    index = load_index_safe(index_path)
    print(f"[加载] 索引维度: {index.d}, 向量数: {index.ntotal}")

    print(f"[加载] 元数据: {metadata_path}")
    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    print(f"[加载] 元数据条目数: {len(metadata)}")

    return index, metadata


def load_embedding_model(model_name: str = EMBEDDING_MODEL):
    """
    加载 Embedding 模型（强制 CPU 模式）。
    """
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


def search(index, metadata, model, query: str, top_k: int = DEFAULT_TOP_K):
    """
    执行语义检索。

    参数:
        index:     FAISS 索引对象
        metadata:  元数据列表
        model:     SentenceTransformer 模型
        query:     用户查询文本
        top_k:     返回最相似的结果数量

    返回:
        list[dict]: 每个 dict 包含 rank, score, content, source_file, chapter
    """
    # 1. 将查询文本编码为向量（手动归一化）
    query_embedding = encode_query(model, query)

    # 2. 在 FAISS 索引中搜索
    distances, indices = index.search(query_embedding, top_k)

    # 3. 组装结果
    results = []
    for i in range(top_k):
        idx = int(indices[0][i])
        score = float(distances[0][i])
        if idx < 0 or idx >= len(metadata):
            continue
        meta = metadata[idx]
        results.append({
            "rank": i + 1,
            "score": score,
            "content": meta["content"],
            "source_file": meta["source_file"],
            "chapter": meta["chapter"]
        })
    return results


def print_results(query: str, results: list):
    """格式化打印检索结果。"""
    print("\n" + "=" * 80)
    print(f"【查询】{query}")
    print("=" * 80)
    for r in results:
        print(f"\n[排名 {r['rank']}]  相似度: {r['score']:.4f}")
        print(f"  来源: {r['source_file']}")
        print(f"  章节: {r['chapter']}")
        content = r['content']
        preview = content[:250] + "..." if len(content) > 250 else content
        print(f"  内容: {preview}")


# ============================================================================
# 主程序
# ============================================================================

def main():
    print("=" * 80)
    print("  陈家祠知识库 FAISS 向量检索 —— 基础使用示例")
    print("=" * 80)

    # 1. 加载向量数据库
    index, metadata = load_vector_db(DB_DIR)

    # 2. 加载 Embedding 模型
    model = load_embedding_model()

    # 3. 定义测试查询
    test_queries = [
        "陈家祠的建筑特色是什么？",
        "聚贤堂有哪些展品？",
        "洗手间在哪里？",
    ]

    # 4. 执行检索并打印结果
    for q in test_queries:
        results = search(index, metadata, model, q, top_k=DEFAULT_TOP_K)
        print_results(q, results)

    print("\n" + "=" * 80)
    print("  示例运行完毕。您可以直接修改 test_queries 列表测试其他问题。")
    print("=" * 80)


if __name__ == "__main__":
    main()