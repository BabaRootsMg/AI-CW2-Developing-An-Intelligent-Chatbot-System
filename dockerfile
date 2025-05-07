# 1) Start from a lightweight Python image
FROM python:3.10-slim

# 2) Install any OS-level deps (tk for GUI, build tools if you need to compile C extensions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3-tk \
    && rm -rf /var/lib/apt/lists/*

# 3) Set working directory
WORKDIR /app

# 4) Copy requirements and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5) (Optional) Download spaCy model so it's baked in
RUN python -m spacy download en_core_web_sm

# 6) Copy your application code
COPY . .

# 7) Expose a port only if you have a web service
# EXPOSE 5000

# 8) Default command: run CLI. 
#    Change to ["python","main.py","--gui"] if you want GUI by default.
CMD ["python", "main.py"]
