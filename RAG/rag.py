from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .case_searcher import CaseSearcher, SimulationCase
from .parameter_searcher import Parameter, ParameterSearcher


@dataclass(frozen=True)
class RAGResult:
    """统一检索结果，同时包含匹配的参数定义和专家案例"""

    parameters: list[Parameter] = field(default_factory=list)  # 匹配的参数定义
    cases: list[SimulationCase] = field(default_factory=list)  # 匹配的专家案例


class AspectRAG:
    """
    统一 RAG 检索入口，组合参数检索与案例检索。

    一次 search 同时返回：
      - 相关的 ASPECT 参数定义（来自官方文档）
      - 使用过这些参数的专家模拟案例（来自文献清洗）
    供 agent 在生成-运行-修复循环中获取上下文。
    """

    def __init__(
        self,
        parameters_path: Path | None = None,
        cases_path: Path | None = None,
    ):
        self.parameter_searcher = ParameterSearcher(parameters_path)
        self.case_searcher = CaseSearcher(cases_path)

    def search(
        self,
        keyword: str,
        *,
        domain: str | None = None,
        limit: int = 20,
    ) -> RAGResult:
        """
        统一搜索：同时检索参数定义和专家案例。

        Args:
            keyword: 搜索关键词
            domain: 可选，按案例领域过滤（如 "mantle convection"）
            limit: 每类结果的最大返回数
        """
        parameters = self.parameter_searcher.search(keyword, limit=limit)

        cases = self.case_searcher.search(keyword, domain=domain, limit=limit)

        if not cases and keyword:
            cases = self._find_cases_by_parameters(
                [p.name for p in parameters], limit=limit
            )

        return RAGResult(parameters=parameters, cases=cases)

    def _find_cases_by_parameters(
        self, parameter_names: list[str], *, limit: int
    ) -> list[SimulationCase]:
        """通过参数名反查使用了这些参数的案例（参数→案例关联）"""
        seen: set[str] = set()
        result: list[SimulationCase] = []
        for name in parameter_names:
            for case in self.case_searcher.by_parameter(name):
                if case.case_id not in seen:
                    seen.add(case.case_id)
                    result.append(case)
                    if len(result) >= limit:
                        return result
        return result

    @property
    def parameter_count(self) -> int:
        """已加载的参数总数"""
        return self.parameter_searcher.count()

    @property
    def case_count(self) -> int:
        """已加载的案例总数"""
        return self.case_searcher.count()
