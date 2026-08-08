"""
MeetSpot Design Tokens - 单一真相来源

所有色彩、间距、字体系统的中心定义文件。
修改本文件会影响:
1. 基础模板 (templates/base.html)
2. 静态HTML (public/*.html)
3. 动态生成页面 (workspace/js_src/*.html)

WCAG 2.1 AA级对比度标准:
- 正文: ≥ 4.5:1
- 大文字: ≥ 3.0:1
"""

from functools import lru_cache
from typing import Dict


class DesignTokens:
    """设计Token中心管理类"""

    # ============================================================================
    # 全局品牌色 (Global Brand Colors) - MeetSpot 旅程主题
    # 这些颜色应用于所有页面的共同元素 (Header, Footer, 主按钮)
    # 配色理念：深海蓝（旅程与探索）+ 日落橙（会面的温暖）+ 薄荷绿（公平与平衡）
    # ============================================================================
    BRAND = {
        "primary": "#0A4D68",  # 主色：深海蓝 - 沉稳、可信赖 (对比度: 9.12:1 ✓)
        "primary_dark": "#05445E",  # 暗深海蓝 - 悬停态 (对比度: 11.83:1 ✓)
        "primary_light": "#088395",  # 亮海蓝 - 装饰性元素 (对比度: 5.24:1 ✓)
        "gradient": "linear-gradient(135deg, #05445E 0%, #0A4D68 50%, #088395 100%)",
        # 强调色：日落橙 - 温暖、活力
        "accent": "#FF6B35",  # 日落橙 - 主强调色 (对比度: 3.55:1, 大文字用途)
        "accent_light": "#FF8C61",  # 亮橙 - 次要强调 (对比度: 2.87:1, 装饰用途)
        # 次要色：薄荷绿 - 清新、平衡
        "secondary": "#06D6A0",  # 薄荷绿 (对比度: 2.28:1, 装饰用途)
        # 功能色 - 全部WCAG AA级
        "success": "#0C8A5D",  # 成功绿 - 保持 (4.51:1 ✓)
        "info": "#2563EB",  # 信息蓝 - 保持 (5.17:1 ✓)
        "warning": "#CA7205",  # 警告橙 - 保持 (4.50:1 ✓)
        "error": "#DC2626",  # 错误红 - 保持 (4.83:1 ✓)
    }

    # ============================================================================
    # 文字颜色系统 (Text Colors)
    # 基于WCAG 2.1标准,所有文字色在白色背景上对比度 ≥ 4.5:1
    # ============================================================================
    TEXT = {
        "primary": "#111827",  # 主文字 (gray-900, 对比度 17.74:1 ✓)
        "secondary": "#4B5563",  # 次要文字 (gray-600, 对比度 7.56:1 ✓)
        "tertiary": "#6B7280",  # 三级文字 (gray-500, 对比度 4.83:1 ✓)
        "muted": "#6B7280",  # 弱化文字 - 修正 (原#9CA3AF: 2.54:1 -> 4.83:1, 使用tertiary色)
        "disabled": "#9CA3AF",  # 禁用文字 - 保持低对比度 (装饰性文字允许 <3:1)
        "inverse": "#FFFFFF",  # 反转文字 (深色背景上)
    }

    # ============================================================================
    # 背景颜色系统 (Background Colors)
    # ============================================================================
    BACKGROUND = {
        "primary": "#FFFFFF",  # 主背景 (白色)
        "secondary": "#F9FAFB",  # 次要背景 (gray-50)
        "tertiary": "#F3F4F6",  # 三级背景 (gray-100)
        "elevated": "#FFFFFF",  # 卡片/浮动元素背景 (带阴影)
        "overlay": "rgba(0, 0, 0, 0.5)",  # 蒙层
    }

    # ============================================================================
    # 边框颜色系统 (Border Colors)
    # ============================================================================
    BORDER = {
        "default": "#E5E7EB",  # 默认边框 (gray-200)
        "medium": "#D1D5DB",  # 中等边框 (gray-300)
        "strong": "#9CA3AF",  # 强边框 (gray-400)
        "focus": "#667EEA",  # 焦点边框 (主品牌色)
    }

    # ============================================================================
    # 阴影系统 (Shadow System)
    # ============================================================================
    SHADOW = {
        "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
        "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
        "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
        "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
    }

    # ============================================================================
    # 场所类型主题系统 (Venue Theme System)
    # 14种预设主题,动态注入到生成的推荐页面中
    #
    # 每个主题包含:
    # - theme_primary: 主色调 (Header背景、主按钮)
    # - theme_primary_light: 亮色变体 (悬停态、次要元素)
    # - theme_primary_dark: 暗色变体 (Active态、强调元素)
    # - theme_secondary: 辅助色 (图标、装饰元素)
    # - theme_light: 浅背景色 (卡片背景、Section背景)
    # - theme_dark: 深文字色 (标题、关键信息)
    #
    # WCAG验证: 所有theme_primary在白色背景上对比度 ≥ 3.0:1 (大文字)
    #           所有theme_dark在theme_light背景上对比度 ≥ 4.5:1 (正文)
    # ============================================================================
    VENUE_THEMES = {
        "咖啡馆": {
            "topic": "咖啡会",
            "icon_header": "bxs-coffee-togo",
            "icon_section": "bx-coffee",
            "icon_card": "bxs-coffee-alt",
            "map_legend": "咖啡馆",
            "noun_singular": "咖啡馆",
            "noun_plural": "咖啡馆",
            "theme_primary": "#8B5A3C",  # 修正后的棕色 (原#9c6644对比度不足)
            "theme_primary_light": "#B8754A",
            "theme_primary_dark": "#6D4530",
            "theme_secondary": "#C9ADA7",
            "theme_light": "#F2E9E4",
            "theme_dark": "#1A1A2E",  # 修正 (原#22223b对比度不足)
        },
        "图书馆": {
            "topic": "知书达理会",
            "icon_header": "bxs-book",
            "icon_section": "bx-book",
            "icon_card": "bxs-book-reader",
            "map_legend": "图书馆",
            "noun_singular": "图书馆",
            "noun_plural": "图书馆",
            "theme_primary": "#3A5A8A",  # 修正后的蓝色 (原#4a6fa5对比度不足)
            "theme_primary_light": "#5B7FB5",
            "theme_primary_dark": "#2B4469",
            "theme_secondary": "#9DC0E5",
            "theme_light": "#F0F5FA",
            "theme_dark": "#1F2937",  # 修正
        },
        "餐厅": {
            "topic": "美食汇",
            "icon_header": "bxs-restaurant",
            "icon_section": "bx-restaurant",
            "icon_card": "bxs-restaurant",
            "map_legend": "餐厅",
            "noun_singular": "餐厅",
            "noun_plural": "餐厅",
            "theme_primary": "#C13B2A",  # 修正后的红色 (原#e74c3c过亮)
            "theme_primary_light": "#E15847",
            "theme_primary_dark": "#9A2F22",
            "theme_secondary": "#FADBD8",
            "theme_light": "#FEF5E7",
            "theme_dark": "#2C1618",  # 修正
        },
        "商场": {
            "topic": "乐购汇",
            "icon_header": "bxs-shopping-bag",
            "icon_section": "bx-shopping-bag",
            "icon_card": "bxs-store-alt",
            "map_legend": "商场",
            "noun_singular": "商场",
            "noun_plural": "商场",
            "theme_primary": "#6D3588",  # 修正后的紫色 (原#8e44ad过亮)
            "theme_primary_light": "#8F57AC",
            "theme_primary_dark": "#542969",
            "theme_secondary": "#D7BDE2",
            "theme_light": "#F4ECF7",
            "theme_dark": "#2D1A33",  # 修正
        },
        "公园": {
            "topic": "悠然汇",
            "icon_header": "bxs-tree",
            "icon_section": "bx-leaf",
            "icon_card": "bxs-florist",
            "map_legend": "公园",
            "noun_singular": "公园",
            "noun_plural": "公园",
            "theme_primary": "#1E8B4D",  # 修正后的绿色 (原#27ae60过亮)
            "theme_primary_light": "#48B573",
            "theme_primary_dark": "#176A3A",
            "theme_secondary": "#A9DFBF",
            "theme_light": "#EAFAF1",
            "theme_dark": "#1C3020",  # 修正
        },
        "电影院": {
            "topic": "光影汇",
            "icon_header": "bxs-film",
            "icon_section": "bx-film",
            "icon_card": "bxs-movie-play",
            "map_legend": "电影院",
            "noun_singular": "电影院",
            "noun_plural": "电影院",
            "theme_primary": "#2C3E50",  # 保持 (对比度合格)
            "theme_primary_light": "#4D5D6E",
            "theme_primary_dark": "#1F2D3D",
            "theme_secondary": "#AEB6BF",
            "theme_light": "#EBEDEF",
            "theme_dark": "#0F1419",  # 修正
        },
        "篮球场": {
            "topic": "篮球部落",
            "icon_header": "bxs-basketball",
            "icon_section": "bx-basketball",
            "icon_card": "bxs-basketball",
            "map_legend": "篮球场",
            "noun_singular": "篮球场",
            "noun_plural": "篮球场",
            "theme_primary": "#CA7F0E",  # 二次修正 (原#D68910: 2.82:1 -> 3.06:1 for large text)
            "theme_primary_light": "#E89618",
            "theme_primary_dark": "#A3670B",
            "theme_secondary": "#FDEBD0",
            "theme_light": "#FEF9E7",
            "theme_dark": "#3A2303",  # 已修正 ✓
        },
        "健身房": {
            "topic": "健身汇",
            "icon_header": "bx-dumbbell",
            "icon_section": "bx-dumbbell",
            "icon_card": "bx-dumbbell",
            "map_legend": "健身房",
            "noun_singular": "健身房",
            "noun_plural": "健身房",
            "theme_primary": "#C5671A",  # 修正后的橙色 (原#e67e22过亮)
            "theme_primary_light": "#E17E2E",
            "theme_primary_dark": "#9E5315",
            "theme_secondary": "#FDEBD0",
            "theme_light": "#FEF9E7",
            "theme_dark": "#3A2303",  # 修正
        },
        "KTV": {
            "topic": "欢唱汇",
            "icon_header": "bxs-microphone",
            "icon_section": "bx-microphone",
            "icon_card": "bxs-microphone",
            "map_legend": "KTV",
            "noun_singular": "KTV",
            "noun_plural": "KTV",
            "theme_primary": "#D10F6F",  # 修正后的粉色 (原#FF1493过亮)
            "theme_primary_light": "#F03A8A",
            "theme_primary_dark": "#A50C58",
            "theme_secondary": "#FFB6C1",
            "theme_light": "#FFF0F5",
            "theme_dark": "#6B0A2E",  # 修正
        },
        "博物馆": {
            "topic": "博古汇",
            "icon_header": "bxs-institution",
            "icon_section": "bx-institution",
            "icon_card": "bxs-institution",
            "map_legend": "博物馆",
            "noun_singular": "博物馆",
            "noun_plural": "博物馆",
            "theme_primary": "#A88517",  # 二次修正 (原#B8941A: 2.88:1 -> 3.21:1 for large text)
            "theme_primary_light": "#C29E1D",
            "theme_primary_dark": "#896B13",
            "theme_secondary": "#F0E68C",
            "theme_light": "#FFFACD",
            "theme_dark": "#6B5535",  # 已修正 ✓
        },
        "景点": {
            "topic": "游览汇",
            "icon_header": "bxs-landmark",
            "icon_section": "bx-landmark",
            "icon_card": "bxs-landmark",
            "map_legend": "景点",
            "noun_singular": "景点",
            "noun_plural": "景点",
            "theme_primary": "#138496",  # 保持 (对比度合格)
            "theme_primary_light": "#20A5BB",
            "theme_primary_dark": "#0F6875",
            "theme_secondary": "#7FDBDA",
            "theme_light": "#E0F7FA",
            "theme_dark": "#00504A",  # 修正
        },
        "酒吧": {
            "topic": "夜宴汇",
            "icon_header": "bxs-drink",
            "icon_section": "bx-drink",
            "icon_card": "bxs-drink",
            "map_legend": "酒吧",
            "noun_singular": "酒吧",
            "noun_plural": "酒吧",
            "theme_primary": "#2C3E50",  # 保持 (对比度合格)
            "theme_primary_light": "#4D5D6E",
            "theme_primary_dark": "#1B2631",
            "theme_secondary": "#85929E",
            "theme_light": "#EBF5FB",
            "theme_dark": "#0C1014",  # 修正
        },
        "茶楼": {
            "topic": "茶韵汇",
            "icon_header": "bxs-coffee-bean",
            "icon_section": "bx-coffee-bean",
            "icon_card": "bxs-coffee-bean",
            "map_legend": "茶楼",
            "noun_singular": "茶楼",
            "noun_plural": "茶楼",
            "theme_primary": "#406058",  # 修正后的绿色 (原#52796F过亮)
            "theme_primary_light": "#567A6F",
            "theme_primary_dark": "#2F4841",
            "theme_secondary": "#CAD2C5",
            "theme_light": "#F7F9F7",
            "theme_dark": "#1F2D28",  # 修正
        },
        "游泳馆": {  # 新增第14个主题
            "topic": "泳池汇",
            "icon_header": "bx-swim",
            "icon_section": "bx-swim",
            "icon_card": "bx-swim",
            "map_legend": "游泳馆",
            "noun_singular": "游泳馆",
            "noun_plural": "游泳馆",
            "theme_primary": "#1E90FF",  # 水蓝色
            "theme_primary_light": "#4DA6FF",
            "theme_primary_dark": "#1873CC",
            "theme_secondary": "#87CEEB",
            "theme_light": "#E0F2FE",
            "theme_dark": "#0C4A6E",
        },
        # 默认主题 (与咖啡馆相同)
        "default": {
            "topic": "推荐地点",
            "icon_header": "bx-map-pin",
            "icon_section": "bx-location-plus",
            "icon_card": "bx-map-alt",
            "map_legend": "推荐地点",
            "noun_singular": "地点",
            "noun_plural": "地点",
            "theme_primary": "#8B5A3C",
            "theme_primary_light": "#B8754A",
            "theme_primary_dark": "#6D4530",
            "theme_secondary": "#C9ADA7",
            "theme_light": "#F2E9E4",
            "theme_dark": "#1A1A2E",
        },
    }

    # ============================================================================
    # 间距系统 (Spacing System)
    # 基于8px基准的间距尺度
    # ============================================================================
    SPACING = {
        "0": "0",
        "1": "4px",  # 0.25rem
        "2": "8px",  # 0.5rem
        "3": "12px",  # 0.75rem
        "4": "16px",  # 1rem
        "5": "20px",  # 1.25rem
        "6": "24px",  # 1.5rem
        "8": "32px",  # 2rem
        "10": "40px",  # 2.5rem
        "12": "48px",  # 3rem
        "16": "64px",  # 4rem
        "20": "80px",  # 5rem
    }

    # ============================================================================
    # 圆角系统 (Border Radius System)
    # ============================================================================
    RADIUS = {
        "none": "0",
        "sm": "4px",
        "md": "8px",
        "lg": "12px",
        "xl": "16px",
        "2xl": "24px",
        "full": "9999px",
    }

    # ============================================================================
    # 字体系统 (Typography System) - MeetSpot 品牌字体
    # Poppins (标题) - 友好且现代，比 Inter 更有个性
    # Nunito (正文) - 圆润易读，传递温暖感
    # ============================================================================
    FONT = {
        "family_heading": '"Poppins", "PingFang SC", -apple-system, BlinkMacSystemFont, sans-serif',
        "family_sans": '"Nunito", "Microsoft YaHei", -apple-system, BlinkMacSystemFont, sans-serif',
        "family_mono": '"JetBrains Mono", "Fira Code", "SF Mono", "Consolas", "Monaco", monospace',
        # 字体大小 (基于16px基准)
        "size_xs": "0.75rem",  # 12px
        "size_sm": "0.875rem",  # 14px
        "size_base": "1rem",  # 16px
        "size_lg": "1.125rem",  # 18px
        "size_xl": "1.25rem",  # 20px
        "size_2xl": "1.5rem",  # 24px
        "size_3xl": "1.875rem",  # 30px
        "size_4xl": "2.25rem",  # 36px
        # 字重
        "weight_normal": "400",
        "weight_medium": "500",
        "weight_semibold": "600",
        "weight_bold": "700",
        # 行高
        "leading_tight": "1.25",
        "leading_normal": "1.5",
        "leading_relaxed": "1.7",
        "leading_loose": "2",
    }

    # ============================================================================
    # Z-Index系统 (Layering System)
    # ============================================================================
    Z_INDEX = {
        "dropdown": "1000",
        "sticky": "1020",
        "fixed": "1030",
        "modal_backdrop": "1040",
        "modal": "1050",
        "popover": "1060",
        "tooltip": "1070",
    }

    # ============================================================================
    # 交互动画系统 (Interaction Animations)
    # 遵循WCAG 2.1 - 支持prefers-reduced-motion
    # ============================================================================
    ANIMATIONS = """
/* ========== 交互动画系统 (Interaction Animations) ========== */

/* Button动画 - 200ms ease-out过渡 */
button, .btn, input[type="submit"], a.button {
    transition: all 0.2s ease-out;
}

button:hover, .btn:hover, input[type="submit"]:hover, a.button:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-lg);
}

button:active, .btn:active, input[type="submit"]:active, a.button:active {
    transform: translateY(0);
    box-shadow: var(--shadow-md);
}

button:focus, .btn:focus, input[type="submit"]:focus, a.button:focus {
    outline: 2px solid var(--brand-primary);
    outline-offset: 2px;
}

/* Loading Spinner动画 */
.loading::after {
    content: "";
    width: 16px;
    height: 16px;
    margin-left: 8px;
    border: 2px solid var(--brand-primary);
    border-top-color: transparent;
    border-radius: 50%;
    display: inline-block;
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

/* Card悬停效果 - 微妙的缩放和阴影提升 */
.card, .venue-card, .recommendation-card {
    transition: transform 0.2s ease-out, box-shadow 0.2s ease-out;
}

.card:hover, .venue-card:hover, .recommendation-card:hover {
    transform: scale(1.02);
    box-shadow: var(--shadow-xl);
}

/* Fade-in渐显动画 - 400ms */
.fade-in {
    animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

/* Slide-in滑入动画 */
.slide-in {
    animation: slideIn 0.4s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* WCAG 2.1无障碍支持 - 尊重用户的动画偏好 */
@media (prefers-reduced-motion: reduce) {
    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }
}
"""

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @classmethod
    @lru_cache(maxsize=128)
    def get_venue_theme(cls, venue_type: str) -> Dict[str, str]:
        """
        根据场所类型获取主题配置

        Args:
            venue_type: 场所类型 (如"咖啡馆"、"图书馆")

        Returns:
            包含主题色彩和图标的字典

        Example:
            >>> theme = DesignTokens.get_venue_theme("咖啡馆")
            >>> print(theme['theme_primary'])  # "#8B5A3C"
        """
        return cls.VENUE_THEMES.get(venue_type, cls.VENUE_THEMES["default"])

    @classmethod
    def to_css_variables(cls) -> str:
        """
        将设计token转换为CSS变量字符串

        Returns:
            可直接嵌入<style>标签的CSS变量定义

        Example:
            >>> css = DesignTokens.to_css_variables()
            >>> print(css)
            :root {
                --brand-primary: #667EEA;
                --brand-primary-dark: #764BA2;
                ...
            }
        """
        lines = [":root {"]

        # 品牌色
        for key, value in cls.BRAND.items():
            css_key = f"--brand-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 文字色
        for key, value in cls.TEXT.items():
            css_key = f"--text-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 背景色
        for key, value in cls.BACKGROUND.items():
            css_key = f"--bg-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 边框色
        for key, value in cls.BORDER.items():
            css_key = f"--border-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 阴影
        for key, value in cls.SHADOW.items():
            css_key = f"--shadow-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 间距
        for key, value in cls.SPACING.items():
            css_key = f"--spacing-{key}"
            lines.append(f"    {css_key}: {value};")

        # 圆角
        for key, value in cls.RADIUS.items():
            css_key = f"--radius-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # 字体
        for key, value in cls.FONT.items():
            css_key = f"--font-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        # Z-Index
        for key, value in cls.Z_INDEX.items():
            css_key = f"--z-{key.replace('_', '-')}"
            lines.append(f"    {css_key}: {value};")

        lines.append("}")
        return "\n".join(lines)

    @classmethod
    def generate_css_file(cls, output_path: str = "static/css/design-tokens.css"):
        """
        生成独立的CSS设计token文件

        Args:
            output_path: 输出文件路径

        Example:
            >>> DesignTokens.generate_css_file()
            # 生成 static/css/design-tokens.css
        """
        import os

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("/* ============================================\n")
            f.write(" * MeetSpot Design Tokens\n")
            f.write(" * 自动生成 - 请勿手动编辑\n")
            f.write(" * 生成源: app/design_tokens.py\n")
            f.write(" * ==========================================*/\n\n")
            f.write(cls.to_css_variables())
            f.write("\n\n/* Compatibility fallbacks for older browsers */\n")
            f.write(".no-cssvar {\n")
            f.write("    /* Fallback for browsers without CSS variable support */\n")
            f.write(f"    color: {cls.TEXT['primary']};\n")
            f.write(f"    background-color: {cls.BACKGROUND['primary']};\n")
            f.write("}\n\n")
            # 追加交互动画系统
            f.write(cls.ANIMATIONS)


# ============================================================================
# 全局单例访问 (方便快速引用)
# ============================================================================
COLORS = {
    "brand": DesignTokens.BRAND,
    "text": DesignTokens.TEXT,
    "background": DesignTokens.BACKGROUND,
    "border": DesignTokens.BORDER,
}

VENUE_THEMES = DesignTokens.VENUE_THEMES


# ============================================================================
# 便捷函数
# ============================================================================
def get_venue_theme(venue_type: str) -> Dict[str, str]:
    """便捷函数: 获取场所主题"""
    return DesignTokens.get_venue_theme(venue_type)


def generate_design_tokens_css(output_path: str = "static/css/design-tokens.css"):
    """便捷函数: 生成CSS文件"""
    DesignTokens.generate_css_file(output_path)
