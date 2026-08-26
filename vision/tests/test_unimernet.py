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


processor = load_processor(
    "formula_image_eval"
)


image = Image.open(
    IMAGE_PATH
).convert("RGB")


pixel_values = processor(image)


print(pixel_values.shape)


with torch.no_grad():

    result = model.generate(
        {
            "image": pixel_values
        },
        temperature=0,
        do_sample=False
    )


print(result)
