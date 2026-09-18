FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY bot_mail ./bot_mail
COPY config.example.json ./
RUN pip install --no-cache-dir . && useradd --uid 10001 --create-home botmail
USER botmail
ENV BOT_MAIL_INSTANCE=/data BOT_MAIL_HOST=0.0.0.0 BOT_MAIL_PORT=8000
EXPOSE 8000
CMD ["python", "-m", "bot_mail.cli", "serve"]
