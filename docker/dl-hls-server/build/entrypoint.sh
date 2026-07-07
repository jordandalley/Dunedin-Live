#!/bin/sh

# Start Nginx in the background
nginx

if [ -z "$RTSP_URL" ]; then
    echo "Error: RTSP_URL environment variable is not set."
    exit 1
fi
if [ -z "$STREAM_NAME" ]; then
    echo "Error: STREAM_NAME environment variable is not set."
    exit 1
fi
echo "Starting JPEG fetcher loop in the background..."
if [ ! -z "$IMG_URL" ]; then
    # Run the fetcher in a background subshell
    (
        while true; do
            # curl fetches the image and saves it to the tmpfs ramdisk.
            # -s hides the progress bar, --anyauth handles Basic/Digest camera logins
            curl -s --anyauth -o /hls/camera1.jpg "${IMG_URL}"
            sleep 60
        done
    ) &
else
    echo "Warning: IMG_URL is not set. Skipping image fetcher."
fi

echo "Starting FFmpeg to ingest RTSP and output fMP4 HLS..."

# Run FFmpeg in the foreground
exec ffmpeg \
    -loglevel level+info \
    -err_detect ignore_err \
    -y \
    -fflags +genpts \
    -thread_queue_size 5120 \
    -probesize 5000000 \
    -analyzeduration 5000000 \
    -timeout 5000000 \
    -rtsp_transport udp \
    -i "${RTSP_URL}" \
    -thread_queue_size 5120 \
    -f lavfi \
    -i anullsrc=cl=mono:r=44100 \
    -dn \
    -sn \
    -map 0:0 \
    -tag:v hvc1 \
    -c:v copy \
    -map 1:0 \
    -c:a aac \
    -b:a 8k \
    -shortest \
    -bsf:a aac_adtstoasc \
    -flags +low_delay \
    -f hls \
    -start_number 0 \
    -hls_time 6 \
    -hls_list_size 60 \
    -hls_flags append_list+delete_segments+program_date_time+independent_segments+temp_file \
    -hls_delete_threshold 4 \
    -hls_segment_type fmp4 \
    -hls_fmp4_init_filename "${STREAM_NAME}-init.mp4" \
    -hls_fmp4_init_resend 1 \
    -master_pl_name "${STREAM_NAME}-master.m3u8" \
    -hls_segment_filename "/hls/${STREAM_NAME}-%d.m4s" \
    "/hls/${STREAM_NAME}.m3u8"
