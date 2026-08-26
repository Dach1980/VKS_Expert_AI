from vision.formula_recognizer import FormulaRecognizer


IMAGE = (
    r"D:\Projects\VKS_Expert_AI"
    r"\vision\tests\formula.png"
)


recognizer = FormulaRecognizer()


result = recognizer.recognize(
    IMAGE
)


print()
print("RESULT")
print(result)

print()
print("LaTeX:")
print(result["latex"])
