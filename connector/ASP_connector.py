from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ConnectorConfig:
    """连接器配置，包含 ASPECT 二进制路径、MPI 参数、工作目录等"""

    aspect_binary: Path  # ASPECT 可执行文件路径
    mpirun_binary: str = ""  # mpirun 可执行文件名称，为空则不使用 MPI
    default_nproc: int = 1  # 默认并行进程数
    working_directory: Path = Path("./runs")  # 默认工作目录
    default_timeout_seconds: float = 3600.0  # 默认超时时间（秒）
    extra_args: list[str] = field(default_factory=list)  # 额外命令行参数

    @classmethod
    def from_file(cls, path: Path) -> ConnectorConfig:
        """从 JSON 配置文件加载配置"""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            aspect_binary=Path(raw["aspect_binary"]).expanduser().resolve(),
            mpirun_binary=raw.get("mpirun_binary", ""),
            default_nproc=raw.get("default_nproc", 1),
            working_directory=Path(raw.get("working_directory", "./runs")),
            default_timeout_seconds=raw.get("default_timeout_seconds", 3600),
            extra_args=raw.get("extra_args", []),
        )

    @classmethod
    def default(cls) -> ConnectorConfig:
        """返回默认配置"""
        return cls(aspect_binary=Path("/Users/bai/workspace/aspect-main/build/aspect"))


@dataclass(frozen=True)
class RunResult:
    """运行结果，包含成功标志、返回码、标准输出/错误、耗时等"""

    success: bool  # 是否成功运行
    returncode: int  # 进程返回码
    stdout: str  # 标准输出内容
    stderr: str  # 标准错误内容
    elapsed_seconds: float  # 运行耗时（秒）
    prm_path: Path  # 参数文件路径
    output_directory: Path | None  # 输出目录
    timed_out: bool = False  # 是否超时
    command: list[str] = field(default_factory=list)  # 实际执行的命令


class ConnectorError(Exception):
    """连接器基础异常"""
    pass


class BinaryNotFoundError(ConnectorError):
    """ASPECT 二进制文件未找到异常"""
    pass


class PrmFileNotFoundError(ConnectorError):
    """参数文件（.prm）未找到异常"""
    pass


class RunTimeoutError(ConnectorError):
    """运行超时异常"""
    pass


class AspectConnector:
    """ASPECT 求解器连接器，负责参数校验、命令构建和运行管理"""
    def __init__(
        self,
        config: ConnectorConfig | None = None,
        config_path: Path | None = None,
    ):
        """初始化连接器，优先使用传入的 config 对象，其次从文件加载，最后使用默认配置"""
        if config is not None:
            self.config = config
        elif config_path is not None:
            self.config = ConnectorConfig.from_file(config_path)
        else:
            default_config = Path(__file__).parent / "config.json"
            if default_config.exists():
                self.config = ConnectorConfig.from_file(default_config)
            else:
                self.config = ConnectorConfig.default()

    def validate(self) -> None:
        """验证 ASPECT 二进制文件是否存在；若使用 MPI 则也验证 mpirun 是否可用"""
        binary = self.config.aspect_binary
        if not binary.exists():
            raise BinaryNotFoundError(f"ASPECT binary not found: {binary}")
        if not binary.is_file():
            raise BinaryNotFoundError(f"ASPECT path is not a file: {binary}")
        if self.config.default_nproc > 1 and self.config.mpirun_binary:
            if not shutil.which(self.config.mpirun_binary):
                raise BinaryNotFoundError(
                    f"mpirun not found: {self.config.mpirun_binary}"
                )

    def run(
        self,
        prm_path: str | Path,
        *,
        nproc: int | None = None,
        timeout: float | None = None,
        working_dir: str | Path | None = None,
    ) -> RunResult:
        """同步运行 ASPECT 求解，返回运行结果（支持超时处理）"""
        prm_path = Path(prm_path).expanduser().resolve()
        if not prm_path.exists():
            raise PrmFileNotFoundError(f"Parameter file not found: {prm_path}")
        self.validate()

        nproc = nproc or self.config.default_nproc
        timeout = timeout or self.config.default_timeout_seconds
        cwd = self._resolve_working_dir(prm_path, working_dir)
        cmd = self._build_command(prm_path, nproc)

        start = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            returncode = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as e:
            timed_out = True
            returncode = -1
            stdout = e.stdout or ""
            stderr = e.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode(errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
        elapsed = time.perf_counter() - start

        output_dir = self._parse_output_directory(prm_path)
        if output_dir and not output_dir.is_absolute():
            output_dir = cwd / output_dir

        return RunResult(
            success=(returncode == 0 and not timed_out),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            elapsed_seconds=elapsed,
            prm_path=prm_path,
            output_directory=output_dir,
            timed_out=timed_out,
            command=cmd,
        )

    def run_async(
        self,
        prm_path: str | Path,
        *,
        nproc: int | None = None,
        working_dir: str | Path | None = None,
    ) -> subprocess.Popen:
        """异步启动 ASPECT 求解，返回 Popen 对象以便手动管理子进程"""
        prm_path = Path(prm_path).expanduser().resolve()
        if not prm_path.exists():
            raise PrmFileNotFoundError(f"Parameter file not found: {prm_path}")
        self.validate()

        nproc = nproc or self.config.default_nproc
        cwd = self._resolve_working_dir(prm_path, working_dir)
        cmd = self._build_command(prm_path, nproc)

        return subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def _build_command(self, prm_path: Path, nproc: int) -> list[str]:
        """构建 ASPECT 运行命令，nproc>1 时自动添加 mpirun 前缀"""
        cmd: list[str] = []
        if nproc > 1 and self.config.mpirun_binary:
            cmd = [self.config.mpirun_binary, "-np", str(nproc)]
        cmd.append(str(self.config.aspect_binary))
        cmd.extend(self.config.extra_args)
        cmd.append(str(prm_path))
        return cmd

    def _resolve_working_dir(
        self, prm_path: Path, working_dir: str | Path | None
    ) -> Path:
        """解析工作目录：优先使用传入的 working_dir，否则在配置目录下以 prm 文件名创建子目录"""
        if working_dir is not None:
            cwd = Path(working_dir).expanduser().resolve()
        else:
            base = self.config.working_directory
            if not base.is_absolute():
                base = Path(__file__).parent.parent / base
            cwd = base / prm_path.stem
        cwd.mkdir(parents=True, exist_ok=True)
        return cwd

    @staticmethod
    def _parse_output_directory(prm_path: Path) -> Path | None:
        """从 .prm 参数文件中解析 'set Output directory' 配置项"""
        for line in prm_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("set output directory"):
                _, _, value = stripped.partition("=")
                value = value.strip()
                if value:
                    return Path(value)
        return None
