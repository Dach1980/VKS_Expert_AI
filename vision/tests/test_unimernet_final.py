from PIL import Image
import torch

from unimernet.models import load_model
from unimernet.processors import load_processor


IMAGE_PATH = r"D:\Projects\VKS_Expert_AI\vision\tests\formula.png"


print("Loading model")

model = load_model(
    "unimernet",
    "default"
)

model.eval()

print("Model loaded")


print("Loading processor")

processor = load_processor(
    "formula_image_eval"
)

print("Processor loaded")


image = Image.open(IMAGE_PATH).convert("RGB")


print("Processing image")

pixel_values = processor(image)


print("RAW:", pixel_values.shape)


# processor возвращает C,H,W
# добавляем batch dimension -> B,C,H,W
if pixel_values.dim() == 3:
    pixel_values = pixel_values.unsqueeze(0)


print("AFTER BATCH:", pixel_values.shape)


# UniMERNet ожидает RGB
# B,1,H,W -> B,3,H,W
if pixel_values.shape[1] == 1:
    pixel_values = pixel_values.repeat(1, 3, 1, 1)


print("FINAL INPUT:", pixel_values.shape)


with torch.no_grad():

    result = model.generate(
        {
            "image": pixel_values
        },
        do_sample=False
    )


print("\nRESULT:")
print(result)


print("\nLaTeX:")
print(result["pred_str"])
