FROM ubuntu:20.04

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

# Install Python 3.9, system dependencies, and both rendering engines
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    wkhtmltopdf \
    xvfb \
    fonts-dejavu-core \
    fontconfig \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Create Python symlink
RUN ln -s /usr/bin/python3.9 /usr/bin/python

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
