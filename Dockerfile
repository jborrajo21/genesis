# syntax=docker/dockerfile:1

# Pinned to a specific Debian release, not bare `3.11-slim`: the tag would
# otherwise drift to a new base OS under you between builds.
FROM python:3.11-slim-bookworm

# PYTHONUNBUFFERED matters here more than usual. Genesis reports progress as it
# plans and scaffolds; with stdout block-buffered (which it is when not a tty)
# a container run would appear to hang and then dump everything at the end.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# No system packages are installed: Genesis has no compiled dependencies.
# pip and the venv module ship with the base image and must stay — Genesis
# shells out to `python -m venv` and `pip install` at runtime to verify that a
# generated repo actually builds (D-032).
COPY pyproject.toml ./
COPY src/ ./src/
COPY README.md ./

# A plain non-editable install. This only works because the template lives
# inside the package (D-054) and therefore ships in the wheel; before that fix
# an installed Genesis could plan but not scaffold.
RUN pip install --no-cache-dir ".[anthropic]"

# Run as a non-root user, from a writable directory meant to be volume-mounted.
# Generated repos land in the working directory, so it must not be root-owned.
RUN useradd --create-home --uid 1000 genesis \
    && mkdir -p /work \
    && chown genesis:genesis /work
USER genesis
WORKDIR /work

ENTRYPOINT ["genesis"]
CMD ["--help"]
