from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Parameter:
    """ASPECT 参数定义条目，对应 parameters.json 中的一条记录"""

    name: str  # 参数名，如 "CFL number"
    section: str  # 所属 section 全路径字符串，如 "Global parameters / No subsection"
    section_path: list[str]  # section 层级列表
    default: str  # 默认值
    type: str  # 参数类型，如 Double / Integer / Selection / Bool
    choices: list[str] | None  # 可选值列表（Selection 类型才有）
    pattern: str  # 取值范围模式描述
    documentation: str  # 官方文档说明
    anchor: str  # 文档锚点，可用于拼接在线文档 URL

    def to_summary(self, score: int = 0, *, brief_len: int = 120) -> ParameterSummary:
        """转换为轻量摘要；brief_len 控制 doc_brief 截断长度"""
        doc = self.documentation
        doc_brief = doc[:brief_len].rstrip()
        if len(doc) > brief_len:
            doc_brief += "..."
        return ParameterSummary(
            name=self.name,
            section=self.section,
            type=self.type,
            default=self.default,
            doc_brief=doc_brief,
            score=score,
        )


@dataclass(frozen=True)
class ParameterSummary:
    """参数轻量摘要，用于 LLM 上下文友好的快速扫描（不含完整 documentation）"""

    name: str  # 参数名
    section: str  # 所属 section
    type: str  # 参数类型
    default: str  # 默认值
    doc_brief: str  # documentation 摘要（截断至约 120 字符）
    score: int  # 相关性分数，用于排序透明与调试


class ParameterSearcher:
    """ASPECT 参数检索器，从 parameters.json 加载并提供关键词模糊搜索"""

    def __init__(self, parameters_path: Path | None = None):
        if parameters_path is None:
            parameters_path = Path(__file__).parent / "parameters.json"
        self._parameters = self._load(parameters_path)

    def _load(self, path: Path) -> list[Parameter]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("parameters", [])
        result: list[Parameter] = []
        for item in items:
            result.append(
                Parameter(
                    name=item["name"],
                    section=item.get("section", ""),
                    section_path=item.get("section_path", []),
                    default=item.get("default", ""),
                    type=item.get("type", ""),
                    choices=item.get("choices"),
                    pattern=item.get("pattern", ""),
                    documentation=item.get("documentation", ""),
                    anchor=item.get("anchor", ""),
                )
            )
        return result

    def count(self) -> int:
        """返回参数总数"""
        return len(self._parameters)

    def all_parameters(self) -> list[Parameter]:
        """返回全部参数列表"""
        return list(self._parameters)

    def get(self, name: str) -> Parameter | None:
        """按参数名精确查询（大小写不敏感）"""
        target = name.strip().lower()
        for p in self._parameters:
            if p.name.lower() == target:
                return p
        return None

    def search(self, keyword: str, *, limit: int = 20) -> list[Parameter]:
        """
        关键词模糊搜索，按相关性排序返回完整 Parameter（含完整 documentation）。

        打分规则（从高到低）：
          - 完整关键词出现在参数名中        → +1000
          - 每个分词命中参数名              → +100/词
          - 完整关键词出现在 section 中     → +100
          - 每个分词命中 section            → +30/词
          - 完整关键词出现在 documentation → +50
          - 每个分词命中 documentation     → +5/词
        """
        query = keyword.strip().lower()
        if not query or limit <= 0:
            return []

        tokens = [t for t in query.split() if t]
        scored: list[tuple[int, str, Parameter]] = []
        for p in self._parameters:
            score = self._score(p, query, tokens)
            if score > 0:
                scored.append((score, p.name.lower(), p))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [item[2] for item in scored[:limit]]

    def search_summary(
        self,
        keyword: str,
        *,
        limit: int = 10,
        min_score: int = 1,
        brief_len: int = 120,
    ) -> list[ParameterSummary]:
        """
        轻量搜索，返回 ParameterSummary 列表（不含完整 documentation）。

        适合 agent 先快速扫描相关参数，再用 get() 按需展开完整文档，
        大幅减少 LLM 上下文占用。

        Args:
            keyword: 搜索关键词
            limit: 最大返回数（默认 10）
            min_score: 最小相关性分数，过滤弱匹配（默认 1）
            brief_len: doc_brief 截断长度（默认 120 字符）
        """
        query = keyword.strip().lower()
        if not query or limit <= 0:
            return []

        tokens = [t for t in query.split() if t]
        scored: list[tuple[int, str, Parameter]] = []
        for p in self._parameters:
            score = self._score(p, query, tokens)
            if score >= min_score:
                scored.append((score, p.name.lower(), p))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [
            item[2].to_summary(score=item[0], brief_len=brief_len)
            for item in scored[:limit]
        ]

    @staticmethod
    def _score(param: Parameter, query: str, tokens: list[str]) -> int:
        name_lower = param.name.lower()
        section_lower = param.section.lower()
        doc_lower = param.documentation.lower()

        score = 0
        if name_lower == query:
            # 精确同名（如查 "viscosity" 命中 Simple model 的 "Viscosity"）
            # 必须压过所有复合名，否则会被同分字母序挤出 top-N，
            # 导致 rag.py 的参数→案例反查断链
            score += 5000
        if query in name_lower:
            score += 1000
        if query in section_lower:
            score += 100
        if query in doc_lower:
            score += 50

        for t in tokens:
            if t in name_lower:
                score += 100
            if t in section_lower:
                score += 30
            if t in doc_lower:
                score += 5
        return score
