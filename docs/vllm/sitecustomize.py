# Bound the MLX Metal buffer cache for the embedding engine.
#
# vllm-mlx does not call set_cache_limit on the embedding path, so MLX leaves the
# cache at the device working set (tens of GB) and the process footprint balloons
# under load. The embedding forward needs only a small scratch pool. 512MB keeps
# cache hits on common shapes while capping growth. Remove this file to revert.
import sys

_LIMIT = 512 * 1024 * 1024  # 512 MB

try:
    import mlx.core as mx
    _set = getattr(mx, "set_cache_limit", None) or getattr(getattr(mx, "metal", None), "set_cache_limit", None)
    if _set is not None:
        prev = _set(_LIMIT)
        print(f"[sitecustomize] MLX cache_limit set to 512MB (prev={prev})", file=sys.stderr)
except Exception as e:
    print(f"[sitecustomize] MLX cache_limit NOT set: {e}", file=sys.stderr)
