# Use the Python 3 official image
# https://hub.docker.com/_/python
FROM python:3-slim

# Install system dependencies
RUN apt-get update && apt-get install -y git python3-venv python3-pip

# Run in unbuffered mode
ENV PYTHONUNBUFFERED=1 

# Create and change to the app directory
WORKDIR /app

# Copy local code to the container image
COPY . ./

# Fetch the .git folder initialize submodules
RUN git init && \
    git remote add origin https://github.com/virginviolet/sponsorblockcasino.git && \
    git fetch --depth=30 origin main && \
    git checkout -f main && \
    git submodule update --init --recursive || echo "No submodules found" && \
    rm -rf .git && \
    rm -rf sponsorblockchain/.git

# Add venv to PATH
ENV PATH="/opt/venv/bin:$PATH"
RUN printf '\nPATH=/opt/venv/bin:$PATH' >>/root/.profile

# Install Python dependencies
RUN --mount=type=cache,id=s/f37f20e4-ec25-4620-9359-ffe68caf8d61-/root/cache/pip,target=/root/.cache/pip \
    python --version && \
    python -m ensurepip --default-pip && \
    python -m venv --copies /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup
CMD ["python", "sponsorblockcasino.py"]