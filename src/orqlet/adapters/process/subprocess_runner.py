"""Run a program with a timeout and a cap on captured output. No shell, no inherited environment."""

from __future__ import annotations

import contextlib
import subprocess
import threading
from collections.abc import Mapping, Sequence
from typing import IO

from orqlet.application.ports.process import (
    OutputLimitExceeded,
    ProcessError,
    ProcessResult,
    ProcessTimeout,
)

_CHUNK = 65536


class SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str,
        env: Mapping[str, str],
        timeout_seconds: float,
        max_output_bytes: int,
        stdin: bytes | None = None,
    ) -> ProcessResult:
        command = tuple(argv)
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=dict(env),
                stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                close_fds=True,
            )
        except (OSError, ValueError) as exc:
            raise ProcessError(f"cannot start {command[0]!r}: {type(exc).__name__}") from exc

        exceeded = threading.Event()
        out, err = bytearray(), bytearray()
        assert process.stdout is not None
        assert process.stderr is not None
        workers = [
            threading.Thread(
                target=_drain, args=(process.stdout, out, max_output_bytes, exceeded, process)
            ),
            threading.Thread(
                target=_drain, args=(process.stderr, err, max_output_bytes, exceeded, process)
            ),
        ]
        if stdin is not None:
            assert process.stdin is not None
            workers.append(threading.Thread(target=_feed, args=(process.stdin, stdin)))
        for worker in workers:
            worker.daemon = True
            worker.start()
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            process.kill()
            process.wait()
            raise ProcessTimeout(f"{command[0]!r} exceeded {timeout_seconds} seconds") from exc
        finally:
            for worker in workers:
                worker.join(timeout=5)
        if exceeded.is_set():
            raise OutputLimitExceeded(f"{command[0]!r} wrote more than {max_output_bytes} bytes")
        return ProcessResult(command, process.returncode, bytes(out), bytes(err))


def _drain(
    stream: IO[bytes],
    sink: bytearray,
    limit: int,
    exceeded: threading.Event,
    process: subprocess.Popen[bytes],
) -> None:
    try:
        while chunk := stream.read1(_CHUNK):  # type: ignore[attr-defined]
            if len(sink) + len(chunk) > limit:
                exceeded.set()
                process.kill()
                return
            sink.extend(chunk)
    except (OSError, ValueError):
        return
    finally:
        stream.close()


def _feed(stream: IO[bytes], data: bytes) -> None:
    with contextlib.suppress(OSError, ValueError):  # the program may exit before reading it all
        try:
            stream.write(data)
        finally:
            stream.close()
