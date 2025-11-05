# ───────────────────────────────────────────────
# 1. Use a lightweight base image with Python
# ───────────────────────────────────────────────
FROM python:3.11-slim

# ───────────────────────────────────────────────
# 2. Set working directory
# ───────────────────────────────────────────────
WORKDIR /app

# ───────────────────────────────────────────────
# 3. Install system dependencies (curl, git, etc.)
# ───────────────────────────────────────────────
RUN apt-get update && \
    apt-get install -y curl git && \
    rm -rf /var/lib/apt/lists/*

# ───────────────────────────────────────────────
# 4. Install Pixi package manager
# ───────────────────────────────────────────────
RUN curl -fsSL https://pixi.sh/install.sh | bash && \
    ln -s /root/.pixi/bin/pixi /usr/local/bin/pixi

# ───────────────────────────────────────────────
# 5. Copy project files into container
# ───────────────────────────────────────────────
COPY . .

# ───────────────────────────────────────────────
# 6. Install environment (dependencies from pixi.toml)
# ───────────────────────────────────────────────
RUN pixi install

# ───────────────────────────────────────────────
# 7. Copy environment variables
#    Docker doesn't automatically read `.env`
# ───────────────────────────────────────────────
# You can use `--env-file .env` at runtime
# or bake default env values into the image if you prefer:
# COPY .env .env

# ───────────────────────────────────────────────
# 8. Expose Uvicorn port
# ───────────────────────────────────────────────
EXPOSE 8000

# ───────────────────────────────────────────────
# 9. Default command to start FastAPI app
# ───────────────────────────────────────────────
CMD ["pixi", "run", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
