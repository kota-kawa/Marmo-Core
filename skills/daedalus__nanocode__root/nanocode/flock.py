"""Custom file-based distributed locking using atomic mkdir.

This provides cross-process, cross-machine locking using the filesystem as a coordination
primitive. It mirrors the flock.ts implementation from opencode.

## Design

The lock uses atomic directory creation (mkdir with mode 0o700) as the primitive:
1. Try to acquire: mkdir .lockdir -> if EEXIST, check if stale
2. Stale detection: if heartbeat/meta mtime > stale_ms, try to break
3. Write heartbeat + meta atomically using exclusive create (flag "x")
4. Token verification on release prevents releasing another's lock

## Known Limitations

- TOCTOU race: When multiple processes race simultaneously to acquire a non-existent lock,
  there's a window where all see "doesn't exist" and all succeed. This is the same
  behavior as opencode's flock.ts. In practice, this only triggers when processes
  race at exactly the same microsecond before either creates the lock.

- Works correctly for:
  * Sequential ownership (owner holds first, waiters try after)
  * Single-process async operations
  * Stale lock breaking

- The race does NOT trigger when:
  * An owner explicitly acquires the lock first
  * There is any delay between process starts
  * File has been locked at least once (heartbeat exists)

## Usage

    from nanocode.flock import Flock

    fl = Flock(lock_dir="/tmp/my-locks", stale_ms=60000)
    lease = await fl.acquire("my-resource")
    # critical section
    await lease.release()

    # Or use context manager:
    async with fl.with_lock("my-resource") as lease:
        # critical section
"""

import asyncio
import json
import os
import random
import string
import tempfile
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_STALE_MS = 60_000
DEFAULT_TIMEOUT_MS = 5 * 60_000
DEFAULT_BASE_DELAY_MS = 100
DEFAULT_MAX_DELAY_MS = 2_000


def _err_code(err: BaseException) -> str | None:
    if hasattr(err, "errno"):
        return getattr(err, "errno", None)
    if hasattr(err, "code"):
        return getattr(err, "code", None)
    return None


def _random_token() -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=32))


def _wall_ms() -> float:
    return time.time() * 1000


def _sleep_ms(ms: float) -> asyncio.Task:
    async def sleep_task():
        await asyncio.sleep(ms / 1000)

    return asyncio.create_task(sleep_task())


def _jitter(ms: float) -> float:
    j = int(ms * 0.3)
    d = random.randint(-j, j)
    return max(0, ms + d)


def _parse_time(val: str) -> datetime | None:
    try:
        return datetime.fromisoformat(val)
    except (ValueError, TypeError):
        return None


async def _stat_mtime_ms(path: Path) -> float | None:
    try:
        stat = await asyncio.get_event_loop().run_in_executor(None, os.stat, path)
        return stat.st_mtime * 1000
    except (FileNotFoundError, OSError):
        return None


class FlockLease:
    """Represents an acquired lock."""

    def __init__(
        self,
        key: str,
        lock_dir: Path,
        token: str,
        release_fn,
    ):
        self.key = key
        self.lock_dir = lock_dir
        self.token = token
        self._release_fn = release_fn
        self._released = False
        self._heartbeat_task: asyncio.Task | None = None

    async def start_heartbeat(self, stale_ms: int = DEFAULT_STALE_MS) -> None:
        """Start sending heartbeats to prevent lock from being considered stale."""
        interval_ms = max(100, stale_ms // 3)
        heartbeat_path = self.lock_dir / "heartbeat"

        async def heartbeat_loop():
            while not self._released:
                try:
                    await asyncio.sleep(interval_ms / 1000)
                    if self._released:
                        break
                    # Touch the heartbeat file by updating mtime
                    now = datetime.now(UTC)
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: os.utime(heartbeat_path, (
                            now.timestamp(),
                            now.timestamp(),
                        )),
                    )
                except FileNotFoundError:
                    break
                except Exception:
                    pass
            # Update final heartbeat to show we're still alive right before release
            try:
                now = datetime.now(UTC)
                os.utime(heartbeat_path, (now.timestamp(), now.timestamp()))
            except Exception:
                pass

        self._heartbeat_task = asyncio.create_task(heartbeat_loop())

    async def release(self) -> None:
        """Release the lock."""
        if self._released:
            return

        self._released = True

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        await self._release_fn(self.lock_dir, self.token)


