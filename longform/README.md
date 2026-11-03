# Long-form videos (16:9, ~10 min, space topics)

All visuals are generated in code (procedural 3D globes, voxel terrain, cloud seas); no downloaded footage.
Fonts in `engine/fonts/` are Inter (SIL Open Font License).

    python3 longform/engine/narrate.py longform/scripts/<slug>.json longform/work/<slug>   # voice + timeline (~9 min)
    python3 longform/engine/mixaudio.py longform/work/<slug>                               # add ambient pad
    python3 longform/engine/render_long.py longform/work/<slug> <slug>.mp4 --stills 10,60  # check frames
    JOBS=2 python3 longform/engine/render_long.py longform/work/<slug> longform/work/<slug>/<slug>.mp4   # ~40 min
    python3 longform/engine/thumbnail.py thumb.jpg

Scene visuals available: see `make()` in `engine/scenes.py`.
