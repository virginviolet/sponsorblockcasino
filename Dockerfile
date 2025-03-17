FROM ghcr.io/railwayapp/nixpacks:ubuntu

# Install git (in case not already installed)
RUN apt-get update && apt-get install -y git

# Install nixpacks
RUN curl -sSL https://nixpacks.com/install.sh | bash

# Ensure nixpacks is available
ENV PATH="/usr/local/bin:$PATH"

RUN ls -a

# Set working directory to /app
WORKDIR /app

# Copy everything downloaded from the repo into /app
COPY . /app
WORKDIR /app

# Fetch the .git folder
RUN git init && \
    git remote add origin https://github.com/virginviolet/sponsorblockcasino.git && \
    git fetch --depth=1 origin main && \
    git checkout -f main && \
    git submodule update --init --recursive && \
    rm -rf .git && \
    rm -rf sponsorblockchain/.git

# Add venv to PATH
RUN printf '\nPATH=/opt/venv/bin:$PATH' >>/root/.profile

# Generate .nixpacks files locally
RUN nixpacks build /app \
    --name sponsorblockcasino \
    --start-cmd "python sponsorblockcasino.py"

RUN docker run -it my-app

# Install Nix dependencies
RUN nix-env -if .nixpacks/*.nix && nix-collect-garbage -d

# Install Python dependencies
RUN --mount=type=cache,id=s/f37f20e4-ec25-4620-9359-ffe68caf8d61-/root/cache/pip,target=/root/.cache/pip \
    python -m venv --copies /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install -r requirements.txt

# Set the start command that nixpacks should detect
CMD ["python", "sponsorblockcasino.py"]
