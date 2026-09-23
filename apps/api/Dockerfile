# ═══════════════════════════════════════════════════════════════════════════
# SlotSight API — multi-stage build
#
# Stage 1 installs dependencies with uv into a virtualenv; stage 2 copies that
# venv into a slim runtime image. Keeping the build toolchain out of the final
# image is both smaller and a smaller attack surface.
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /build

# Dependency layer first, so a source-only change does not re-resolve the
# dependency graph on every rebuild. A stub package satisfies the build backend
# without needing the real sources yet.
COPY pyproject.toml README.md ./
RUN mkdir -p src/slotsight && touch src/slotsight/__init__.py \
    && uv venv /opt/venv \
    && VIRTUAL_ENV=/opt/venv uv pip install --no-cache .

# Now the real sources.
#
# `--reinstall-package slotsight` is load-bearing: without it uv sees
# slotsight==0.1.0 already installed from the stub above, skips the install
# entirely, and the image ships with an EMPTY package. The failure surfaces at
# runtime as `ModuleNotFoundError: No module named 'slotsight.seed'`, which
# points nowhere near the Dockerfile.
#
# The check is an IMPORT probe, not a path probe. It used to be
# `test -f /opt/venv/lib/python3.12/site-packages/slotsight/seed/generate.py`,
# which hardcoded the interpreter's minor version into a path — so bumping the
# base image to 3.13 moved site-packages, the test failed, and the build died
# claiming the package "did not install completely". It had installed fine.
# That blocked the python base-image bump for three weeks behind a message
# pointing at the wrong thing.
#
# Importing is also the stronger assertion: the failure this guards against
# surfaces at runtime as ModuleNotFoundError, so checking that the module
# IMPORTS tests the actual property rather than a proxy for it.
COPY src/ ./src/
RUN VIRTUAL_ENV=/opt/venv uv pip install --no-cache --no-deps --reinstall-package slotsight . \
    && /opt/venv/bin/python -c "import slotsight.seed.generate" \
    || (echo "BUILD ERROR: slotsight package did not install completely" && exit 1)


# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim-bookworm AS runtime

# Non-root. A container that does not need root should not have it.
RUN groupadd --system --gid 1001 slotsight \
    && useradd --system --uid 1001 --gid slotsight --create-home slotsight

COPY --from=builder --chown=slotsight:slotsight /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
USER slotsight

EXPOSE 8000

# Reports database and Azure OpenAI reachability without revealing either.
HEALTHCHECK --interval=20s --timeout=5s --start-period=25s --retries=4 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status==200 else 1)"

CMD ["uvicorn", "slotsight.main:app", "--host", "0.0.0.0", "--port", "8000"]
