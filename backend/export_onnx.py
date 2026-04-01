from ultralytics import YOLO

# 加载你的模型
model = YOLO("best.pt")

# 导出为 ONNX 格式（会自动处理输入输出）
model.export(format="onnx")