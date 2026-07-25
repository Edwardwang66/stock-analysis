# 通用容器镜像(Render / Railway / Fly / 任意平台均可)
FROM python:3.11.15-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOME=/tmp
WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.txt

COPY --chown=10001:10001 app ./app

# 平台通过 $PORT 注入端口(本地默认 8000)
ENV PORT=8000
EXPOSE 8000
USER 10001:10001
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
