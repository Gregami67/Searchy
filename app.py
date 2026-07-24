import os
import torch
import torch.nn.functional as F
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

device = torch.device("cpu")

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

image_dir = "./images"
valid_extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

image_paths = [
    os.path.join(image_dir, f)
    for f in os.listdir(image_dir)
    if f.lower().endswith(valid_extensions)
]
images = [Image.open(path) for path in image_paths]

query = "potato"

inputs = processor(text=query, images=images, return_tensors="pt", padding=True)

with torch.inference_mode():
    outputs = model(**inputs)

image_embeds = outputs.image_embeds
text_embeds = outputs.text_embeds

norm_image_embeds = F.normalize(image_embeds, dim=-1)
norm_text_embeds = F.normalize(text_embeds, dim=-1)

# Get similarity scores as a 1D tensor
similarities = (norm_image_embeds @ norm_text_embeds.T).squeeze()

# Zip paths with float similarity scores and sort high-to-low
results = sorted(
    zip(image_paths, similarities.tolist()), key=lambda pair: pair[1], reverse=True
)

# Print formatted results
for path, score in results:
    print(f"{score:.4f} -> {path}")
