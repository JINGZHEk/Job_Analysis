"""近重复检测单元测试。"""
from app.dedup import MinHash, NearDuplicateDetector, SimHash, char_shingles, tokenize


def test_simhash_similar_texts():
    sh = SimHash()
    a = sh.fingerprint(tokenize("负责深度学习模型训练与调优"))
    b = sh.fingerprint(tokenize("负责深度学习模型训练与调优"))
    assert sh.hamming(a, b) == 0


def test_simhash_different_texts():
    sh = SimHash()
    a = sh.fingerprint(tokenize("负责深度学习模型训练"))
    b = sh.fingerprint(tokenize("负责前端页面开发"))
    assert sh.hamming(a, b) > 0


def test_minhash_identical():
    mh = MinHash(128)
    a = mh.signature(tokenize("Python PyTorch Deep Learning"))
    b = mh.signature(tokenize("Python PyTorch Deep Learning"))
    assert mh.jaccard_estimate(a, b) == 1.0


def test_near_duplicate_detector():
    det = NearDuplicateDetector(hamming_threshold=3, jaccard_threshold=0.82)
    docs = {
        "a": "岗位职责：负责深度学习模型训练。任职要求：熟练 Python、PyTorch",
        "b": "岗位职责：负责深度学习模型训练。任职要求：熟练 Python、PyTorch",
        "c": "岗位职责：负责前端页面开发。任职要求：熟练 JavaScript、CSS",
    }
    res = det.detect(docs)
    assert res["a"]["duplication_risk"] >= 0.82
    assert res["c"]["duplication_risk"] < 0.82


def test_char_shingles():
    s = char_shingles("abcdef", 3)
    assert s == ["abc", "bcd", "cde", "def"]
