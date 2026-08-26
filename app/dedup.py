"""近重复检测：SimHash（海明距离）与 MinHash（Jaccard 相似度）。"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Iterable

_TOKEN_RE = re.compile(r"[一-鿿]|[a-zA-Z0-9_]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def char_shingles(text: str, k: int = 3) -> list[str]:
    """字符级 k-shingle，用于捕捉逐字复制（抄袭检测更强）。"""
    text = text.lower()
    return [text[i:i + k] for i in range(len(text) - k + 1)]


def _hash_token(token: str, seed: int) -> int:
    h = hashlib.md5(f"{seed}:{token}".encode("utf-8")).hexdigest()
    return int(h[:16], 16)


class SimHash:
    """64 位 SimHash，用于海明距离判定模板复制。"""

    def __init__(self, num_bits: int = 64):
        self.num_bits = num_bits

    def fingerprint(self, tokens: Iterable[str]) -> int:
        vector = [0] * self.num_bits
        for token in tokens:
            h = _hash_token(token, 0)
            for i in range(self.num_bits):
                vector[i] += 1 if (h >> i) & 1 else -1
        fp = 0
        for i in range(self.num_bits):
            if vector[i] > 0:
                fp |= 1 << i
        return fp

    @staticmethod
    def hamming(a: int, b: int) -> int:
        return bin(a ^ b).count("1")


class MinHash:
    """基于多排列的最小哈希，估计 Jaccard 相似度。"""

    def __init__(self, num_perm: int = 128):
        self.num_perm = num_perm

    def signature(self, tokens: Iterable[str]) -> list[int]:
        toks = set(tokens)
        if not toks:
            return [0] * self.num_perm
        sig = []
        for seed in range(self.num_perm):
            sig.append(min(_hash_token(t, seed) for t in toks))
        return sig

    @staticmethod
    def jaccard_estimate(a: list[int], b: list[int]) -> float:
        n = min(len(a), len(b))
        if n == 0:
            return 0.0
        matches = sum(1 for i in range(n) if a[i] == b[i])
        return matches / n


class NearDuplicateDetector:
    """将一批文档分组成重复簇，返回每条文档的 duplication_risk。"""

    def __init__(
        self,
        hamming_threshold: int = 3,
        jaccard_threshold: float = 0.82,
        num_perm: int = 128,
        use_char_shingle: bool = True,
    ):
        self.simhash = SimHash()
        self.minhash = MinHash(num_perm)
        self.hamming_threshold = hamming_threshold
        self.jaccard_threshold = jaccard_threshold
        self.use_char_shingle = use_char_shingle

    def _features(self, text: str) -> list[str]:
        if self.use_char_shingle:
            return char_shingles(text, 3)
        return tokenize(text)

    def build_index(self, docs: dict[str, str]) -> dict[str, dict]:
        """docs: {doc_id: text} -> {doc_id: {simhash, minhash_sig, tokens}}"""
        index = {}
        for doc_id, text in docs.items():
            feats = self._features(text)
            index[doc_id] = {
                "simhash": self.simhash.fingerprint(feats),
                "minhash": self.minhash.signature(feats),
                "tokens": feats,
            }
        return index

    def detect(self, docs: dict[str, str]) -> dict[str, dict]:
        """返回 {doc_id: {duplicate_group, duplication_risk, near_duplicates}}。"""
        index = self.build_index(docs)
        ids = list(index.keys())
        # 用 SimHash 分桶做候选
        seen = {}
        groups: dict[str, list[str]] = {}
        result: dict[str, dict] = {}

        for doc_id in ids:
            fp = index[doc_id]["simhash"]
            best_group = None
            for other in seen:
                if self.simhash.hamming(fp, seen[other]) <= self.hamming_threshold:
                    best_group = other
                    break
            if best_group is None:
                best_group = doc_id
                seen[doc_id] = fp
                groups[doc_id] = [doc_id]
            else:
                groups[best_group].append(doc_id)

        # 对每个簇内文档用 MinHash 精确评估相似度
        for doc_id in ids:
            group = None
            for gid, members in groups.items():
                if doc_id in members:
                    group = gid
                    break
            risk = 0.0
            near = []
            if group is not None and len(groups[group]) > 1:
                risk = 0.6
                for other in groups[group]:
                    if other == doc_id:
                        continue
                    sim = self.minhash.jaccard_estimate(
                        index[doc_id]["minhash"], index[other]["minhash"]
                    )
                    if sim >= self.jaccard_threshold:
                        near.append(other)
                        risk = max(risk, sim)
            result[doc_id] = {
                "duplicate_group": group if len(groups.get(group, [])) > 1 else None,
                "duplication_risk": round(risk, 4),
                "near_duplicates": near,
            }
        return result
