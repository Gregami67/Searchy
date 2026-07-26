# Searchy

## Plan

### Pre start

Must run in order

- load the models (CLIPModel, CLIPProcessor)
- read all image paths
- hash images (in batches?)
- compare if hash exists in db (db side)
  - add new images to db (client side)
    - calculate image embeds
    - save to db
  - remove deleted images from image paths (db side)
    - drop image hash

### Ready

#### Tasks (celery?)

- watch images paths
  - repeat hash comparison

#### Flask

- search by text (db side)
- search by image (db side) (optional)
