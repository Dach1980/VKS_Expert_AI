from PIL import Image
import torch
import re

from unimernet.models import load_model
from unimernet.processors import load_processor


class FormulaRecognizer:

    def __init__(self):

        print("Loading UniMERNet...")

        self.model = load_model(
            "unimernet",
            "default"
        )

        self.model.eval()

        self.processor = load_processor(
            "formula_image_eval"
        )

        print("UniMERNet loaded")


    def preprocess(self, image_path):

        image = (
            Image.open(image_path)
            .convert("RGB")
        )

        tensor = self.processor(image)


        # processor returns CHW
        if tensor.dim() == 3:
            tensor = tensor.unsqueeze(0)


        # grayscale -> RGB
        if tensor.shape[1] == 1:
            tensor = tensor.repeat(
                1,3,1,1
            )


        return tensor



    def clean_latex(self, latex):

        if not latex:
            return latex


        # убрать двойные пробелы

        latex = re.sub(
            r"\s+",
            " ",
            latex
        )


        # степени

        latex = re.sub(
            r"\^\s*\{\s*(.*?)\s*\}",
            r"^{\1}",
            latex
        )


        # убрать пробелы около символов

        latex = latex.replace(
            " ^",
            "^"
        )

        latex = latex.replace(
            " {",
            "{"
        )


        # математические пробелы

        latex = latex.replace(
            " m c ",
            " mc "
        )


        return latex.strip()



    @torch.no_grad()
    def recognize(
        self,
        image_path
    ):

        tensor = self.preprocess(
            image_path
        )


        result = self.model.generate(
            {
                "image": tensor
            },
            temperature=0.2,
            do_sample=False
        )


        raw = result["pred_str"][0]


        latex = self.clean_latex(
            raw
        )


        return {
            "latex": latex,
            "raw": raw,
            "tokens": result["pred_tokens"][0]
        }
    