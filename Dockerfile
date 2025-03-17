FROM ghcr.io/railwayapp/nixpacks:ubuntu

# Install git (in case not already installed)
RUN apt-get update && apt-get install -y git

# Install nixpacks
RUN curl -sSL https://nixpacks.com/install.sh | bash

# Ensure nixpacks is available
ENV PATH="/usr/local/bin:$PATH"
RUN echo $PATH

# Set working directory to /app
WORKDIR /app

# Copy everything from repo into /app
COPY . /app

# Initialize and update submodules
RUN git init && git submodule update --init --recursive

# Generate .nixpacks files locally
RUN nixpacks build --name temp-build /app

# Install Nix dependencies
RUN nix-env -if .nixpacks/*.nix && nix-collect-garbage -d

# Install Python dependencies with nixpacks's default method
RUN python -m venv --copies /opt/venv && . /opt/venv/bin/activate && \
    pip install -r requirements.txt

# Add the virtual environment to PATH
RUN printf '\nPATH=/opt/venv/bin:$PATH' >> /root/.profile

# Copy project files last
COPY . /app/.

# Default command
CMD ["python", "sponsorblockcasino.py"]
