from PIL import Image
import torch

from unimernet.models import load_model
from unimernet.processors import load_processor


IMAGE_PATH = r"D:\Projects\VKS_Expert_AI\vision\tests\formula.png"


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

pixel_values = pixel_values.unsqueeze(0)


print(
    "INPUT:",
    pixel_values.shape
)


with torch.no_grad():

    encoder_output = model.model.model.encoder(
        pixel_values
    )


print(type(encoder_output))

print(
    encoder_output.last_hidden_state.shape
)


print(
    encoder_output.last_hidden_state.mean()
)

print(
    encoder_output.last_hidden_state.std()
)
