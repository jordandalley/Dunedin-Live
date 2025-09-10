# Use a lightweight Python image
FROM python:slim

# Install ffmpeg and any other system dependencies vainfo libmfx-gen1.2 libva-drm2 libva-x11-2 libva2
RUN apt-get update \
&& apt-get install -y curl gnupg \
&& mkdir -p /etc/apt/keyrings \
&& curl -fsSL https://repo.jellyfin.org/jellyfin_team.gpg.key | gpg --dearmor -o /etc/apt/keyrings/jellyfin.gpg \
&& export VERSION_OS="$( awk -F'=' '/^ID=/{ print $NF }' /etc/os-release )" \
&& export VERSION_CODENAME="$( awk -F'=' '/^VERSION_CODENAME=/{ print $NF }' /etc/os-release )" \
&& export DPKG_ARCHITECTURE="$( dpkg --print-architecture )" \
&& echo "Types: deb" > /etc/apt/sources.list.d/jellyfin.sources \
&& echo "URIs: https://repo.jellyfin.org/${VERSION_OS}" >> /etc/apt/sources.list.d/jellyfin.sources \
&& echo "Suites: ${VERSION_CODENAME}" >> /etc/apt/sources.list.d/jellyfin.sources \
&& echo "Components: main" >> /etc/apt/sources.list.d/jellyfin.sources \
&& echo "Architectures: ${DPKG_ARCHITECTURE}" >> /etc/apt/sources.list.d/jellyfin.sources \
&& echo "Signed-By: /etc/apt/keyrings/jellyfin.gpg" >> /etc/apt/sources.list.d/jellyfin.sources \
&& apt-get update \
&& apt-get install -y jellyfin-ffmpeg7 \
&& ln -s /usr/lib/jellyfin-ffmpeg/ffmpeg /usr/bin/ffmpeg \
&& rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY build/timelapse-stitcher.py .

# Set python in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Command to run the app
CMD ["python", "timelapse-stitcher.py"]
