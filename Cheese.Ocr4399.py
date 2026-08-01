"""
Cheese.Ocr4399.exe 替代品
接收 base64 图片数据作为参数，输出识别结果到 stdout
"""
import sys
import base64
import io
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import onnxruntime as ort
from PIL import Image, ImageOps

ONNX_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "4399ocr", "4399ocr.onnx")
FIXED_W, FIXED_H = 160, 64

CHARSET = [
    " ", "6", "t", "y", "w", "J", "K", "k", "p", "7", "8", "9", "n", "j",
    "P", "q", "D", "G", "c", "N", "v", "X", "H", "Y", "5", "0", "h", "R",
    "f", "r", "4", "d", "A", "E", "M", "l", "V", "m", "a", "F", "s", "i",
    "z", "U", "g", "x", "u", "o", "3", "Q", "b", "e", "T", "1", "2",
]

# 全局 session（只初始化一次）
_session = None
_input_name = None
_output_name = None

def get_session():
    global _session, _input_name, _output_name
    if _session is None:
        _session = ort.InferenceSession(ONNX_MODEL_PATH, providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
        _output_name = _session.get_outputs()[0].name
    return _session, _input_name, _output_name

def recognize(img_bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
    except Exception:
        return ""
    img = img.resize((FIXED_W, FIXED_H), Image.LANCZOS)
    img = ImageOps.autocontrast(img)
    arr = np.array(img, dtype=np.float32) / 255.0
    tensor = arr.reshape(1, 1, FIXED_H, FIXED_W)
    session, input_name, output_name = get_session()
    outputs = session.run([output_name], {input_name: tensor})[0]
    return decode(outputs[0])

def decode(logits):
    res, last = [], -1
    for idx in logits:
        idx = int(idx)
        if idx != last and 0 < idx < len(CHARSET):
            res.append(CHARSET[idx])
        last = idx
    return "".join(res)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("", end="")
        sys.exit(0)

    base64_data = sys.argv[1]
    try:
        img_bytes = base64.b64decode(base64_data)
        result = recognize(img_bytes)
        print(result, end="")
    except Exception as e:
        print("", end="")
