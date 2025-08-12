# Dunedin-Live Docker Containers #

Each of the folders here contains a different docker container that performs a different role for the Dunedin Livestream

All docker containers share the same docker network 'dunedin-live'. This network is initialised by running the following command, and only needs to be run once: `docker network create dunedin-live`

## dl-camera-control ##

This docker container runs as a daemon and makes automated shutter speed adjustments to the Provision-ISR DI-380IPEN-MVF-V3 camera settings according to dawn, sunrise, sunset and dusk.

The Provision-ISR DI-380IPEN-MVF-V3 on its own, does not have sufficient automation to select the appropriate shutter speed and typically relies on dialling the gain up and down.

In order to avoid graininess, the gain setting on the Dunedin-Live camera is set very low at '2' with the shutter speed used instead as a way of controlling exposure and frame rate.

## dl-timelapse-capturer ##

This docker container runs as a daemon that downloads snapshots directly from the Provision-ISR DI-380IPEN-MVF-V3 camera every 10 seconds and stores them in a folder according to the current date.

## dl-timelapse-stitcher ##

This docker container runs on a schedule using crontab at midnight every night:

`0 0 * * * /usr/bin/docker compose --project-directory /docker/dl-timelapse-stitcher run --rm dl-timelapse-stitcher`

The container uses ffmpeg to compile a timelapse of the images collected by the 'dl-timelapse-capturer' process/container from the day prior.

The video is compiled at 30 FPS, which equates to 5 minutes per second of video.

Once the timelapse video is compiled, it is then uploaded to Youtube.

There are three volume mappings in the docker compose file which need close attention, such as the image sources from the 'dl-timelapse-capturer' container, and the oauth keys from the 'dl-youtube-manager' container.

## dl-wx-updater ##

This docker container runs as a daemon that simply updates the on-screen display (OSD) of the Provision-ISR DI-380IPEN-MVF-V3 camera every 10 minutes with updated weather information pulled from the Metservice mobile weather API's.

## dl-youtube-manager ##

This docker container runs on a schedule using crontab at 03:00 and 15:00 each day:

```
0 15 * * * /usr/bin/docker compose --project-directory /docker/dl-youtube-manager run --rm dl-youtube-manager
0 3 * * * /usr/bin/docker compose --project-directory /docker/dl-youtube-manager run --rm dl-youtube-manager
```

Youtube livestreams only have a retention of 12 hours, so this process counters that by creating a new livestream at this interval for archival purposes.

When run, it looks for a currently running stream by the stream key, and if there is one, stops it and creates a new one.
