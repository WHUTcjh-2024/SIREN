"""
本地知识库 RAG 检索：TF-IDF + 字符 n-gram，无需额外向量模型下载。
"""

import os
import re
from typing import List, Dict, Optional

_retriever_instance: Optional['KnowledgeRetriever'] = None


class KnowledgeRetriever:
    def __init__(self, kb_dir: str, max_chunk_chars: int = 1400, min_chunk_chars: int = 80):
        self.kb_dir = os.path.abspath(kb_dir)
        self.max_chunk_chars = max_chunk_chars
        self.min_chunk_chars = min_chunk_chars
        self.chunks: List[Dict] = []
        self._vectorizer = None
        self._matrix = None
        self._ready = False

    def load_and_index(self) -> int:
        self.chunks = []
        if not os.path.isdir(self.kb_dir):
            return 0
        for root, _, files in os.walk(self.kb_dir):
            for name in sorted(files):
                if not name.endswith('.md'):
                    continue
                path = os.path.join(root, name)
                rel = os.path.relpath(path, self.kb_dir).replace('\\', '/')
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        text = f.read()
                except OSError:
                    continue
                for chunk in self._split_document(text, rel):
                    if len(chunk['text'].strip()) >= self.min_chunk_chars:
                        self.chunks.append(chunk)
        self._build_tfidf()
        self._ready = bool(self.chunks)
        return len(self.chunks)

    def _split_document(self, text: str, source: str) -> List[Dict]:
        text = text.strip()
        if not text:
            return []
        parts = re.split(r'(?=^##\s)', text, flags=re.MULTILINE)
        sections = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = part.split('\n', 1)
            title = lines[0].strip().lstrip('#').strip() if lines else source
            body = lines[1].strip() if len(lines) > 1 else part
            if not body:
                body = part
            sections.append((title, body))

        if len(sections) <= 1 and len(text) > self.max_chunk_chars:
            sections = [('全文', text)]

        out = []
        for title, body in sections:
            paras = [p.strip() for p in re.split(r'\n\s*\n', body) if p.strip()]
            buf = ''
            for para in paras:
                if len(buf) + len(para) + 2 <= self.max_chunk_chars:
                    buf = (buf + '\n\n' + para).strip() if buf else para
                else:
                    if buf:
                        out.append(self._make_chunk(source, title, buf))
                    if len(para) > self.max_chunk_chars:
                        for i in range(0, len(para), self.max_chunk_chars):
                            out.append(self._make_chunk(
                                source, title, para[i:i + self.max_chunk_chars]
                            ))
                        buf = ''
                    else:
                        buf = para
            if buf:
                out.append(self._make_chunk(source, title, buf))
        return out

    @staticmethod
    def _make_chunk(source: str, title: str, text: str) -> Dict:
        return {
            'source': source,
            'title': title,
            'text': f'【{source} · {title}】\n{text}',
        }

    def _build_tfidf(self):
        if not self.chunks:
            self._vectorizer = None
            self._matrix = None
            return
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            self._vectorizer = None
            self._matrix = None
            return
        corpus = [c['text'] for c in self.chunks]
        self._vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            max_features=50000,
            sublinear_tf=True,
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    def retrieve(
        self,
        query: str,
        top_k: int = 6,
        min_score: float = 0.04,
        allow_weak_fallback: bool = False,
    ) -> List[Dict]:
        if not self._ready or self._matrix is None:
            return []
        try:
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            return self._retrieve_keyword(query, top_k)

        qv = self._vectorizer.transform([query])
        scores = cosine_similarity(qv, self._matrix).flatten()
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        hits = []
        for idx, score in ranked[: top_k * 3]:
            if score < min_score:
                continue
            item = dict(self.chunks[idx])
            item['score'] = float(score)
            hits.append(item)
            if len(hits) >= top_k:
                break
        if not hits and allow_weak_fallback and ranked:
            idx, score = ranked[0]
            item = dict(self.chunks[idx])
            item['score'] = float(score)
            hits.append(item)
        return hits

    @staticmethod
    def is_covered(hits: List[Dict], coverage_min_score: float = 0.08, coverage_min_keyword_hits: int = 2) -> bool:
        """判断检索结果是否足以视为知识库已覆盖该问题。"""
        if not hits:
            return False
        top = float(hits[0].get('score', 0))
        # TF-IDF 余弦相似度 ∈ [0, 1]；关键词回退得分为命中次数（通常 > 1）
        if top <= 1.0:
            return top >= coverage_min_score
        return top >= coverage_min_keyword_hits

    def _retrieve_keyword(self, query: str, top_k: int) -> List[Dict]:
        keys = set(re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', query))
        scored = []
        for i, c in enumerate(self.chunks):
            t = c['text']
            s = sum(t.count(k) for k in keys)
            if s > 0:
                scored.append((i, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [dict(self.chunks[i], score=float(s)) for i, s in scored[:top_k]]

    @staticmethod
    def format_context(hits: List[Dict]) -> str:
        if not hits:
            return '（未检索到相关知识库条目，请依据系统角色设定谨慎回答，并建议学生查阅教材或询问教师。）'
        blocks = []
        for i, h in enumerate(hits, 1):
            blocks.append(f"### 检索片段 {i}（相关度 {h.get('score', 0):.3f}）\n{h['text']}")
        return '\n\n'.join(blocks)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)


def get_retriever(kb_dir: Optional[str] = None, force_reload: bool = False) -> KnowledgeRetriever:
    global _retriever_instance
    if _retriever_instance is not None and not force_reload:
        return _retriever_instance
    from config import RAG_CONFIG
    base = kb_dir or RAG_CONFIG.get('knowledge_base_dir', 'knowledge_base')
    root = base if os.path.isabs(base) else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), base
    )
    r = KnowledgeRetriever(
        root,
        max_chunk_chars=RAG_CONFIG.get('max_chunk_chars', 1400),
    )
    n = r.load_and_index()
    print(f'[RAG] 知识库已加载: {root}，共 {n} 个片段')
    _retriever_instance = r
    return r
