FROM ghcr.io/astral-sh/uv:python3.13-alpine

WORKDIR /opt
COPY pyproject.toml uv.lock .
RUN uv sync --no-dev --all-extras --compile-bytecode --no-install-project --locked
# RUN uv sync --locked --no-install-project --no-install-workspace

COPY src /opt/src
COPY api.yaml /opt/api.yaml
COPY README.md /opt/README.md

RUN uv sync --no-dev --all-extras --compile-bytecode --frozen

ENTRYPOINT ["uv", "run", "--no-sync"]
CMD [ \
    "gunicorn", "attackapi.server:create_app", \
    "--bind", ":14320", \
    "--worker-class", "attackapi.server.worker.MyGunicornWebWorker", \
    "--workers", "4" \
]
