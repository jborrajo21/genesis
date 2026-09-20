# syntax=docker/dockerfile:1

# Pinned to a specific Debian release, not bare `3.11-slim`: the tag would
# otherwise drift to a new base OS under you between builds.
FROM python:3.11-slim-bookworm AS base

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

# The Lambda Runtime Interface Client: the loop that polls Lambda's Runtime API
# and dispatches each invocation to a Python function. A deployment-target
# dependency, not part of the genesis-agent package (D-081) — nobody installing
# from PyPI wants it, and the handler never imports it; the RIC imports the
# handler. Its own layer so this comment has somewhere to live: it does not
# belong in pyproject.toml's extras.
RUN pip install --no-cache-dir awslambdaric

RUN useradd --create-home --uid 1000 genesis \
    && mkdir -p /work \
    && chown genesis:genesis /work


# --- lambda -----------------------------------------------------------------
# Deliberately sets no USER. Lambda defines its own least-privileged Linux user,
# which is why AWS's own container examples omit the instruction — and setting
# one actively breaks the local path: `sam local invoke` builds a derived image
# that installs the Runtime Interface Emulator into root-owned /var/rapid, and
# those mv/chmod steps run as the image's USER. Pre-creating the directory does
# not help; chmod on a root-owned file fails whoever owns the directory.
#
# This stage is why the image is no longer strictly single (amends D-081). The
# cost is contained: one Dockerfile, one base, one build context, and the two
# final stages differ only in their last three lines.
FROM base AS lambda
WORKDIR /tmp
ENTRYPOINT ["/usr/local/bin/python", "-m", "awslambdaric"]
CMD ["genesis.lambda_handler.handler"]


# --- cli --------------------------------------------------------------------
# Runs as a non-root user, from a writable directory meant to be volume-mounted.
# Generated repos land in the working directory, so it must not be root-owned —
# as root, every file a CLI user generates arrives on their disk owned by root.
#
# LAST ON PURPOSE: `docker build` with no --target builds the final stage, so
# the Phase 9 CI gate keeps building and testing the CLI image unchanged. SAM
# reaches the other stage explicitly, via DockerBuildTarget in template.yaml.
FROM base AS cli
USER genesis
WORKDIR /work

ENTRYPOINT ["genesis"]
CMD ["--help"]
