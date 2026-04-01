import flet as ft
from flet import (Page, Container, Row, Column, IconButton, Text, PopupMenuButton, 
                 PopupMenuItem, Icon, Stack, alignment, border_radius, Colors)


class QQStyleBottomNav:
    """QQ风格底部导航栏组件"""
    
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.nav_items = []
        self.create_nav_items()
        
    def create_nav_items(self):
        """创建导航项 - 模仿QQ的5个主要功能"""
        nav_config = [
            {
                "index": 0,
                "label": "首页",
                "icon_outlined": ft.Icons.HOME_OUTLINED,
                "icon_filled": ft.Icons.HOME,
                "badge": None
            },
            {
                "index": 1,
                "label": "搜索",
                "icon_outlined": ft.Icons.SEARCH_OUTLINED,
                "icon_filled": ft.Icons.SEARCH,
                "badge": None
            },
            {
                "index": 2,
                "label": "植物库",
                "icon_outlined": ft.Icons.LOCAL_FLORIST_OUTLINED,
                "icon_filled": ft.Icons.LOCAL_FLORIST,
                "badge": None
            },
            {
                "index": 3,
                "label": "收藏",
                "icon_outlined": ft.Icons.STAR_OUTLINE,
                "icon_filled": ft.Icons.STAR,
                "badge": "5"  # 模拟收藏数量
            },
            {
                "index": 4,
                "label": "我的",
                "icon_outlined": ft.Icons.PERSON_OUTLINE,
                "icon_filled": ft.Icons.PERSON,
                "badge": "3"  # 模拟消息数量
            }
        ]
        
        for config in nav_config:
            self.nav_items.append(self._create_nav_item(config))
    
    def _create_nav_item(self, config):
        """创建单个导航项 - 模仿QQ的图标+文字+徽章布局"""
        index = config["index"]
        label = config["label"]
        icon_outlined = config["icon_outlined"]
        icon_filled = config["icon_filled"]
        badge = config["badge"]
        
        # 图标容器
        icon_container = Container(
            content=Stack(
                controls=[
                    # 主图标
                    Icon(
                        name=icon_outlined,
                        size=24,
                        color=Colors.GREY_600
                    ),
                    # 选中状态图标（隐藏）
                    Icon(
                        name=icon_filled,
                        size=24,
                        color=Colors.GREEN_600,
                        visible=False
                    ),
                    # 徽章（如果有）
                    Container(
                        content=Text(
                            badge,
                            size=10,
                            color=Colors.WHITE,
                            weight=ft.FontWeight.BOLD
                        ),
                        bgcolor=Colors.RED,
                        width=16,
                        height=16,
                        border_radius=border_radius.all(8),
                        alignment=alignment.center,
                        visible=badge is not None
                    ) if badge else Container()
                ]
            ),
            width=32,
            height=32
        )
        
        # 文字标签
        text_label = Text(
            label,
            size=11,
            color=Colors.GREY_600,
            weight=ft.FontWeight.NORMAL
        )
        
        # 完整的导航项容器
        nav_item = Container(
            content=Column(
                controls=[
                    icon_container,
                    text_label
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4
            ),
            padding=ft.padding.symmetric(vertical=8, horizontal=4),
            on_click=lambda e, idx=index: self.parent_app.on_custom_nav_click(idx),
            expand=True,  # 等宽分配
            alignment=alignment.center
        )
        
        return {
            "container": nav_item,
            "icon_outlined": icon_container.content.controls[0],
            "icon_filled": icon_container.content.controls[1],
            "text": text_label,
            "badge": icon_container.content.controls[2] if badge else None
        }
    
    def build(self):
        """构建完整的导航栏"""
        return Container(
            content=Row(
                controls=[item["container"] for item in self.nav_items],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,  # 等间距分布
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0  # 无间距，完全等宽
            ),
            bgcolor=Colors.WHITE,
            padding=ft.padding.symmetric(vertical=4),
            height=40,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=8,
                color=Colors.BLACK26,
                offset=ft.Offset(0, -2)
            )
        )
    
    def update_selection(self, selected_index):
        """更新选中状态 - 模仿QQ的选中效果"""
        for i, item in enumerate(self.nav_items):
            is_selected = (i == selected_index)
            
            # 图标状态
            item["icon_outlined"].visible = not is_selected
            item["icon_filled"].visible = is_selected
            
            # 文字状态
            if is_selected:
                item["text"].color = Colors.GREEN_600
                item["text"].weight = ft.FontWeight.BOLD
                item["text"].size = 11
            else:
                item["text"].color = Colors.GREY_600
                item["text"].weight = ft.FontWeight.NORMAL
                item["text"].size = 11


def create_top_bar(parent_app, title, can_go_back, notification_badge):
    """创建固定顶部栏组件"""
    return Container(
        content=Row([
            # 左侧：返回按钮
            Container(
                content=IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=parent_app.go_back,
                    disabled=not can_go_back,
                    icon_size=22,  # 略微减小图标大小
                    style=ft.ButtonStyle(
                        color=Colors.WHITE
                    )
                ),
                width=45  # 减小宽度，为标题留出更多空间
            ),
            # 中间：标题 - 进一步优化显示以确保"青芜识界"完全可见
            Container(
                content=Text(title, size=16, weight=ft.FontWeight.BOLD, color=Colors.WHITE, no_wrap=True),
                expand=True,
                alignment=alignment.center,
                padding=ft.padding.symmetric(horizontal=5)  # 微调内边距
            ),
            # 右侧：功能按钮 - 精简布局，减小间距
            Row([
                # 相机按钮
                IconButton(
                    icon=ft.Icons.CAMERA_ALT,
                    on_click=parent_app.open_image_picker,
                    tooltip="拍照识别",
                    icon_size=22,  # 略微减小图标大小
                    style=ft.ButtonStyle(
                        color=Colors.WHITE
                    )
                ),
                # 搜索按钮
                IconButton(
                    icon=ft.Icons.SEARCH,
                    on_click=lambda _: parent_app.on_custom_nav_click(1),
                    tooltip="搜索植物",
                    icon_size=22,  # 略微减小图标大小
                    style=ft.ButtonStyle(
                        color=Colors.WHITE
                    )
                ),
                # 通知按钮
                notification_badge,
                # 菜单按钮 - 保持不变
                PopupMenuButton(
                    icon=ft.Icons.MORE_VERT,
                    icon_color=Colors.WHITE,
                    icon_size=22,
                    items=[
                        PopupMenuItem(
                            text="个人资料",
                            on_click=lambda _: parent_app.navigate_to_page(parent_app.profile_page, "个人资料")
                        ),
                        PopupMenuItem(
                            text="我的收藏",
                            on_click=lambda _: parent_app.navigate_to_page(parent_app.collection_page, "我的收藏")
                        ),
                        PopupMenuItem(
                            text="设置",
                            on_click=lambda _: parent_app.navigate_to_page(parent_app.settings_page, "设置")
                        ),
                    ]
                ),
            ], spacing=0)  # 进一步减小按钮间距
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        bgcolor=Colors.GREEN_600,
        padding=10,
        height=56,
        margin=0,
    )


def create_bottom_spacer():
    """创建底部导航栏上方的间隔容器"""
    return Container(height=650, bgcolor=Colors.LIGHT_GREEN_50)  # 调整为650