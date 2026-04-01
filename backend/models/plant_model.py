import torch
import torch.nn.functional as F
import numpy as np
import os
from PIL import Image
from torchvision import transforms
from .BryoFormer import BryoFormer


class UniversalPlantIdentifier:
    def __init__(self, model_path, device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 你的44个苔藓类别
        self.class_names = [
            'Barbulaunguiculata', 'Bartramia pomiformis', 'Bryum argenteum', 'Calohypnum plumiforme',
            'Climacium dendroides', 'Conocephalum conicum', 'Dumortiera hirsuta', 'Ectropothecium ohosimense',
            'Entodon challengeri', 'Entodon cladorrhizans', 'Entodon flavescens', 'Entodon luridus',
            'Entodon macropodus', 'Eurohypnum leptothallum', 'Funaria hygrometrica', 'Haplocladium microphyllum',
            'Hypnum cupressiforme', 'Leucobryum glaucum', 'Marchantia emarginata subsp. Tosana',
            'Marchantia polymorpha', 'Myuroclada maximowiczii', 'Physcomitrium sphaericum',
            'Plagiochasma rupestre', 'Plagiomnium acutum', 'Plagiomnium cuspidatum', 'Pogonatum inflexum',
            'Polytrichum commune', 'Pseudotaxiphyllum pohliaecarpum', 'Reboulia hemisphaerica',
            'Rhodobryum giganteum', 'Rhodobryum roseum', 'Riccia fluitans', 'Ricciocarpus natans',
            'Sphagnum palustre', 'Taxiphyllum taxirameum', 'Thuidium assimile', 'Thuidium cymbifolium',
            'Thuidium kanedae', 'Thuidium pristocalyx', 'Venturiella sinensis', 'abietinella_abietina',
            'hylocomium_splendens', 'pleurozium_schreberi', 'pseudoscleropodium_purum'
        ]

        print(f"🌿 苔藓类别数量: {len(self.class_names)}")

        # 先尝试直接加载整个模型
        self.model_loaded = False
        self.model = None

        if model_path and os.path.exists(model_path):
            try:
                print(f"📥 加载权重文件: {model_path}")
                print(f"📏 文件大小: {os.path.getsize(model_path) / 1024 / 1024:.2f} MB")

                # 方法1: 直接加载整个模型
                print("🔄 尝试直接加载模型对象...")
                loaded_obj = torch.load(model_path, map_location=self.device, weights_only=False)
                print(f"📦 加载的对象类型: {type(loaded_obj)}")
                print(f"📦 加载的对象: {loaded_obj}")

                if isinstance(loaded_obj, BryoFormer):
                    print("✅ 成功加载 BryoFormer 模型实例")
                    self.model = loaded_obj
                    self.model_loaded = True
                    print(f"🔢 加载模型的类别数: {self.model.num_classes}")
                else:
                    print("❌ 加载的对象不是 BryoFormer 类型")
                    print("🔄 尝试作为 state_dict 加载...")

                    # 方法2: 创建新模型并加载权重
                    self.model = BryoFormer(
                        img_size=224,
                        patch_size=16,
                        in_chans=3,
                        num_classes=44,  # 重要：改为44
                        embed_dim=384,
                        depth=8,
                        mlp_ratio=2.
                    )

                    if isinstance(loaded_obj, dict):
                        print(f"🔑 字典键: {loaded_obj.keys()}")
                        # 如果是字典，尝试不同的键
                        if 'state_dict' in loaded_obj:
                            self.model.load_state_dict(loaded_obj['state_dict'])
                            print("✅ 从 state_dict 加载权重")
                            self.model_loaded = True
                        elif 'model' in loaded_obj:
                            self.model.load_state_dict(loaded_obj['model'])
                            print("✅ 从 model 键加载权重")
                            self.model_loaded = True
                        elif 'weights' in loaded_obj:
                            self.model.load_state_dict(loaded_obj['weights'])
                            print("✅ 从 weights 键加载权重")
                            self.model_loaded = True
                        else:
                            # 尝试直接加载整个字典
                            try:
                                self.model.load_state_dict(loaded_obj)
                                print("✅ 直接加载字典权重")
                                self.model_loaded = True
                            except Exception as e:
                                print(f"❌ 直接加载字典失败: {e}")
                    else:
                        print("❌ 无法识别的权重格式，创建新模型")
                        # 创建新的模型
                        self.model = BryoFormer(
                            img_size=224,
                            patch_size=16,
                            in_chans=3,
                            num_classes=44,
                            embed_dim=384,
                            depth=8,
                            mlp_ratio=2.
                        )

            except Exception as e:
                print(f"❌ 权重加载失败: {e}")
                import traceback
                traceback.print_exc()
                # 创建新的模型作为备选
                self.model = BryoFormer(
                    img_size=224,
                    patch_size=16,
                    in_chans=3,
                    num_classes=44,
                    embed_dim=384,
                    depth=8,
                    mlp_ratio=2.
                )

        # 如果模型还是None，创建新模型
        if self.model is None:
            print("⚠️ 创建新的 BryoFormer 模型")
            self.model = BryoFormer(
                img_size=224,
                patch_size=16,
                in_chans=3,
                num_classes=44,
                embed_dim=384,
                depth=8,
                mlp_ratio=2.
            )

        self.model = self.model.to(self.device)
        self.model.eval()
        print(f"🎯 模型状态: {'预训练权重' if self.model_loaded else '随机初始化'}")
        if hasattr(self.model, 'num_classes'):
            print(f"🔢 模型输出维度: {self.model.num_classes}")
        else:
            print("⚠️ 模型没有 num_classes 属性")

        # 图像预处理
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    async def predict(self, image_path, top_k=3):
        """真正的苔藓分类预测"""
        try:
            print(f"🔍 开始预测，模型加载状态: {self.model_loaded}")
            if hasattr(self.model, 'num_classes'):
                print(f"📊 模型类别数: {self.model.num_classes}")

            # 打开图片
            image = Image.open(image_path).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            print(f"📊 输入张量形状: {input_tensor.shape}")

            # 模型推理
            with torch.no_grad():
                outputs = self.model(input_tensor)
                print(f"📊 模型输出形状: {outputs.shape}")
                print(f"📊 输出值范围: {outputs.min().item():.4f} ~ {outputs.max().item():.4f}")

                # 获取概率
                probabilities = F.softmax(outputs, dim=1)
                top_probs, top_indices = torch.topk(probabilities, top_k)

                print(f"🎯 前{top_k}个预测:")
                results = []
                for i in range(top_k):
                    class_idx = top_indices[0][i].item()
                    confidence = top_probs[0][i].item()

                    # 确保索引在范围内
                    if class_idx < len(self.class_names):
                        class_name = self.class_names[class_idx]
                    else:
                        class_name = f"未知类别_{class_idx}"

                    result = {
                        "name": class_name,
                        "sci_name": class_name,
                        "family": "苔藓植物",
                        "confidence": round(confidence, 4),
                        "class_id": class_idx
                    }
                    results.append(result)
                    print(f"  {i + 1}. {class_name}: {confidence:.4f}")

            return {
                "success": True,
                "identification": {
                    "predictions": results,
                    "top_prediction": results[0] if results else None
                },
                "message": f"识别成功: {results[0]['name']}" if results else "识别失败",
                "model_type": "BryoFormer苔藓分类",
                "model_loaded": self.model_loaded
            }

        except Exception as e:
            print(f"❌ 预测失败: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "message": f"识别失败: {str(e)}"}