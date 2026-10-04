from rapidocr_onnxruntime import RapidOCR 

engine = RapidOCR()

image_path = "demo.png"

result, elapse = engine(image_path)

final_text = ""
if result:
  for item in result:
    bbox = item[0]
    text = item[1]
    confidence = item[2]

    final_text = final_text + text

    print(f"Text: {text} | Confidence: {float(confidence):.2f}")

print(f"Tổng thời gian xử lý CPU: {sum(elapse):.4f} giây")
print(final_text)