# Image Tools

Local command-line image utilities. The first command resizes an image to exact
pixel dimensions using OpenCV.

## Resize

```sh
uv sync
uv run image-tools resize input.jpg --width 630 --height 810 --output passport.jpg
```

The resize sets the requested width and height directly, so it can change the
image's aspect ratio. It does not crop, center a face, change the background, or
check passport-photo composition requirements. Existing output files are
preserved unless `--overwrite` is supplied. Input images are read locally and
are never modified.
