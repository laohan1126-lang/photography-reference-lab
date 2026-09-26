FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LAB_DATA_DIR=/data
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ref_lab ./ref_lab
COPY web ./web
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home reference && mkdir /data && chown reference:reference /data
USER reference
VOLUME /data
EXPOSE 8765
CMD ["python", "-m", "ref_lab", "serve", "--host", "0.0.0.0", "--port", "8765", "--allow-remote"]
