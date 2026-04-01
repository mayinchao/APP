import os
import shutil
from flask import Flask, request, jsonify
from ultralytics import YOLO
import tempfile

app = Flask(__name__)

# 加载模型（请确保 best.pt 在当前目录或指定正确路径）
MODEL_PATH = "best.pt"
try:
    model = YOLO(MODEL_PATH)
    print(f"✅ 模型加载成功：{MODEL_PATH}")
except Exception as e:
    print(f"❌ 模型加载失败：{e}")
    model = None

@app.route('/api/plant-detect', methods=['POST'])
def plant_detect():
    if not model:
        return jsonify({"code": 500, "msg": "模型未加载"}), 500

    # 检查是否有文件上传
    if 'file' not in request.files:
        return jsonify({"code": 400, "msg": "未上传文件"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 400, "msg": "文件名为空"}), 400

    # 保存临时文件
    tmp_dir = tempfile.gettempdir()
    save_path = os.path.join(tmp_dir, "upload.jpg")
    file.save(save_path)

    try:
        # 推理
        results = model(save_path)
        detect_list = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls)
                confidence = float(box.conf)
                detect_list.append({
                    "class_name": model.names[class_id],
                    "confidence": round(confidence, 4),
                    "box": box.xyxy.tolist()[0]  # 坐标
                })
        return jsonify({
            "code": 200,
            "msg": "识别成功",
            "data": {
                "detections": detect_list,
                "image_path": save_path
            }
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": f"推理失败: {str(e)}"}), 500

@app.route('/')
def root():
    return {"msg": "菌类识别后端运行中", "model_status": "loaded" if model else "failed"}

if __name__ == '__main__':
    # 允许所有主机访问，端口8000
    app.run(host='0.0.0.0', port=8000, debug=True)