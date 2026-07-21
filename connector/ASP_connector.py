from __future__ import annotations

import json
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ConnectorConfig:
    aspect_binary: Path
    mpirun_binary: str = ""
    default_nproc: int = 1
    working_directory: Path = Path("./runs")
    default_timeout_seconds: float = 3600.0
    extra_args: list[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: Path) -> ConnectorConfig:
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
        return cls(aspect_binary=Path("/Users/bai/workspace/aspect-main/build/aspect"))


@dataclass(frozen=True)
class RunResult:
    success: bool
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    prm_path: Path
    output_directory: Path | None
    timed_out: bool = False
    command: list[str] = field(default_factory=list)


class ConnectorError(Exception):
    pass


class BinaryNotFoundError(ConnectorError):
    pass


class PrmFileNotFoundError(ConnectorError):
    pass


class RunTimeoutError(ConnectorError):
    pass


class AspectConnector:
    def __init__(
        self,
        config: ConnectorConfig | None = None,
        config_path: Path | None = None,
    ):
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
        for line in prm_path.read_text(encoding="utf-8", errors="replace").splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("set output directory"):
                _, _, value = stripped.partition("=")
                value = value.strip()
                if value:
                    return Path(value)
        return None
