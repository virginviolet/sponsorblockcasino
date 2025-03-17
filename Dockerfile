# Use the Python 3 official image
# https://hub.docker.com/_/python
FROM python:3-slim

# Run in unbuffered mode
ENV PYTHONUNBUFFERED=1 

# Create and change to the app directory.
WORKDIR /app

# Copy local code to the container image.
COPY . ./

# Fetch the .git folder initialize submodules
RUN git init && \
    git remote add origin https://github.com/virginviolet/sponsorblockcasino.git && \
    git fetch --depth=1 origin main && \
    git checkout -f main && \
    git submodule update --init --recursive || echo "No submodules found" && \
    rm -rf .git && \
    rm -rf sponsorblockchain/.git

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the web service on container startup.
CMD ["python", "sponsorblockcasino.py"]