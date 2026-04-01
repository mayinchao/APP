import flet as ft
import navigation_bars
from flet import (
    Page, Container, Row, Column, IconButton, Text, PopupMenuButton,
    PopupMenuItem, Icon, Stack, alignment, border_radius, Colors, ScrollMode,
    Card, Image, ElevatedButton, TextField, Switch, SnackBar, Divider, ListView,
    Geolocator, GeolocatorPosition, Video,
    AlertDialog, TextButton, ListTile
)
import datetime
import uuid
import aiohttp
import asyncio
import os
import json
import platform
import socket
import subprocess   # 用于创建隐藏窗口


class PlantAPIClient:
    """与后端 YOLO 识别服务通信的客户端"""
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def set_base_url(self, new_url):
        """动态修改后端地址"""
        self.base_url = new_url

    async def identify_plant(self, image_path):
        """调用后端识别接口，返回识别结果"""
        url = f"{self.base_url}/api/plant-detect"
        try:
            async with aiohttp.ClientSession() as session:
                with open(image_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('file', f, filename=os.path.basename(image_path))
                    async with session.post(url, data=data) as resp:
                        result = await resp.json()
                        if result.get('code') == 200:
                            detections = result.get('data', {}).get('detections', [])
                            if detections:
                                # 取置信度最高的检测结果
                                top = max(detections, key=lambda x: x['confidence'])
                                class_name = top['class_name']
                                confidence = top['confidence']
                                # 注意：毒性判断现在移至前端，因为名称映射可能改变
                                return {
                                    "success": True,
                                    "data": {
                                        "identification": {
                                            "top_prediction": {
                                                "name": class_name,
                                                "confidence": confidence
                                            }
                                        }
                                    }
                                }
                            else:
                                return {"success": False, "message": "未检测到任何菌类"}
                        else:
                            return {"success": False, "message": result.get('msg', '识别失败')}
        except Exception as e:
            return {"success": False, "message": f"网络请求异常: {str(e)}"}


class PlantApp:
    """菌类识别应用主类"""

    # 名称映射：后端返回的旧名称 -> 前端使用的正确名称
    NAME_MAPPING = {
        "鸡中菌": "鸡枞菌",
        "蓝牦牛杆菌": "兰茂牛肝菌",
        # 如果还有其他不匹配的名称，可以在此处添加
    }

    # 毒蘑菇列表（使用前端正确的名称）
    TOXIC_MUSHROOMS = ['致命鹅膏菌', '毒蝇伞', '白毒伞', '绿褶菌', '死亡帽']

    def __init__(self, page: Page):
        self.page = page
        # 修改为云函数地址
        self.backend_url = "https://1415794693-dermy2rvju.ap-shanghai.tencentscf.com"
        self.api_client = PlantAPIClient(self.backend_url)

        # 检测是否为桌面环境（Windows/macOS/Linux）
        self.is_desktop = platform.system() in ('Windows', 'Darwin', 'Linux')

        # ========== 存储可用性标志 ==========
        self.storage_available = True  # 初始假定可用，后续检测

        # ========== 应急响应系统状态管理 ==========
        self.first_aid_video_url = "http://localhost:8000/static/videos/emergency_first_aid.mp4"
        self.local_first_aid_video_path = os.path.join(os.path.dirname(__file__),
                                                         "assets/videos/emergency_first_aid.mp4")
        self.emergency_contacts = []
        self.default_emergency_phone = "120"
        self.geolocator = Geolocator()
        self.current_position = None
        self.page.overlay.append(self.geolocator)
        self.is_emergency_mode = False

        # 原有状态管理
        self.current_page_index = 0
        self.page_history = []
        self.editing_profile = False

        # 用户名改为“用户”
        self.user_info = {
            "username": "用户",
            "user_id": "user_" + str(uuid.uuid4())[:8],
            "join_date": "2025-09-11",
            "bio": "热爱自然，喜欢探索菌类的奥秘",
            "browsed": 52,
            "searched": 18,
            "avatar_url": "https://picsum.photos/200/200"
        }

        self.browsing_history = []
        self.collected_plants = set()
        self.collection_history = []
        self.plant_comments = {}
        self.comment_visibility = {}
        self.user_reactions = {}
        self.notifications = []
        self.unread_count = 0

        # ========== 菌类数据（更新名称、描述、图片） ==========
        self.all_plants = [
            {
                "name": "致命鹅膏菌",
                "desc": "剧毒蘑菇，误食可致死",
                "image_url": "https://tse2-mm.cn.bing.net/th/id/OIP-C.0LZfGV2oUY_O8NbpSD03fwHaFQ?w=225&h=180&c=7&r=0&o=7&dpr=1.5&pid=1.7&rm=3",
                "sci_name": "Amanita phalloides",
                "family": "鹅膏菌科 鹅膏菌属",
                "distribution": "广泛分布于温带及亚热带地区，夏秋季生于阔叶林或针阔混交林地上。",
                "features": "菌盖光滑，黄绿色至橄榄色，直径5-15cm；菌柄基部有菌托，上部有菌环；孢子印白色。",
                "habit": "与壳斗科、松科等树木形成外生菌根，喜温暖湿润环境。",
                "culture": "世界上最著名的毒蘑菇，含有鹅膏毒肽，中毒后死亡率极高。",
                "flower_language": "",
                "poem": "",
                "is_toxic": True
            },
            {
                "name": "鸡枞菌",
                "desc": "可食用美味菌类，与白蚁共生",
                "image_url": "https://tse3-mm.cn.bing.net/th/id/OIP-C.8vfcJyj5lzoRAOU70NyYrwHaFj?w=226&h=180&c=7&r=0&o=7&dpr=1.5&pid=1.7&rm=3",
                "sci_name": "Termitomyces albuminosus",
                "family": "口蘑科 蚁巢伞属",
                "distribution": "中国南方各省，东南亚也有分布",
                "features": "菌盖浅褐色，直径5-20cm，表面光滑；菌柄基部膨大，与白蚁巢相连；菌肉白色，味鲜美。",
                "habit": "夏季雨后生于白蚁巢上，形成菌圃，依赖白蚁共生。",
                "culture": "著名的食用菌，被称为‘菌中之王’，营养丰富，味道鲜美。",
                "flower_language": "",
                "poem": "",
                "is_toxic": False
            },
            {
                "name": "兰茂牛肝菌",
                "desc": "可食用菌，菌肉受伤变蓝，云南特产",
                "image_url": "https://tse3-mm.cn.bing.net/th/id/OIP-C.08zwN2w6E0t4lYFzGN5qOgHaFj?w=265&h=199&c=7&r=0&o=7&dpr=1.5&pid=1.7&rm=3",
                "sci_name": "Lanmaoa asiatica",
                "family": "牛肝菌科 兰茂牛肝菌属",
                "distribution": "中国西南、华南地区",
                "features": "菌盖半球形，黄褐色至红褐色，菌肉白色，受伤后迅速变蓝；菌管黄色，孔口红色。",
                "habit": "夏秋季生于针叶林或混交林地上，与松树等形成菌根。",
                "culture": "可食用，但需彻底煮熟；民间常用于炒食或煲汤。",
                "flower_language": "",
                "poem": "",
                "is_toxic": False
            },
            {
                "name": "毒蝇伞",
                "desc": "致幻毒菌，不可食用",
                "image_url": "https://example.com/fly_agaric.jpg",
                "sci_name": "Amanita muscaria",
                "family": "鹅膏菌科 鹅膏菌属",
                "distribution": "北半球温带地区",
                "features": "菌盖鲜红色，有白色鳞片，菌柄有菌环，基部膨大。",
                "habit": "夏秋季生于针叶林或混交林地上，与松树、桦树共生。",
                "culture": "含有毒蝇碱等致幻成分，古代用于宗教仪式。",
                "flower_language": "",
                "poem": "",
                "is_toxic": True
            },
            {
                "name": "松茸",
                "desc": "珍贵食用菌，被誉为‘菌中之王’",
                "image_url": "https://example.com/matsutake.jpg",
                "sci_name": "Tricholoma matsutake",
                "family": "口蘑科 口蘑属",
                "distribution": "东亚、北美等地",
                "features": "菌盖黄褐色，中央有鳞片；菌柄粗壮，有菌环；具浓郁香气。",
                "habit": "夏秋季生于松林或针阔混交林地上，与松树形成菌根。",
                "culture": "高档食材，价格昂贵，富含氨基酸和微量元素。",
                "flower_language": "",
                "poem": "",
                "is_toxic": False
            },
            {
                "name": "白毒伞",
                "desc": "剧毒蘑菇，外形似可食用蘑菇",
                "image_url": "https://example.com/death_angel.jpg",
                "sci_name": "Amanita virosa",
                "family": "鹅膏菌科 鹅膏菌属",
                "distribution": "欧洲、北美、中国东北",
                "features": "全体白色，菌盖光滑，菌柄有菌环，基部有菌托。",
                "habit": "夏秋季生于阔叶林地上。",
                "culture": "含有剧毒鹅膏毒肽，误食后死亡率极高，常与可食用蘑菇混淆。",
                "flower_language": "",
                "poem": "",
                "is_toxic": True
            },
            {
                "name": "绿褶菌",
                "desc": "有毒，误食引起肠胃炎",
                "image_url": "https://example.com/green_spore.jpg",
                "sci_name": "Chlorophyllum molybdites",
                "family": "蘑菇科 绿褶菇属",
                "distribution": "全球分布",
                "features": "菌盖灰白色，有褐色鳞片，菌褶成熟后呈灰绿色，孢子印绿色。",
                "habit": "夏季生于草地、田野，群生。",
                "culture": "常见毒蘑菇，误食后出现呕吐、腹泻等肠胃炎症状。",
                "flower_language": "",
                "poem": "",
                "is_toxic": True
            },
            {
                "name": "牛肝菌",
                "desc": "多种可食用牛肝菌的总称",
                "image_url": "https://example.com/boletus.jpg",
                "sci_name": "Boletus edulis",
                "family": "牛肝菌科 牛肝菌属",
                "distribution": "北半球温带",
                "features": "菌盖褐色，菌肉白色，菌管黄色，柄粗壮。",
                "habit": "夏秋季生于针叶林或混交林地上。",
                "culture": "味道鲜美，是著名的食用菌，但需注意有些品种有毒。",
                "flower_language": "",
                "poem": "",
                "is_toxic": False
            }
        ]

        self.init_components()
        self.assemble_page()
        self.create_welcome_notification()
        # 加载存储的地址和联系人
        self.page.run_task(self.load_emergency_contacts)
        self.page.run_task(self.load_backend_url)
        # 启动自动检测（会等待存储加载完成后进行）
        self.page.run_task(self.auto_detect_if_needed)
        self.page.run_task(self.show_launch_location_dialog)

    # ========== 存储可用性检测 ==========
    async def check_storage(self):
        """检测 client_storage 是否可用，超时则设为不可用"""
        try:
            await asyncio.wait_for(self.page.client_storage.get("__test__"), timeout=2.0)
            self.storage_available = True
            print("✅ 本地存储可用")
        except (asyncio.TimeoutError, Exception):
            self.storage_available = False
            print("⚠️ 本地存储不可用（超时），将降级为内存存储，配置不会持久化")

    # ========== 安全存储辅助函数（根据存储可用性决定是否实际调用） ==========
    async def _safe_storage_get(self, key, default=None, timeout=2.0, retries=1):
        """安全读取 client_storage，若存储不可用则直接返回默认值"""
        if not self.storage_available:
            return default
        for attempt in range(retries):
            try:
                value = await asyncio.wait_for(
                    self.page.client_storage.get(key), timeout=timeout
                )
                return value
            except (asyncio.TimeoutError, Exception):
                if attempt == retries - 1:
                    print(f"⚠️ 读取 {key} 失败（存储可能不可用）")
                    self.storage_available = False  # 后续不再尝试
                    return default
                await asyncio.sleep(0.3)
        return default

    async def _safe_storage_set(self, key, value, timeout=2.0, retries=1):
        """安全写入 client_storage，若存储不可用则直接返回 False"""
        if not self.storage_available:
            return False
        for attempt in range(retries):
            try:
                await asyncio.wait_for(
                    self.page.client_storage.set(key, value), timeout=timeout
                )
                return True
            except (asyncio.TimeoutError, Exception):
                if attempt == retries - 1:
                    print(f"⚠️ 写入 {key} 失败（存储可能不可用）")
                    self.storage_available = False
                    return False
                await asyncio.sleep(0.3)
        return False

    # ========== 后端地址管理 ==========
    async def load_backend_url(self):
        """加载后端地址（带超时）"""
        saved = await self._safe_storage_get("backend_url")
        if saved:
            self.backend_url = saved
            self.api_client.set_base_url(saved)
            print(f"✅ 已加载后端地址: {saved}")

    async def save_backend_url(self, url):
        """保存后端地址（带超时）"""
        success = await self._safe_storage_set("backend_url", url)
        if success:
            self.backend_url = url
            self.api_client.set_base_url(url)
            print(f"✅ 后端地址已保存: {url}")
        else:
            # 内存模式：仅更新当前会话
            self.backend_url = url
            self.api_client.set_base_url(url)
            # 可选：提示用户
            self.page.snack_bar = SnackBar(Text("⚠️ 地址已临时生效，但无法持久化（存储不可用）"), bgcolor=Colors.ORANGE)
            self.page.snack_bar.open = True
            self.page.update()

    # ========== 本地后端启动与检测 ==========
    async def check_local_backend(self, url="http://localhost:8000"):
        """检查本地后端是否可用"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/", timeout=3) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("model_status") == "loaded":
                            return True
            return False
        except:
            return False

    async def start_local_backend(self):
        """尝试启动本地后端服务（仅桌面环境，隐藏终端窗口）"""
        if not self.is_desktop:
            print("当前环境不支持启动本地后端")
            return False

        # 获取 app.py 所在目录（Frontend）的父目录（项目根目录），再拼接 backend
        frontend_dir = os.path.dirname(__file__)
        project_root = os.path.dirname(frontend_dir)  # 父目录
        backend_dir = os.path.join(project_root, "backend")
        bat_path = os.path.join(backend_dir, "start_backend.bat")
        if not os.path.exists(bat_path):
            print(f"未找到启动脚本: {bat_path}")
            return False

        try:
            # 在 Windows 上隐藏控制台窗口
            creationflags = 0
            if platform.system() == 'Windows':
                creationflags = subprocess.CREATE_NO_WINDOW

            # 启动子进程，并设置工作目录为 backend 文件夹
            process = await asyncio.create_subprocess_shell(
                f'"{bat_path}"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                creationflags=creationflags,
                cwd=backend_dir
            )
            # 等待几秒让服务启动
            await asyncio.sleep(3)

            # 检查服务是否启动成功
            if await self.check_local_backend():
                print("本地后端启动成功")
                return True
            else:
                print("本地后端启动失败，请手动检查")
                return False
        except Exception as e:
            print(f"启动本地后端时出错: {e}")
            return False

    async def auto_detect_on_startup(self):
        """应用启动时自动检测可用后端地址（后台运行，不阻塞UI）"""
        # 优先使用云函数地址
        cloud_function_url = "https://1415794693-dermy2rvju.ap-shanghai.tencentscf.com"
        candidates = [
            cloud_function_url,                # 优先云函数
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://10.0.2.2:8000",          # Android 模拟器专用
        ]
        # 添加本机局域网 IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            candidates.append(f"http://{local_ip}:8000")
        except:
            pass

        # 先遍历候选地址
        for url in candidates:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{url}/", timeout=3) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("model_status") == "loaded":
                                # 找到可用的地址
                                if self.backend_url != url:
                                    self.backend_url = url
                                    self.api_client.set_base_url(url)
                                    await self.save_backend_url(url)
                                    print(f"✅ 自动检测到可用后端: {url}")
                                    self.page.snack_bar = SnackBar(
                                        Text(f"✅ 已自动连接到后端: {url}"),
                                        bgcolor=Colors.GREEN,
                                        duration=3000
                                    )
                                    self.page.snack_bar.open = True
                                    self.page.update()
                                return
            except Exception:
                continue

        # 所有候选地址均不可用，尝试启动本地后端
        print("所有后端地址均不可用，尝试启动本地后端...")
        started = await self.start_local_backend()
        if started:
            self.backend_url = "http://localhost:8000"
            self.api_client.set_base_url(self.backend_url)
            await self.save_backend_url(self.backend_url)
            self.page.snack_bar = SnackBar(
                Text("✅ 已自动启动并连接到本地后端"),
                bgcolor=Colors.GREEN
            )
            self.page.snack_bar.open = True
            self.page.update()
            return
        else:
            print("无法启动本地后端，请手动启动")
            self.page.snack_bar = SnackBar(
                Text("⚠️ 未检测到后端服务，请在设置中手动配置"),
                bgcolor=Colors.ORANGE,
                duration=5000
            )
            self.page.snack_bar.open = True
            self.page.update()

    async def auto_detect_if_needed(self):
        """仅在存储地址不可用时才自动检测"""
        # 先尝试测试已保存的地址（如果已加载）
        if self.backend_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.backend_url}/", timeout=2) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("model_status") == "loaded":
                                print(f"✅ 已保存的后端地址可用: {self.backend_url}")
                                return
            except:
                pass
        # 保存地址不可用，启动自动检测
        await self.auto_detect_on_startup()

    # ========== 应急联系人管理 ==========
    async def load_emergency_contacts(self):
        """加载紧急联系人（带超时）"""
        contacts_json = await self._safe_storage_get("emergency_contacts")
        if contacts_json:
            try:
                self.emergency_contacts = json.loads(contacts_json)
                print(f"✅ 加载到{len(self.emergency_contacts)}个紧急联系人")
            except json.JSONDecodeError as e:
                print(f"❌ 紧急联系人数据解析失败: {e}")

    async def save_emergency_contacts(self):
        """保存紧急联系人（带超时）"""
        success = await self._safe_storage_set(
            "emergency_contacts",
            json.dumps(self.emergency_contacts, ensure_ascii=False)
        )
        if success:
            print("✅ 紧急联系人已保存")
        else:
            # 内存模式：仅提示，不保存
            self.page.snack_bar = SnackBar(Text("⚠️ 联系人已添加，但无法持久化（存储不可用）"), bgcolor=Colors.ORANGE)
            self.page.snack_bar.open = True
            self.page.update()

    # ========== 核心：返回上一页方法 ==========
    def go_back(self, e=None):
        """返回上一页"""
        if self.page_history:
            last_index = self.page_history.pop()
            self.current_page_index = last_index
            self.qq_nav.update_selection(last_index)
            self.on_custom_nav_click(last_index)

            if hasattr(self, 'top_bar'):
                back_button = self.top_bar.content.controls[0].content
                back_button.disabled = len(self.page_history) == 0
                if last_index == 0:
                    self.top_bar.content.controls[1].content.value = "滇菌智护"

            snack = SnackBar(Text("返回上一页"))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

    # ========== 应急响应核心功能：地理位置获取 ==========
    async def get_current_location(self):
        """异步获取用户当前地理位置"""
        try:
            print("📍 开始获取当前位置...")
            permission = await self.geolocator.request_permission()
            if permission != "granted":
                print("❌ 位置权限被拒绝")
                return {"success": False, "message": "位置权限被拒绝，请开启权限后重试"}

            position: GeolocatorPosition = await self.geolocator.get_current_position(accuracy="high")
            self.current_position = {
                "latitude": position.latitude,
                "longitude": position.longitude,
                "accuracy": position.accuracy,
                "timestamp": position.timestamp
            }
            print(f"✅ 位置获取成功：{self.current_position}")
            return {"success": True, "data": self.current_position}
        except Exception as e:
            print(f"❌ 位置获取异常: {e}")
            return {"success": False, "message": f"位置获取失败: {str(e)}"}

    def generate_location_share_text(self, plant_name):
        """生成位置分享文本"""
        if not self.current_position:
            return "【紧急求助】我疑似误食剧毒野生菌，无法获取当前位置，请立即联系我！"

        lat = self.current_position["latitude"]
        lon = self.current_position["longitude"]
        map_url = f"https://apis.map.qq.com/uri/v1/marker?marker=coord:{lat},{lon};title:我的位置&referer=滇菌智护"

        return f"""【紧急求助】我疑似误食剧毒野生菌【{plant_name}】，请立即协助救援！
我的实时位置：纬度 {lat}，经度 {lon}
地图导航链接：{map_url}
急救指引：请立即联系就近医院，携带疑似毒菌样本就医，切勿自行催吐/服药！"""

    # ========== 应急响应核心功能：紧急拨号与短信发送 ==========
    async def make_emergency_call(self, phone_number=None):
        """一键拨打急救电话"""
        target_phone = phone_number if phone_number else self.default_emergency_phone
        try:
            print(f"📞 正在拨打急救电话: {target_phone}")
            await self.page.launch_url(f"tel:{target_phone}")
            return {"success": True}
        except Exception as e:
            print(f"❌ 拨号失败: {e}")
            return {"success": False, "message": f"拨号失败: {str(e)}"}

    async def send_emergency_sms(self, plant_name):
        """向所有紧急联系人发送紧急求助短信"""
        if not self.emergency_contacts:
            print("⚠️ 未配置紧急联系人")
            return {"success": False, "message": "未配置紧急联系人"}

        sms_content = self.generate_location_share_text(plant_name)
        success_count = 0

        for contact in self.emergency_contacts:
            try:
                phone = contact["phone"]
                sms_url = f"sms:{phone}?body={sms_content}"
                await self.page.launch_url(sms_url)
                success_count += 1
                print(f"✅ 向{contact['name']}({phone})发送求助短信")
            except Exception as e:
                print(f"❌ 向{contact['name']}发送短信失败: {e}")

        return {
            "success": success_count > 0,
            "success_count": success_count,
            "total": len(self.emergency_contacts)
        }

    async def navigate_to_nearest_hospital(self):
        """调起地图导航至最近的医院"""
        if not self.current_position:
            await self.page.launch_url("https://maps.apple.com/?q=附近可救治毒菌中毒的医院")
            return {"success": True}

        lat = self.current_position["latitude"]
        lon = self.current_position["longitude"]
        map_url = f"https://maps.apple.com/?saddr={lat},{lon}&daddr=医院&dirflg=d"
        try:
            await self.page.launch_url(map_url)
            return {"success": True}
        except Exception as e:
            print(f"❌ 导航调起失败: {e}")
            return {"success": False, "message": f"导航调起失败: {str(e)}"}

    # ========== 应急响应核心功能：急救视频播放 ==========
    def create_first_aid_video_player(self):
        """创建急救视频播放器组件"""
        video_src = self.first_aid_video_url
        if os.path.exists(self.local_first_aid_video_path):
            video_src = self.local_first_aid_video_path

        self.first_aid_video = Video(
            src=video_src,
            width=600,
            height=400,
            autoplay=True,
            loop=False,
            show_controls=True,
            fit=ft.ImageFit.CONTAIN,
            filter_quality=ft.FilterQuality.HIGH
        )

        self.fullscreen_btn = IconButton(
            icon=ft.Icons.FULLSCREEN,
            on_click=lambda _: self.first_aid_video.enter_fullscreen(),
            icon_color=Colors.WHITE,
            bgcolor=Colors.BLACK54
        )

        return Container(
            content=Stack([
                self.first_aid_video,
                Container(
                    content=self.fullscreen_btn,
                    alignment=alignment.top_right,
                    padding=10
                )
            ]),
            border_radius=border_radius.all(8),
            margin=ft.margin.symmetric(vertical=10)
        )

    async def play_first_aid_video(self):
        """播放急救视频"""
        if hasattr(self, 'first_aid_video'):
            try:
                await self.first_aid_video.play()
                await self.first_aid_video.enter_fullscreen()
                print("🎥 急救视频开始播放")
            except Exception as e:
                print(f"❌ 视频播放失败: {e}")

    # ========== 应急响应配套功能：紧急联系人界面 ==========
    def create_emergency_contacts_page(self):
        """创建紧急联系人管理页面"""
        self.contacts_list = ListView(expand=True, spacing=5)
        self.update_contacts_list()

        self.contact_name_input = TextField(label="联系人姓名", width=300, border_radius=8)
        self.contact_phone_input = TextField(label="联系电话", width=300, border_radius=8,
                                              keyboard_type=ft.KeyboardType.PHONE)

        def add_new_contact(e):
            name = self.contact_name_input.value.strip()
            phone = self.contact_phone_input.value.strip()
            if not name or not phone:
                self.page.snack_bar = SnackBar(Text("请填写完整的姓名和电话"))
                self.page.snack_bar.open = True
                self.page.update()
                return

            self.emergency_contacts.append({"name": name, "phone": phone})
            self.page.run_task(self.save_emergency_contacts)
            self.update_contacts_list()
            self.contact_name_input.value = ""
            self.contact_phone_input.value = ""
            self.page.update()

        return Container(
            content=Column([
                Container(height=20),
                Row([
                    IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: self.navigate_to_page(self.settings_page, "设置")),
                    Text("紧急联系人管理", size=24, weight=ft.FontWeight.BOLD, expand=True, text_align="center"),
                    Container(width=40)
                ]),
                Divider(height=20),
                Card(
                    content=Container(
                        content=Column([
                            Text("新增紧急联系人", size=16, weight=ft.FontWeight.BOLD),
                            self.contact_name_input,
                            self.contact_phone_input,
                            ElevatedButton("添加联系人", on_click=add_new_contact,
                                         style=ft.ButtonStyle(bgcolor=Colors.GREEN_600, color=Colors.WHITE))
                        ], spacing=10),
                        padding=20
                    ),
                    margin=ft.margin.symmetric(horizontal=10)
                ),
                Container(height=10),
                Text("已保存联系人", size=16, weight=ft.FontWeight.BOLD, margin=ft.margin.only(left=15)),
                Container(content=self.contacts_list, expand=True, margin=ft.margin.symmetric(horizontal=10)),
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def update_contacts_list(self):
        """更新联系人列表"""
        self.contacts_list.controls.clear()
        if not self.emergency_contacts:
            self.contacts_list.controls.append(Text("暂无紧急联系人，请添加", color=Colors.GREY_500, text_align="center"))
            return

        for idx, contact in enumerate(self.emergency_contacts):
            def delete_contact(e, contact_idx=idx):
                del self.emergency_contacts[contact_idx]
                self.page.run_task(self.save_emergency_contacts)
                self.update_contacts_list()
                self.page.update()

            self.contacts_list.controls.append(
                Card(
                    content=Container(
                        content=Row([
                            Column([
                                Text(contact["name"], weight=ft.FontWeight.BOLD),
                                Text(contact["phone"], size=14, color=Colors.GREY_600)
                            ], expand=True),
                            IconButton(icon=ft.Icons.DELETE, icon_color=Colors.RED_500, on_click=delete_contact)
                        ]),
                        padding=15
                    )
                )
            )

    def create_first_aid_guide_page(self):
        """创建急救指南页面"""
        video_player = self.create_first_aid_video_player()

        return Container(
            content=Column([
                Container(height=20),
                Row([
                    IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: self.navigate_to_page(self.settings_page, "设置")),
                    Text("毒菌中毒急救指南", size=24, weight=ft.FontWeight.BOLD, expand=True, text_align="center"),
                    Container(width=40)
                ]),
                Divider(height=20),
                Text("标准化急救指引视频", size=18, weight=ft.FontWeight.BOLD, margin=ft.margin.only(left=15)),
                video_player,
                Container(height=20),
                Card(
                    content=Container(
                        content=Column([
                            Text("急救核心要点", size=18, weight=ft.FontWeight.BOLD),
                            Divider(height=10),
                            Text("1. 立即拨打120急救电话，告知医生疑似误食毒菌", size=16),
                            Text("2. 携带剩余毒菌样本前往医院，便于医生快速诊断", size=16),
                            Text("3. 切勿自行催吐，尤其出现昏迷、抽搐症状时", size=16),
                            Text("4. 切勿饮酒、服用偏方或止泻药，会加重病情", size=16),
                            Text("5. 保留呕吐物样本，供医院检测使用", size=16),
                        ], spacing=10),
                        padding=20
                    ),
                    margin=ft.margin.symmetric(horizontal=10)
                ),
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    # ========== 应急响应核心：全流程触发与弹窗 ==========
    def create_emergency_alert_dialog(self, plant_name, is_toxic=True):
        """创建剧毒菌应急警示弹窗"""
        def close_dialog(e):
            self.emergency_alert_dialog.open = False
            self.page.update()

        async def confirm_ingestion(e):
            close_dialog(None)
            self.is_emergency_mode = True

            location_result = await self.get_current_location()

            tasks = [
                self.make_emergency_call(),
                self.navigate_to_nearest_hospital(),
                self.send_emergency_sms(plant_name)
            ]
            await asyncio.gather(*tasks)

            await self.play_first_aid_video()
            self.show_emergency_result_page(plant_name, location_result)

        self.emergency_alert_dialog = AlertDialog(
            bgcolor=Colors.RED_50,
            title=Row([
                Icon(ft.Icons.DANGEROUS, color=Colors.RED_600, size=28),
                Text("剧毒野生菌警告！", color=Colors.RED_600, weight=ft.FontWeight.BOLD, size=22)
            ]),
            content=Column([
                Text(f"识别结果：{plant_name}", size=18, weight=ft.FontWeight.BOLD),
                Text("该菌类含有剧毒，误食可危及生命！", size=16, color=Colors.RED_700),
                Container(height=10),
                Text("请问您是否已经误食/接触该菌类？", size=16, weight=ft.FontWeight.BOLD),
                Text("确认后将立即触发应急救援流程", size=14, color=Colors.GREY_700)
            ], tight=True),
            actions=[
                TextButton("未误食，返回", on_click=close_dialog, style=ft.ButtonStyle(color=Colors.GREY_600)),
                ElevatedButton("已误食，紧急求助", on_click=lambda e: self.page.run_task(confirm_ingestion, e),
                              style=ft.ButtonStyle(bgcolor=Colors.RED_600, color=Colors.WHITE, padding=15))
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            modal=True
        )

        return self.emergency_alert_dialog

    def show_emergency_result_page(self, plant_name, location_result):
        """显示应急响应结果页面"""
        video_player = self.create_first_aid_video_player()

        status_content = Column([
            Text("🚨 应急响应已触发", size=20, weight=ft.FontWeight.BOLD, color=Colors.RED_600),
            Divider(height=15),
            Text(f"疑似中毒菌类：{plant_name}", size=16),
            Text(f"位置获取状态：{'成功' if location_result['success'] else '失败'}", size=16),
            Container(height=10),
            Text("已为您执行以下操作：", size=16, weight=ft.FontWeight.BOLD),
            Text("✅ 已调起120急救拨号界面", size=14),
            Text("✅ 已打开地图导航至最近医院", size=14),
            Text(f"✅ 已向{len(self.emergency_contacts)}位紧急联系人发送求助信息", size=14),
            Container(height=10),
            Text("急救指引视频", size=16, weight=ft.FontWeight.BOLD),
            video_player,
            Container(height=10),
            Text("⚠️ 重要提示：请立即携带毒菌样本前往医院就医，切勿自行催吐、饮酒或服用偏方！",
                 size=14, color=Colors.RED_600),
            Container(height=20),
            ElevatedButton("返回首页", on_click=lambda _: self.on_custom_nav_click(0),
                          style=ft.ButtonStyle(bgcolor=Colors.GREEN_600, color=Colors.WHITE))
        ])

        self.page_container.content = Container(
            content=Column([status_content], scroll=ScrollMode.AUTO),
            padding=20,
            expand=True
        )
        self.page.update()

    # ========== UI 组件初始化 ==========
    def init_components(self):
        """初始化所有组件"""
        self.badge_text = Text(
            str(self.unread_count) if self.unread_count <= 99 else "99+",
            size=10,
            color=Colors.WHITE,
            weight=ft.FontWeight.BOLD
        )
        self.notification_icon = IconButton(
            icon=ft.Icons.NOTIFICATIONS,
            on_click=lambda _: self.navigate_to_notification_page(),
            icon_size=24
        )
        self.notification_badge = Stack(
            controls=[
                self.notification_icon,
                Container(
                    content=self.badge_text,
                    bgcolor=Colors.RED,
                    width=18,
                    height=18,
                    border_radius=border_radius.all(9),
                    alignment=alignment.center,
                    visible=self.unread_count > 0
                )
            ]
        )

        self.top_bar = navigation_bars.create_top_bar(
            parent_app=self,
            title="滇菌智护",
            can_go_back=False,
            notification_badge=self.notification_badge
        )
        self.qq_nav = navigation_bars.QQStyleBottomNav(parent_app=self)

        self.search_input = ft.TextField(
            hint_text="搜索菌类名称或特征...",
            expand=True,
            text_size=14,
            content_padding=10,
            border_radius=20,
            filled=True,
            fill_color=Colors.WHITE,
            border_color=Colors.GREEN_400,
            max_lines=1,
            on_submit=lambda e: self.handle_search_click(e),
        )

        self.search_bar = Container(
            content=Row([
                self.search_input,
                IconButton(
                    icon=ft.Icons.SEARCH,
                    on_click=self.handle_search_click,
                    icon_size=24,
                    style=ft.ButtonStyle(
                        bgcolor=Colors.GREEN_500,
                        color=Colors.WHITE
                    )
                )
            ], spacing=10),
            padding=ft.padding.symmetric(horizontal=15, vertical=10),
            bgcolor=Colors.GREEN_50,
            visible=False,
            margin=0
        )

        self.image_picker = ft.FilePicker(on_result=self.on_image_selected)
        self.page.overlay.append(self.image_picker)
        self.photo_preview = ft.Image(
            visible=False,
            width=400,
            height=300,
            fit=ft.ImageFit.COVER,
            border_radius=border_radius.all(8)
        )

        self.identification_result = ft.Column(visible=False)

        self.avatar_picker = ft.FilePicker(on_result=self.on_avatar_selected)
        self.page.overlay.append(self.avatar_picker)

        self.page_container = Container(
            content=self.create_home_page(),
            expand=True
        )

        self.home_page = self.create_home_page()
        self.search_page = self.create_search_page()
        self.plant_page = self.create_plant_library_page()
        self.collection_page = self.create_collection_page()
        self.profile_page = self.create_profile_page()
        self.settings_page = self.create_settings_page()
        self.notification_page = self.create_notification_page()

    # ========== 页面构建函数 ==========
    def create_home_page(self):
        """创建首页内容"""
        featured_plants = [self.create_plant_card(plant) for plant in self.all_plants[:3]]

        return Container(
            content=Column([
                Container(height=20),
                Text("欢迎使用滇菌智护", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Divider(height=20),
                Text("滇菌智护，识得菌中味", size=16, color=Colors.GREY_700, text_align="center"),
                Container(height=20),

                Card(
                    content=Container(
                        content=Column([
                            Text("菌类图片识别", size=20, weight=ft.FontWeight.BOLD, text_align="center"),
                            Container(height=10),
                            Text("上传菌类图片，AI智能识别种类", size=14, color=Colors.GREY_600, text_align="center"),
                            Container(height=15),
                            ElevatedButton(
                                "📸 上传图片识别菌类",
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=self.open_image_picker,
                                style=ft.ButtonStyle(
                                    bgcolor=Colors.GREEN_600,
                                    color=Colors.WHITE,
                                    padding=20
                                ),
                                width=250
                            ),
                            Container(height=10),
                            Text("支持 JPG、PNG 格式图片", size=12, color=Colors.GREY_500, text_align="center")
                        ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        padding=20,
                        alignment=ft.alignment.center,
                    ),
                    elevation=3,
                    margin=ft.margin.symmetric(vertical=10)
                ),
                Container(height=20),

                Container(
                    content=self.identification_result,
                    padding=10
                ),

                Text("精选菌类", size=20, weight=ft.FontWeight.BOLD),
                Container(height=10),
                ListView(
                    controls=featured_plants,
                    expand=True,
                    spacing=10
                ),
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_search_page(self):
        """创建搜索页面内容"""
        self.search_results = ft.Column(
            controls=[
                Container(
                    content=Column([
                        Icon(ft.Icons.SEARCH, size=48, color=Colors.GREY_400),
                        Text("请输入菌类名称或特征进行搜索",
                             size=16, color=Colors.GREY_600, text_align="center")
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50
                )
            ],
            expand=True,
            spacing=10,
            scroll=ScrollMode.AUTO
        )

        return Container(
            content=Column([
                Container(height=10),
                Text("搜索菌类", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Container(height=10),
                self.search_results
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_plant_library_page(self):
        """创建菌类库页面内容（原植物库）"""
        all_plant_cards = [self.create_plant_card(plant) for plant in self.all_plants]

        return Container(
            content=Column([
                Container(height=20),
                Text("菌类库", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Container(height=20),
                ListView(
                    controls=all_plant_cards,
                    expand=True,
                    spacing=10
                )
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_collection_page(self):
        """创建收藏页面内容"""
        self.collection_list = ListView(
            controls=[Text("您还没有收藏任何菌类，浏览后可收藏喜欢的菌类")],
            expand=True,
            spacing=10
        )

        self.update_collection_list()

        return Container(
            content=Column([
                Container(height=20),
                Text("我的收藏", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Divider(height=20),
                self.collection_list,
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_profile_page(self):
        """创建个人资料页面内容"""
        self.username_field = TextField(
            value=self.user_info["username"],
            label="用户名",
            visible=False,
            width=300
        )
        self.bio_field = TextField(
            value=self.user_info["bio"],
            label="个人简介",
            multiline=True,
            min_lines=3,
            max_lines=5,
            visible=False,
            width=300
        )
        self.avatar_image = Image(
            src=self.user_info["avatar_url"],
            width=100,
            height=100,
            fit=ft.ImageFit.COVER,
            border_radius=ft.border_radius.all(50)
        )
        self.change_avatar_btn = ElevatedButton(
            text="更换头像",
            icon=ft.Icons.CAMERA_ALT,
            on_click=lambda _: self.avatar_picker.pick_files(
                allow_multiple=False,
                file_type=ft.FilePickerFileType.IMAGE
            ),
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=Colors.GREY_200,
                color=Colors.BLACK
            )
        )
        self.username_text = Text(self.user_info["username"], size=18, weight=ft.FontWeight.BOLD)
        self.bio_text = Text(self.user_info["bio"], size=14, color=Colors.GREY_700)

        self.browsing_history_list = ListView(
            controls=[Text("暂无浏览记录")],
            expand=False,
            spacing=5
        )
        self.collection_history_list = ListView(
            controls=[Text("暂无收藏记录")],
            expand=False,
            spacing=5
        )

        self.browsed_count_text = Text(f"{len(self.browsing_history)}", size=20, weight=ft.FontWeight.BOLD, color=Colors.GREEN_600)
        self.collected_count_text = Text(f"{len(self.collected_plants)}", size=20, weight=ft.FontWeight.BOLD, color=Colors.GREEN_600)
        self.searched_count_text = Text(f"{self.user_info['searched']}", size=20, weight=ft.FontWeight.BOLD, color=Colors.GREEN_600)

        self.manage_history_btn = ElevatedButton(
            text="管理浏览历史",
            icon=ft.Icons.DELETE,
            on_click=self.manage_browsing_history,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=Colors.RED_500,
                color=Colors.WHITE
            )
        )

        self.manage_collection_btn = ElevatedButton(
            text="管理收藏",
            icon=ft.Icons.DELETE,
            on_click=self.manage_collections,
            visible=False,
            style=ft.ButtonStyle(
                bgcolor=Colors.RED_500,
                color=Colors.WHITE
            )
        )

        self.update_profile_history_lists()

        def toggle_edit(e):
            self.editing_profile = not self.editing_profile
            self.username_text.visible = not self.editing_profile
            self.username_field.visible = self.editing_profile
            self.bio_text.visible = not self.editing_profile
            self.bio_field.visible = self.editing_profile
            self.change_avatar_btn.visible = self.editing_profile
            self.manage_history_btn.visible = self.editing_profile
            self.manage_collection_btn.visible = self.editing_profile

            self.update_profile_history_lists()

            if self.editing_profile:
                edit_button.text = "保存"
                edit_button.on_click = save_profile
                self.username_field.value = self.user_info["username"]
                self.bio_field.value = self.user_info["bio"]
            else:
                edit_button.text = "编辑资料"
                edit_button.on_click = toggle_edit
            self.page.update()

        def save_profile(e):
            self.user_info["username"] = self.username_field.value
            self.user_info["bio"] = self.bio_field.value
            self.username_text.value = self.user_info["username"]
            self.bio_text.value = self.user_info["bio"]
            toggle_edit(None)
            snack = SnackBar(Text("个人资料已更新"))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

        edit_button = ElevatedButton(
            text="编辑资料",
            on_click=toggle_edit,
            icon=ft.Icons.EDIT,
            style=ft.ButtonStyle(
                bgcolor=Colors.GREEN_600,
                color=Colors.WHITE
            )
        )

        return Container(
            content=Column([
                Container(height=20),
                Text("个人资料", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Divider(height=20),
                Card(
                    content=Container(
                        content=Column([
                            Container(height=20),
                            Row(
                                controls=[
                                    Container(
                                        content=Column([
                                            self.avatar_image,
                                            self.change_avatar_btn
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=10
                                        ),
                                        border_radius=ft.border_radius.all(50),
                                        bgcolor=Colors.GREY_200,
                                        padding=2
                                    ),
                                    Column([
                                        self.username_text,
                                        self.username_field,
                                        Text(f"注册时间：{self.user_info['join_date']}", size=14, color=Colors.GREY_600),
                                        Text(f"收藏菌类数量：{len(self.collected_plants)}", size=14, color=Colors.GREY_600)
                                    ],
                                    spacing=5,
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    expand=True
                                    )
                                ],
                                spacing=20,
                                alignment=ft.MainAxisAlignment.CENTER
                            ),
                            Container(height=15),
                            Divider(height=15),
                            Text("个人简介", size=16, weight=ft.FontWeight.BOLD),
                            self.bio_text,
                            self.bio_field,
                            Container(height=15),
                            Divider(height=15),
                            Text("使用统计", size=16, weight=ft.FontWeight.BOLD),
                            Row([
                                Card(
                                    content=Container(
                                        content=Column([
                                            Container(height=10),
                                            Text("浏览菌类", size=14),
                                            self.browsed_count_text,
                                            Container(height=10)
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=5
                                        ),
                                        border_radius=border_radius.all(8)
                                    ),
                                    elevation=2
                                ),
                                Card(
                                    content=Container(
                                        content=Column([
                                            Container(height=10),
                                            Text("收藏菌类", size=14),
                                            self.collected_count_text,
                                            Container(height=10)
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=5
                                        ),
                                        border_radius=border_radius.all(8)
                                    ),
                                    elevation=2
                                ),
                                Card(
                                    content=Container(
                                        content=Column([
                                            Container(height=10),
                                            Text("搜索次数", size=14),
                                            self.searched_count_text,
                                            Container(height=10)
                                        ],
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=5
                                        ),
                                        border_radius=border_radius.all(8)
                                    ),
                                    elevation=2
                                )
                            ],
                            spacing=15,
                            expand=True
                            ),
                            Container(height=15),
                            Divider(height=15),
                            Row([
                                Text("最近浏览", size=16, weight=ft.FontWeight.BOLD, expand=True),
                                self.manage_history_btn
                            ]),
                            Container(
                                content=self.browsing_history_list,
                                height=200
                            ),
                            Container(height=15),
                            Divider(height=15),
                            Row([
                                Text("我的收藏", size=16, weight=ft.FontWeight.BOLD, expand=True),
                                self.manage_collection_btn
                            ]),
                            Container(
                                content=self.collection_history_list,
                                height=200
                            ),
                            Container(height=15),
                            Container(
                                content=edit_button,
                                alignment=ft.alignment.center,
                            ),
                            Container(height=20)
                        ],
                        spacing=0
                        ),
                        border_radius=border_radius.all(10)
                    ),
                    elevation=3,
                    margin=ft.margin.all(10)
                ),
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_settings_page(self):
        """创建设置页面"""
        # 地理位置获取按钮
        self.location_fetch_btn = ElevatedButton(
            text="📍 手动获取当前地理位置",
            icon=ft.Icons.LOCATION_ON,
            on_click=lambda e: self.page.run_task(self.manual_fetch_location),
            style=ft.ButtonStyle(
                bgcolor=Colors.BLUE_600,
                color=Colors.WHITE,
                padding=15
            ),
            width=300
        )

        # 位置状态显示文本
        self.location_status_text = Text(
            "当前位置：未获取",
            size=14,
            color=Colors.GREY_700
        )

        # 应急设置区域
        emergency_settings_card = Card(
            content=Container(
                content=Column([
                    Text("🚨 应急响应设置", size=18, weight=ft.FontWeight.BOLD),
                    Divider(height=10),
                    Column([
                        Text("地理位置管理", size=16),
                        self.location_fetch_btn,
                        self.location_status_text,
                        Container(height=10),
                    ], spacing=8),
                    ElevatedButton(
                        text="📞 管理紧急联系人",
                        icon=ft.Icons.CONTACT_EMERGENCY,
                        on_click=lambda _: self.navigate_to_page(self.create_emergency_contacts_page(), "紧急联系人管理"),
                        style=ft.ButtonStyle(bgcolor=Colors.ORANGE_500, color=Colors.WHITE)
                    ),
                    ElevatedButton(
                        text="📖 查看毒菌中毒急救指南",
                        icon=ft.Icons.MEDICAL_INFORMATION,
                        on_click=lambda _: self.navigate_to_page(self.create_first_aid_guide_page(), "毒菌中毒急救指南"),
                        style=ft.ButtonStyle(bgcolor=Colors.GREEN_500, color=Colors.WHITE)
                    )
                ], spacing=15),
                padding=20
            ),
            margin=ft.margin.symmetric(vertical=10)
        )

        # ========== 网络设置区域 ==========
        self.backend_url_input = TextField(
            label="后端服务地址",
            value=self.backend_url,
            width=300,
            hint_text="例如 http://localhost:8000 或 http://10.0.2.2:8000"
        )
        self.connection_status = Text("未测试", size=12, color=Colors.GREY_600)

        async def test_connection(e):
            """测试后端连接"""
            test_url = self.backend_url_input.value.strip()
            if not test_url:
                return
            self.connection_status.value = "⏳ 测试中..."
            self.connection_status.color = Colors.BLUE
            self.page.update()

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{test_url}/", timeout=3) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("model_status") == "loaded":
                                self.connection_status.value = "✅ 连接成功，模型已加载"
                                self.connection_status.color = Colors.GREEN
                                await self.save_backend_url(test_url)
                            else:
                                self.connection_status.value = "⚠️ 连接成功但模型未加载"
                                self.connection_status.color = Colors.ORANGE
                        else:
                            self.connection_status.value = f"❌ HTTP {resp.status}"
                            self.connection_status.color = Colors.RED
            except Exception as e:
                self.connection_status.value = f"❌ 连接失败: {str(e)[:50]}"
                self.connection_status.color = Colors.RED
            self.page.update()

        def auto_detect(e):
            """自动检测可用后端地址"""
            self.page.run_task(self.auto_detect_on_startup)

        network_card = Card(
            content=Container(
                content=Column([
                    Text("🌐 后端网络设置", size=18, weight=ft.FontWeight.BOLD),
                    Divider(height=10),
                    Text("当识别失败提示「网络请求异常」时，请检查后端服务是否运行，并尝试修改地址："),
                    self.backend_url_input,
                    Row([
                        ElevatedButton("测试连接", on_click=test_connection, icon=ft.Icons.WIFI_FIND),
                        ElevatedButton("自动检测", on_click=auto_detect, icon=ft.Icons.SEARCH),
                        ElevatedButton("启动本地后端", on_click=lambda e: self.page.run_task(self.start_local_backend), icon=ft.Icons.PLAY_ARROW),
                    ], spacing=10),
                    self.connection_status,
                    Container(height=10),
                    Text("提示：在 Android 模拟器中请使用 http://10.0.2.2:8000", size=12, color=Colors.GREY_500),
                    Text("在真机调试时请使用电脑的局域网 IP（如 192.168.x.x）", size=12, color=Colors.GREY_500),
                ], spacing=15),
                padding=20
            ),
            margin=ft.margin.symmetric(vertical=10)
        )

        # 通用设置区域
        general_settings_card = Card(
            content=Container(
                content=Column([
                    Text("⚙️ 通用设置", size=18, weight=ft.FontWeight.BOLD),
                    Divider(height=10),
                    ListTile(
                        leading=Icon(ft.Icons.NOTIFICATIONS),
                        title=Text("通知权限"),
                        subtitle=Text("开启/关闭应用通知"),
                        trailing=Switch(
                            value=True,
                            on_change=lambda e: self.toggle_notifications(e)
                        )
                    ),
                    ListTile(
                        leading=Icon(ft.Icons.DARK_MODE),
                        title=Text("深色模式"),
                        subtitle=Text("切换应用显示主题"),
                        trailing=Switch(
                            value=False,
                            on_change=lambda e: self.toggle_dark_mode(e)
                        )
                    )
                ], spacing=8),
                padding=20
            ),
            margin=ft.margin.symmetric(vertical=10)
        )

        return Container(
            content=Column([
                Container(height=20),
                Row([
                    IconButton(icon=ft.Icons.ARROW_BACK, on_click=self.go_back),
                    Text("设置中心", size=24, weight=ft.FontWeight.BOLD, expand=True, text_align="center"),
                    Container(width=40)
                ]),
                Divider(height=20),
                emergency_settings_card,
                network_card,
                general_settings_card,
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    async def manual_fetch_location(self):
        """手动触发获取地理位置（带用户反馈）"""
        self.location_fetch_btn.disabled = True
        self.location_status_text.value = "当前位置：正在获取..."
        self.page.update()

        try:
            result = await self.get_current_location()

            if result["success"]:
                lat = self.current_position["latitude"]
                lon = self.current_position["longitude"]
                self.location_status_text.value = f"当前位置：纬度 {lat:.6f}，经度 {lon:.6f}"
                self.page.snack_bar = SnackBar(Text("✅ 地理位置获取成功！"))
            else:
                self.location_status_text.value = f"当前位置：获取失败 - {result['message']}"
                self.page.snack_bar = SnackBar(Text(f"❌ {result['message']}"), bgcolor=Colors.RED_300)

            self.page.snack_bar.open = True
        finally:
            self.location_fetch_btn.disabled = False
            self.page.update()

    def toggle_dark_mode(self, e):
        self.page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
        self.page.update()

    def toggle_notifications(self, e):
        self.page.snack_bar = SnackBar(Text(f"通知权限已{'开启' if e.control.value else '关闭'}"))
        self.page.snack_bar.open = True
        self.page.update()

    async def show_launch_location_dialog(self):
        """应用启动时弹出位置获取确认弹窗"""
        location_dialog = AlertDialog(
            title=Row([
                Icon(ft.Icons.LOCATION_PIN, color=Colors.BLUE_600),
                Text("地理位置授权请求", weight=ft.FontWeight.BOLD)
            ]),
            content=Column([
                Text("为了在紧急情况下快速定位并发起救援，"),
                Text("需要获取您的地理位置权限。"),
                Text("您可以选择「同意」或「拒绝」，也可在设置页手动开启。"),
            ], spacing=5),
            actions=[
                TextButton("拒绝", on_click=lambda e: self.close_dialog(e, location_dialog)),
                TextButton("同意", on_click=lambda e: self.confirm_location_permission(e, location_dialog)),
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            modal=True
        )

        self.page.dialog = location_dialog
        location_dialog.open = True
        self.page.update()

    def close_dialog(self, e, dialog):
        dialog.open = False
        self.page.update()
        self.page.snack_bar = SnackBar(
            Text("您已拒绝位置授权，可在设置页手动获取位置"),
            bgcolor=Colors.GREY_500
        )
        self.page.snack_bar.open = True
        self.page.update()

    async def confirm_location_permission(self, e, dialog):
        dialog.open = False
        self.page.update()

        result = await self.get_current_location()
        if result["success"]:
            self.page.snack_bar = SnackBar(Text("✅ 地理位置获取成功！紧急时可自动定位"))
        else:
            self.page.snack_bar = SnackBar(
                Text(f"❌ 位置获取失败：{result['message']}"),
                bgcolor=Colors.RED_500
            )
        self.page.snack_bar.open = True
        self.page.update()

    def create_notification_page(self):
        """创建通知页面内容"""
        self.notification_list = ListView(expand=True, spacing=10)
        self.update_notification_list()

        return Container(
            content=Column([
                Container(height=20),
                Text("通知中心", size=24, weight=ft.FontWeight.BOLD, text_align="center"),
                Divider(height=20),
                self.notification_list,
                Container(height=20)
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    def create_notification_detail_page(self, notification):
        """创建通知详情页面"""
        if not notification["is_read"]:
            notification["is_read"] = True
            self.unread_count -= 1
            self.unread_count = max(0, self.unread_count)
            self.notification_badge.controls[1].visible = self.unread_count > 0
            self.badge_text.value = str(self.unread_count) if self.unread_count <= 99 else "99+"
            self.update_notification_list()

        return Container(
            content=Column([
                Container(height=20),
                Row([
                    IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda _: self.navigate_to_notification_page()
                    ),
                    Text("通知详情", size=20, weight=ft.FontWeight.BOLD, expand=True, text_align="center"),
                    Container(width=40)
                ]),
                Container(height=20),
                Card(
                    content=Container(
                        content=Column([
                            Container(height=20),
                            Text(notification["title"], size=20, weight=ft.FontWeight.BOLD),
                            Container(height=10),
                            Text(notification["time"].strftime("%Y-%m-%d %H:%M"), size=12, color=Colors.GREY_500),
                            Container(height=20),
                            Divider(height=1),
                            Container(height=20),
                            Text(notification["content"], size=16, selectable=True),
                            Container(height=20)
                        ]),
                        padding=20
                    ),
                    elevation=3,
                    margin=ft.margin.all(10)
                )
            ], scroll=ScrollMode.AUTO),
            expand=True
        )

    # ========== 菌类卡片和详情页面 ==========
    def create_plant_card(self, plant):
        """创建菌类卡片，增加毒性标识"""
        is_collected = plant["name"] in self.collected_plants
        is_toxic = plant.get("is_toxic", False)

        # 毒性标识
        toxic_badge = Container(
            content=Text("☠️", size=14, color=Colors.RED),
            right=10,
            top=10
        ) if is_toxic else Container()

        return Card(
            content=Container(
                content=Stack([
                    Column([
                        Image(
                            src=plant["image_url"],
                            width=300,
                            height=200,
                            fit=ft.ImageFit.COVER,
                            border_radius=border_radius.all(8)
                        ),
                        Container(height=10),
                        Text(plant["name"], size=18, weight=ft.FontWeight.BOLD),
                        Text(plant["desc"], size=14, color=Colors.GREY_600),
                        Container(height=10),
                        Row([
                            ElevatedButton(
                                "查看详情",
                                on_click=lambda e, p=plant: self.navigate_to_plant_detail(p),
                                style=ft.ButtonStyle(
                                    bgcolor=Colors.GREEN_500,
                                    color=Colors.WHITE
                                )
                            ),
                            IconButton(
                                icon=ft.Icons.FAVORITE if is_collected else ft.Icons.FAVORITE_BORDER,
                                on_click=lambda e, p=plant: self.toggle_collection(p),
                                icon_color=Colors.RED_500 if is_collected else Colors.GREY_500,
                                tooltip="收藏" if not is_collected else "取消收藏"
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ], spacing=0),
                    toxic_badge
                ]),
                padding=15
            ),
            elevation=3,
            margin=ft.margin.symmetric(vertical=5)
        )

    def create_plant_detail_page(self, plant):
        """创建菌类详情页面，显示毒性警告"""
        self.add_to_browsing_history(plant)

        is_collected = plant["name"] in self.collected_plants
        is_toxic = plant.get("is_toxic", False)

        self.detail_collect_button = ElevatedButton(
            "取消收藏" if is_collected else "收藏",
            icon=ft.Icons.FAVORITE if is_collected else ft.Icons.FAVORITE_BORDER,
            on_click=lambda e, p=plant: self.toggle_collection_and_refresh(p),
            style=ft.ButtonStyle(
                bgcolor=Colors.RED_500 if is_collected else Colors.GREEN_500,
                color=Colors.WHITE
            )
        )

        # 毒性警告横幅
        toxic_warning = Container(
            content=Text("⚠️ 剧毒警告！请勿接触或食用！",
                         color=Colors.RED, weight=ft.FontWeight.BOLD),
            bgcolor=Colors.RED_100,
            padding=10,
            border_radius=8,
            visible=is_toxic
        )

        detail_content = Column([
            Image(
                src=plant["image_url"],
                width=350,
                height=250,
                fit=ft.ImageFit.COVER,
                border_radius=border_radius.all(8)
            ),
            Container(height=20),
            Text(plant["name"], size=24, weight=ft.FontWeight.BOLD),
            Container(height=10),
            toxic_warning,
            Container(height=5),
            Text(f"学名: {plant['sci_name']}", size=16, italic=True, color=Colors.GREY_600),
            Text(f"科属: {plant['family']}", size=16),
            Container(height=10),
            Text(f"描述: {plant['desc']}", size=16),
            Container(height=10),
            Text(f"分布: {plant['distribution']}", size=16),
            Container(height=10),
            Text(f"形态特征: {plant['features']}", size=16),
            Container(height=10),
            Text(f"生长习性: {plant['habit']}", size=16),
            Container(height=10),
            Text(f"文化意义: {plant['culture']}", size=16),
            Container(height=20),
            Row([
                self.detail_collect_button,
                ElevatedButton(
                    "分享菌类",
                    icon=ft.Icons.SHARE,
                    style=ft.ButtonStyle(
                        bgcolor=Colors.BLUE_500,
                        color=Colors.WHITE
                    )
                )
            ], alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            Container(height=20)
        ], scroll=ScrollMode.AUTO)

        return detail_content

    def toggle_collection_and_refresh(self, plant):
        """切换收藏状态并刷新详情页按钮"""
        self.toggle_collection(plant)
        self.refresh_detail_page_collection_button(plant)

    def refresh_detail_page_collection_button(self, plant):
        """刷新详情页收藏按钮状态"""
        is_collected = plant["name"] in self.collected_plants
        self.detail_collect_button.text = "取消收藏" if is_collected else "收藏"
        self.detail_collect_button.icon = ft.Icons.FAVORITE if is_collected else ft.Icons.FAVORITE_BORDER
        self.detail_collect_button.style.bgcolor = Colors.RED_500 if is_collected else Colors.GREEN_500
        self.page.update()

    def assemble_page(self):
        """组装页面布局"""
        self.page.window.width = 375
        self.page.window.height = 746
        self.page.bgcolor = Colors.LIGHT_GREEN_50

        self.page.add(
            Column([
                self.top_bar,
                self.search_bar,
                Container(
                    content=self.page_container,
                    expand=True
                ),
                self.qq_nav.build()
            ], spacing=0, expand=True)
        )

        self.page_container.content = self.create_home_page()
        self.page.update()

    def on_custom_nav_click(self, index):
        """处理底部导航栏点击事件"""
        if index != self.current_page_index:
            self.page_history.append(self.current_page_index)

        self.current_page_index = index
        self.qq_nav.update_selection(index)

        if index == 0:
            self.page_container.content = self.create_home_page()
            self.search_bar.visible = False
        elif index == 1:
            self.page_container.content = self.create_search_page()
            self.search_bar.visible = True
            if hasattr(self, 'search_input'):
                self.search_input.focus()
        elif index == 2:
            self.page_container.content = self.create_plant_library_page()
            self.search_bar.visible = False
        elif index == 3:
            self.page_container.content = self.create_collection_page()
            self.search_bar.visible = False
        elif index == 4:
            self.page_container.content = self.create_profile_page()
            self.search_bar.visible = False

        if hasattr(self, 'top_bar'):
            back_button = self.top_bar.content.controls[0].content
            back_button.disabled = len(self.page_history) == 0

        self.page.update()

    def handle_search_click(self, e):
        """处理搜索按钮点击"""
        query = self.search_input.value.strip()
        if query:
            print(f"搜索查询: {query}")
            self.perform_search(query)
        else:
            self.search_results.controls = [
                Container(
                    content=Column([
                        Icon(ft.Icons.SEARCH, size=48, color=Colors.GREY_400),
                        Text("请输入菌类名称或特征进行搜索",
                             size=16, color=Colors.GREY_600, text_align="center")
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    alignment=ft.alignment.center,
                    padding=50
                )
            ]
            self.page.update()

    def perform_search(self, query):
        """执行搜索逻辑"""
        print(f"执行搜索: {query}")

        self.user_info["searched"] += 1
        if hasattr(self, 'searched_count_text'):
            self.searched_count_text.value = str(self.user_info["searched"])

        if self.current_page_index != 1:
            self.on_custom_nav_click(1)

        filtered_plants = self.filter_plants(query)
        self.update_search_results(filtered_plants, query)

    def filter_plants(self, query):
        """根据查询过滤菌类列表"""
        query_lower = query.lower()
        results = []

        for plant in self.all_plants:
            if (
                query_lower in plant["name"].lower() or
                query_lower in plant["desc"].lower() or
                query_lower in plant.get("sci_name", "").lower() or
                query_lower in plant.get("family", "").lower() or
                query_lower in plant.get("features", "").lower() or
                query_lower in plant.get("culture", "").lower()
            ):
                results.append(plant)

        return results

    def update_search_results(self, plants, query):
        """更新搜索结果显示"""
        if hasattr(self, 'search_results'):
            if plants:
                result_cards = [self.create_plant_card(plant) for plant in plants]
                self.search_results.controls = [
                    Container(
                        content=Text(f"搜索 '{query}' 的结果 ({len(plants)}个)",
                             size=16, weight=ft.FontWeight.BOLD),
                        margin=ft.margin.only(bottom=10)
                    )
                ] + result_cards
            else:
                self.search_results.controls = [
                    Container(
                        content=Column([
                            Icon(ft.Icons.SEARCH_OFF, size=48, color=Colors.GREY_400),
                            Text(f"未找到与 '{query}' 相关的菌类",
                                 size=16, color=Colors.GREY_600, text_align="center")
                        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                        alignment=ft.alignment.center,
                        padding=50
                    )
                ]

            self.page.update()

    def open_image_picker(self, e):
        """打开文件选择器选图"""
        self.image_picker.pick_files(
            allow_multiple=False,
            file_type=ft.FilePickerFileType.IMAGE,
            dialog_title="选择菌类图片"
        )

    def on_image_selected(self, e: ft.FilePickerResultEvent):
        """处理选图结果"""
        if e.files:
            image_path = e.files[0].path
            print(f"选择的图片路径: {image_path}")
            self.photo_preview.src = image_path
            self.photo_preview.visible = True

            preview_content = Column([
                self.photo_preview,
                Container(height=10),
                Text("准备开始识别...", size=14)
            ])
            self.page_container.content = preview_content
            self.page.update()

            self.page.run_task(self.identify_plant_from_image, image_path)

    async def identify_plant_from_image(self, image_path):
        """识别菌类的异步方法，并应用名称映射和毒性判断"""
        try:
            result = await self.api_client.identify_plant(image_path)

            if result.get('success'):
                plant_data = result.get('data', {})
                identification = plant_data.get('identification', {})
                top_prediction = identification.get('top_prediction', {})

                # 获取原始识别名称，应用映射
                raw_name = top_prediction.get('name', '未知菌类')
                plant_name = self.NAME_MAPPING.get(raw_name, raw_name)

                # 使用映射后的名称判断毒性（基于前端的毒蘑菇列表）
                is_toxic = plant_name in self.TOXIC_MUSHROOMS

                # 获取置信度（后端返回）
                confidence = top_prediction.get('confidence', 0)

                # 如果有毒，弹出应急警告
                if is_toxic:
                    emergency_dialog = self.create_emergency_alert_dialog(plant_name, is_toxic=True)
                    self.page.dialog = emergency_dialog
                    emergency_dialog.open = True
                    self.page.update()

                result_content = Column([
                    Text("🎉 识别完成！", size=20, weight=ft.FontWeight.BOLD, color=Colors.RED if is_toxic else Colors.GREEN),
                    Container(height=10),
                    Text(f"菌类名称: {plant_name}", size=18, weight=ft.FontWeight.BOLD),
                    Text(f"置信度: {confidence:.2%}", size=16, color=Colors.BLUE),
                    Text(f"毒性: {'剧毒，禁止食用！' if is_toxic else '可食用（需确认）'}", size=16, color=Colors.RED if is_toxic else Colors.GREEN_600),
                    Container(height=10),
                    ElevatedButton(
                        "查看详情",
                        on_click=lambda e: self.navigate_to_plant_detail_by_name(plant_name),
                        style=ft.ButtonStyle(
                            bgcolor=Colors.GREEN_600,
                            color=Colors.WHITE
                        )
                    ) if any(p["name"] == plant_name for p in self.all_plants) else Container()
                ])

                result_card = Card(
                    content=Container(
                        content=result_content,
                        padding=20,
                        border_radius=border_radius.all(10)
                    ),
                    elevation=3,
                    margin=10
                )

                self.identification_result.controls = [result_card]
                self.identification_result.visible = True

            else:
                error_msg = result.get('message', '识别失败')
                error_content = Column([
                    Text("❌ 识别失败", size=18, color=Colors.RED),
                    Text(f"错误: {error_msg}", size=14),
                ])
                error_card = Card(
                    content=Container(
                        content=error_content,
                        padding=20,
                        border_radius=border_radius.all(10)
                    ),
                    elevation=3,
                    margin=10
                )

                self.identification_result.controls = [error_card]
                self.identification_result.visible = True

            self.on_custom_nav_click(0)

        except Exception as e:
            print(f"❌ 识别过程异常: {e}")
            error_content = Column([
                Text("❌ 识别异常", size=18, color=Colors.RED),
                Text(f"错误: {str(e)}", size=14),
            ])
            error_card = Card(
                content=Container(
                    content=error_content,
                    padding=20,
                    border_radius=border_radius.all(10)
                ),
                elevation=3,
                margin=10
            )

            self.identification_result.controls = [error_card]
            self.identification_result.visible = True
            self.on_custom_nav_click(0)

    def navigate_to_plant_detail_by_name(self, plant_name):
        """通过菌类名称导航到详情页"""
        plant_data = next((p for p in self.all_plants if p["name"] == plant_name), None)
        if plant_data:
            self.navigate_to_plant_detail(plant_data)
        else:
            snack = SnackBar(Text(f"未找到菌类 '{plant_name}' 的详细信息"))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

    def navigate_to_plant_detail(self, plant):
        """导航到菌类详情页面"""
        self.page_history.append(self.current_page_index)

        detail_page = self.create_plant_detail_page(plant)
        self.page_container.content = detail_page

        if hasattr(self, 'top_bar'):
            self.top_bar.content.controls[1].content.value = plant["name"]
            back_button = self.top_bar.content.controls[0].content
            back_button.disabled = False

        self.page.update()

    def navigate_to_notification_page(self):
        """导航到通知页面"""
        self.page_history.append(self.current_page_index)
        self.current_page_index = 5

        for note in self.notifications:
            if not note["is_read"]:
                note["is_read"] = True
                self.unread_count -= 1

        self.unread_count = max(0, self.unread_count)
        self.notification_badge.controls[1].visible = self.unread_count > 0
        self.badge_text.value = str(self.unread_count) if self.unread_count <= 99 else "99+"

        self.page_container.content = self.create_notification_page()

        if hasattr(self, 'top_bar'):
            self.top_bar.content.controls[1].content.value = "通知中心"
            back_button = self.top_bar.content.controls[0].content
            back_button.disabled = False

        self.page.update()

    def navigate_to_notification_detail(self, notification):
        """导航到通知详情页面"""
        self.page_history.append(self.current_page_index)
        self.current_page_index = 6

        detail_page = self.create_notification_detail_page(notification)
        self.page_container.content = detail_page

        if hasattr(self, 'top_bar'):
            self.top_bar.content.controls[1].content.value = "通知详情"
            back_button = self.top_bar.content.controls[0].content
            back_button.disabled = False

        self.page.update()

    def navigate_to_page(self, target_page, page_name):
        """导航到指定页面"""
        self.page_history.append(self.current_page_index)

        if page_name == "个人资料":
            content = self.create_profile_page()
        else:
            content = target_page

        self.page_container.content = content

        if hasattr(self, 'top_bar'):
            self.top_bar.content.controls[1].content.value = page_name
            back_button = self.top_bar.content.controls[0].content
            back_button.disabled = False

        self.page.update()

    def toggle_collection(self, plant):
        """切换菌类收藏状态"""
        plant_name = plant["name"]

        if plant_name in self.collected_plants:
            self.collected_plants.remove(plant_name)
            snack = SnackBar(Text(f"已取消收藏 {plant_name}"))

            for i, item in enumerate(self.collection_history):
                if item["plant"]["name"] == plant_name:
                    del self.collection_history[i]
                    break
        else:
            self.collected_plants.add(plant_name)
            snack = SnackBar(Text(f"已收藏 {plant_name}"))

            self.collection_history.insert(0, {"plant": plant, "time": datetime.datetime.now()})
            if len(self.collection_history) > 20:
                self.collection_history.pop()

        self.update_collection_list()
        self.update_profile_history_lists()
        self.update_profile_statistics()

        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def update_profile_statistics(self):
        """更新个人资料页的统计数字"""
        if hasattr(self, 'browsed_count_text'):
            self.browsed_count_text.value = str(len(self.browsing_history))
        if hasattr(self, 'collected_count_text'):
            self.collected_count_text.value = str(len(self.collected_plants))
        if hasattr(self, 'searched_count_text'):
            self.searched_count_text.value = str(self.user_info["searched"])

    def update_collection_list(self):
        """更新收藏页列表"""
        if hasattr(self, 'collection_list'):
            self.collection_list.controls.clear()

            if not self.collected_plants:
                self.collection_list.controls.append(Text("您还没有收藏任何菌类，浏览后可收藏喜欢的菌类"))
            else:
                for item in self.collection_history:
                    plant_card = self.create_plant_card(item["plant"])
                    self.collection_list.controls.append(plant_card)

    def update_profile_history_lists(self):
        """更新个人资料页的历史/收藏列表"""
        if hasattr(self, 'browsing_history_list') and hasattr(self, 'collection_history_list'):
            self.browsing_history_list.controls.clear()
            if not self.browsing_history:
                self.browsing_history_list.controls.append(Text("暂无浏览记录"))
            else:
                for item in self.browsing_history[:10]:
                    plant_card = self.create_profile_history_card(item, is_collection=False)
                    self.browsing_history_list.controls.append(plant_card)

            self.collection_history_list.controls.clear()
            if not self.collection_history:
                self.collection_history_list.controls.append(Text("暂无收藏记录"))
            else:
                for item in self.collection_history[:10]:
                    plant_card = self.create_profile_history_card(item, is_collection=True)
                    self.collection_history_list.controls.append(plant_card)

    def create_profile_history_card(self, item, is_collection=False):
        """创建个人资料页的历史/收藏卡片"""
        plant_data = item["plant"]
        time_str = item["time"].strftime("%Y-%m-%d %H:%M")

        delete_button = IconButton(
            icon=ft.Icons.DELETE,
            icon_color=Colors.RED_500,
            on_click=lambda e, p=plant_data, is_coll=is_collection: self.delete_single_item(p, is_coll),
            visible=self.editing_profile
        )

        return Card(
            content=Container(
                content=Row([
                    Image(
                        src=plant_data["image_url"],
                        width=60,
                        height=60,
                        fit=ft.ImageFit.COVER
                    ),
                    Column([
                        Text(plant_data["name"], weight=ft.FontWeight.BOLD),
                        Text(f"科属：{plant_data['family']}", size=12),
                        Text(time_str, size=11, color=Colors.GREY_500)
                    ],
                    spacing=3,
                    expand=True
                    ),
                    Icon(
                        name=ft.Icons.STAR if is_collection else ft.Icons.HISTORY,
                        color=Colors.YELLOW_500 if is_collection else Colors.GREY_500,
                        size=20
                    ),
                    delete_button
                ],
                spacing=10,
                vertical_alignment=ft.CrossAxisAlignment.CENTER
                ),
                padding=10,
                on_click=lambda e, p=plant_data: self.navigate_to_plant_detail(p) if not self.editing_profile else None
            ),
            elevation=2,
            margin=ft.margin.symmetric(vertical=2)
        )

    def delete_single_item(self, plant_data, is_collection):
        """删除单个历史记录或收藏项"""
        plant_name = plant_data["name"]

        if is_collection:
            if plant_name in self.collected_plants:
                self.collected_plants.remove(plant_name)

            for i, item in enumerate(self.collection_history):
                if item["plant"]["name"] == plant_name:
                    del self.collection_history[i]
                    break

            snack = SnackBar(Text(f"已从收藏中移除 {plant_name}"))
            self.update_collection_list()
        else:
            for i, item in enumerate(self.browsing_history):
                if item["plant"]["name"] == plant_name:
                    del self.browsing_history[i]
                    break

            snack = SnackBar(Text(f"已从浏览历史中移除 {plant_name}"))

        self.update_profile_history_lists()
        self.update_profile_statistics()

        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def add_to_browsing_history(self, plant_data):
        """添加到浏览历史"""
        for i, item in enumerate(self.browsing_history):
            if item["plant"]["name"] == plant_data["name"]:
                del self.browsing_history[i]
                break

        self.browsing_history.insert(0, {"plant": plant_data, "time": datetime.datetime.now()})
        if len(self.browsing_history) > 20:
            self.browsing_history.pop()

        self.update_profile_history_lists()
        self.update_profile_statistics()

    def on_avatar_selected(self, e: ft.FilePickerResultEvent):
        """处理头像上传"""
        if e.files:
            file_path = e.files[0].path
            self.avatar_image.src = file_path
            self.user_info["avatar_url"] = file_path
            snack = SnackBar(Text("头像已更新"))
            self.page.snack_bar = snack
            snack.open = True
            self.page.update()

    def update_notification_list(self):
        """更新通知列表"""
        if hasattr(self, 'notification_list'):
            self.notification_list.controls.clear()

            if not self.notifications:
                self.notification_list.controls.append(Text("暂无通知", color=Colors.GREY_500))
            else:
                for note in self.notifications:
                    bg_color = Colors.WHITE if note["is_read"] else Colors.LIGHT_GREEN_50

                    card = Card(
                        content=Container(
                            content=Column([
                                Text(note["title"], weight=ft.FontWeight.BOLD),
                                Text(note["time"].strftime("%Y-%m-%d %H:%M"), size=12, color=Colors.GREY_500),
                                Text(note["content"][:100] + "..." if len(note["content"]) > 100 else note["content"],
                                     size=14, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                            ],
                            spacing=5
                            ),
                            padding=10,
                            bgcolor=bg_color,
                            border_radius=border_radius.all(8),
                            on_click=lambda e, n=note: self.navigate_to_notification_detail(n)
                        ),
                        elevation=2,
                        margin=ft.margin.symmetric(vertical=5)
                    )
                    self.notification_list.controls.append(card)

    def create_welcome_notification(self):
        """创建欢迎通知"""
        welcome_content = """欢迎来到滇菌智护！在这里您可以识别菌类、浏览菌类库、收藏喜欢的菌类，并学习毒菌急救知识。"""
        self.add_notification("欢迎来到滇菌智护", welcome_content)

    def add_notification(self, title, content):
        """添加通知"""
        notification = {
            "id": len(self.notifications) + 1,
            "title": title,
            "content": content,
            "is_read": False,
            "time": datetime.datetime.now()
        }
        self.notifications.insert(0, notification)
        self.unread_count += 1
        self.notification_badge.controls[1].visible = self.unread_count > 0
        self.badge_text.value = str(self.unread_count) if self.unread_count <= 99 else "99+"
        self.page.update()

    def toggle_theme(self, e):
        """切换主题"""
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.page.bgcolor = Colors.LIGHT_GREEN_900
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.page.bgcolor = Colors.LIGHT_GREEN_50
        self.page.update()

    def toggle_notification(self, e):
        """切换通知设置"""
        snack = SnackBar(Text("通知设置已更新"))
        self.page.snack_bar = snack
        snack.open = True
        self.page.update()

    def manage_browsing_history(self, e):
        """管理浏览历史"""
        if self.browsing_history:
            def confirm_clear(e):
                self.browsing_history.clear()
                self.update_profile_history_lists()
                self.update_profile_statistics()
                snack = SnackBar(Text("浏览历史已清空"))
                self.page.snack_bar = snack
                snack.open = True
                self.page.close(dialog)
                self.page.update()

            def cancel_clear(e):
                self.page.close(dialog)
                self.page.update()

            dialog = ft.AlertDialog(
                title=Text("清空浏览历史"),
                content=Text("确定要清空所有浏览历史吗？此操作不可撤销。"),
                actions=[
                    ElevatedButton("取消", on_click=cancel_clear),
                    ElevatedButton("清空", on_click=confirm_clear, style=ft.ButtonStyle(bgcolor=Colors.RED_500))
                ]
            )

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()

    def manage_collections(self, e):
        """管理收藏"""
        if self.collected_plants:
            def confirm_clear(e):
                self.collected_plants.clear()
                self.collection_history.clear()
                self.update_collection_list()
                self.update_profile_history_lists()
                self.update_profile_statistics()
                snack = SnackBar(Text("所有收藏已清空"))
                self.page.snack_bar = snack
                snack.open = True
                self.page.close(dialog)
                self.page.update()

            def cancel_clear(e):
                self.page.close(dialog)
                self.page.update()

            dialog = ft.AlertDialog(
                title=Text("清空所有收藏"),
                content=Text("确定要清空所有收藏吗？此操作不可撤销。"),
                actions=[
                    ElevatedButton("取消", on_click=cancel_clear),
                    ElevatedButton("清空", on_click=confirm_clear, style=ft.ButtonStyle(bgcolor=Colors.RED_500))
                ]
            )

            self.page.dialog = dialog
            dialog.open = True
            self.page.update()


def main(page: Page):
    """应用入口"""
    page.title = "滇菌智护"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = Colors.LIGHT_GREEN_50

    page.window.min_width = 320
    page.window.min_height = 568
    page.window.width = 375
    page.window.height = 667

    app = PlantApp(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)