from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ParameterDecision:
    """专家对单个参数的决策记录，是连接参数定义与模拟案例的桥梁"""

    parameter_name: str  # 对应的 ASPECT 参数名
    value: str  # 专家设定的值
    rationale: str  # 选择该值的原因（专家经验）


@dataclass(frozen=True)
class SimulationCase:
    """专家模拟案例，来源于 cookbook、论文或实际项目中的文献清洗"""

    case_id: str  # 唯一标识
    title: str  # 案例标题
    domain: str  # 领域分类，如 "mantle convection" / "subduction" / "heat conduction"
    description: str  # 案例描述（物理模型、边界条件等）
    source: str  # 来源引用，如 cookbook 路径或论文标题
    prm_path: str  # 关联的 .prm 文件路径（如有）
    outcome: str  # 运行结果描述
    success: bool  # 是否成功
    parameter_decisions: list[ParameterDecision] = field(default_factory=list)  # 专家参数决策列表
    tags: list[str] = field(default_factory=list)  # 检索标签


class CaseSearcher:
    """专家模拟案例检索器，从 cases.json 加载并提供关键词 + 领域过滤搜索"""

    def __init__(self, cases_path: Path | None = None):
        if cases_path is None:
            cases_path = Path(__file__).parent / "cases.json"
        self._cases = self._load(cases_path)

    def _load(self, path: Path) -> list[SimulationCase]:
        if not path.exists():
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        items = raw.get("cases", [])
        result: list[SimulationCase] = []
        for item in items:
            decisions = [
                ParameterDecision(
                    parameter_name=d["parameter_name"],
                    value=d.get("value", ""),
                    rationale=d.get("rationale", ""),
                )
                for d in item.get("parameter_decisions", [])
            ]
            result.append(
                SimulationCase(
                    case_id=item["case_id"],
                    title=item.get("title", ""),
                    domain=item.get("domain", ""),
                    description=item.get("description", ""),
                    source=item.get("source", ""),
                    prm_path=item.get("prm_path", ""),
                    parameter_decisions=decisions,
                    outcome=item.get("outcome", ""),
                    success=item.get("success", False),
                    tags=item.get("tags", []),
                )
            )
        return result

    def count(self) -> int:
        """返回案例总数"""
        return len(self._cases)

    def all_cases(self) -> list[SimulationCase]:
        """返回全部案例列表"""
        return list(self._cases)

    def get(self, case_id: str) -> SimulationCase | None:
        """按 case_id 精确查询"""
        for c in self._cases:
            if c.case_id == case_id:
                return c
        return None

    def by_parameter(self, parameter_name: str) -> list[SimulationCase]:
        """查找使用了某个参数的所有案例（用于参数→案例关联检索）"""
        target = parameter_name.strip().lower()
        result: list[SimulationCase] = []
        for c in self._cases:
            for d in c.parameter_decisions:
                if d.parameter_name.lower() == target:
                    result.append(c)
                    break
        return result

    def search(
        self,
        keyword: str,
        *,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[SimulationCase]:
        """
        关键词模糊搜索案例，可按 domain 过滤。

        打分规则（从高到低）：
          - 完整关键词命中 title          → +1000
          - 每个分词命中 title            → +200/词
          - 命中 tag（完整或分词）        → +150/词
          - 完整关键词命中 domain         → +100
          - 完整关键词命中 description   → +50
          - 每个分词命中 description     → +10/词
          - 命中 parameter_decision 的 rationale → +5/词
        """
        query = keyword.strip().lower()
        if not query or limit <= 0:
            return []

        tokens = [t for t in query.split() if t]
        domain_lower = domain.strip().lower() if domain else None

        scored: list[tuple[int, str, SimulationCase]] = []
        for c in self._cases:
            if domain_lower is not None and c.domain.lower() != domain_lower:
                continue
            score = self._score(c, query, tokens)
            if score > 0:
                scored.append((score, c.title.lower(), c))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [item[2] for item in scored[:limit]]

    @staticmethod
    def _score(case: SimulationCase, query: str, tokens: list[str]) -> int:
        title_lower = case.title.lower()
        domain_lower = case.domain.lower()
        desc_lower = case.description.lower()
        tags_lower = [t.lower() for t in case.tags]

        score = 0
        if query in title_lower:
            score += 1000
        if query in domain_lower:
            score += 100
        if query in desc_lower:
            score += 50

        for t in tokens:
            if t in title_lower:
                score += 200
            if t in domain_lower:
                score += 50
            if t in desc_lower:
                score += 10
            for tag in tags_lower:
                if t in tag or tag in t:
                    score += 150
                    break
            for d in case.parameter_decisions:
                if t in d.rationale.lower():
                    score += 5
                    break
        return score
