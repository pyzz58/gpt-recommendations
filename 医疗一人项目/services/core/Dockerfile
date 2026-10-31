FROM python:3.12.14-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app \
    && mkdir -p /var/lib/medical-one/artifacts /var/lib/medical-one/runs \
       /var/lib/medical-one/knowledge-staging \
    && chown -R app:app /var/lib/medical-one

WORKDIR /app
COPY services/core/requirements.lock /tmp/requirements.lock
RUN python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements.lock \
    && rm /tmp/requirements.lock

COPY --chown=app:app services/core/src /app/src
COPY --chown=app:app services/core/alembic.ini /app/alembic.ini
COPY --chown=app:app services/core/migrations /app/migrations
COPY --chown=app:app config/agents /app/config/agents
COPY --chown=app:app config/skills /app/config/skills
COPY --chown=app:app config/source_policies /app/config/source_policies
COPY --chown=app:app 最高思想.md /app/最高思想.md
ENV PYTHONPATH=/app/src

USER app
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "medical_one_person.main:app", "--host", "0.0.0.0", "--port", "8000"]