class Flock:
    """Distributed file-based lock manager."""

    def __init__(
        self,
lock_dir: Path | None = None,
        stale_ms: int = DEFAULT_STALE_MS,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
        base_delay_ms: int = DEFAULT_BASE_DELAY_MS,
        max_delay_ms: int = DEFAULT_MAX_DELAY_MS,
    ):
        self.lock_dir = lock_dir or Path(tempfile.gettempdir()) / ".nanocode_locks"
        self.stale_ms = stale_ms
        self.timeout_ms = timeout_ms
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_path(self, key: str) -> Path:
        """Get lock file path for a key."""
        import hashlib
        hashed = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.lock_dir / f"{hashed}.lock"

    async def _is_stale(self, lock_dir: Path, stale_ms: int) -> bool:
        """Check if a lock directory is stale."""
        heartbeat_path = lock_dir / "heartbeat"
        meta_path = lock_dir / "meta.json"

        now_ms = _wall_ms()

        mtime = await _stat_mtime_ms(heartbeat_path)
        if mtime is not None:
            return now_ms - mtime > stale_ms

        mtime = await _stat_mtime_ms(meta_path)
        if mtime is not None:
            return now_ms - mtime > stale_ms

        mtime = await _stat_mtime_ms(lock_dir)
        if mtime is None:
            return False  # Lock doesn't exist, not stale

        return now_ms - mtime > stale_ms

    async def _try_acquire(self, lock_path: Path) -> FlockLease | None:
        """Try to acquire a lock. Returns None if failed."""
        import os

        token = _random_token()
        meta_path = lock_path / "meta.json"
        heartbeat_path = lock_path / "heartbeat"

        # First check: can we create the lock dir?
        try:
            lock_path.mkdir(mode=0o700)
        except FileExistsError:
            # Lock exists - check if stale
            if not await self._is_stale(lock_path, self.stale_ms):
                return None

            # Try to break the stale lock
            breaker_path = Path(str(lock_path) + ".breaker")

            try:
                breaker_path.mkdir(mode=0o700)
            except FileExistsError:
                # Another breaker is active
                breaker_mtime = await _stat_mtime_ms(breaker_path)
                if breaker_mtime and _wall_ms() - breaker_mtime > self.stale_ms:
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: _rm_tree(breaker_path)
                    )
                return None

            try:
                # Check again if still stale
                if not await self._is_stale(lock_path, self.stale_ms):
                    await _rm_tree(breaker_path)
                    return None

                # Remove stale lock
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _rm_tree(lock_path)
                )

                # Try to acquire
                try:
                    lock_path.mkdir(mode=0o700)
                except FileExistsError:
                    await _rm_tree(breaker_path)
                    return None
            finally:
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: _rm_tree(breaker_path)
                )

        # Write heartbeat and meta atomically using exclusive create
        try:
            with open(heartbeat_path, "x") as f:
                f.write("")
        except FileExistsError:
            # Heartbeat already exists - possible compromise
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _rm_tree(lock_path)
            )
            raise RuntimeError("Lock acquired but heartbeat already existed (possible compromise)")

        try:
            meta = {
                "token": token,
                "pid": os.getpid(),
                "hostname": os.uname().nodename,
                "createdAt": datetime.now(UTC).isoformat(),
            }
            with open(meta_path, "x") as f:
                json.dump(meta, f)
        except FileExistsError:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _rm_tree(lock_path)
            )
            raise RuntimeError("Lock acquired but meta.json already existed (possible compromise)")

        async def release_fn(lock_dir: Path, held_token: str):
            # Verify token before release
            try:
                with open(meta_path) as f:
                    meta = json.load(f)

                if not meta or meta.get("token") != held_token:
                    raise RuntimeError(
                        "Refusing to release: lock token mismatch (not the owner)"
                    )
            except FileNotFoundError:
                raise RuntimeError(
                    "Refusing to release: lock is compromised (metadata missing)"
                )

            await asyncio.get_event_loop().run_in_executor(
                None, lambda: _rm_tree(lock_dir)
            )

        return FlockLease(
            key="",  # Key is not stored in lease
            lock_dir=lock_path,
            token=token,
            release_fn=release_fn,
        )

    async def acquire(self, key: str) -> FlockLease:
        """Acquire a lock for the given key."""
        lock_path = self._lock_path(key)
        stop_ms = _wall_ms() + self.timeout_ms
        attempt = 0
        waited = 0
        delay = self.base_delay_ms

        while True:
            lease = await self._try_acquire(lock_path)
            if lease:
                lease.key = key
                return lease

            if _wall_ms() > stop_ms:
                raise TimeoutError(f"Timed out waiting for lock: {key}")

            attempt += 1
            ms = _jitter(delay)
            await _sleep_ms(ms)
            waited += ms
            delay = min(self.max_delay_ms, int(delay * 1.7))

    @asynccontextmanager
    async def with_lock(self, key: str) -> AsyncIterator[FlockLease]:
        """Context manager for acquiring and releasing a lock."""
        lease = await self.acquire(key)
        try:
            await lease.start_heartbeat(self.stale_ms)
            yield lease
        finally:
            await lease.release()


def _rm_tree(path: Path) -> None:
    """Remove a directory tree."""
    import shutil
    if path.exists():
        shutil.rmtree(path)


@asynccontextmanager
async def flock(
    key: str,
    lock_dir: Path | None = None,
    stale_ms: int = DEFAULT_STALE_MS,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> AsyncIterator[FlockLease]:
    """Convenience function for acquiring a lock."""
    fl = Flock(
        lock_dir=lock_dir,
        stale_ms=stale_ms,
        timeout_ms=timeout_ms,
    )
    async with fl.with_lock(key) as lease:
        yield lease

