"""生成 GOAI 2026 初赛 PPT 第一版。

内容与 hackathon/goai-2026-submission/PPT-内容稿.md 对齐。
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt


SLIDES = [
    {
        "title": "MeetSpot 多人会面公平决策智能体",
        "bullets": [
            "赛道：无界应用（Boundless Agents）",
            "定位：输入各方位置与需求，自主完成公平中心计算、地点检索、多因子评分和可解释推荐，把\"在哪见\"变成全体可验证的公平决策",
        ],
    },
    {
        "title": "问题与场景",
        "bullets": [
            "四类用户：朋友聚会、学生社团、企业团建、异地客户约见和远程团队碰面",
            "痛点：拉群讨论半小时；众口难调；地图工具按个人位置就近返回，对其他人不公平",
            "量化口径：传统方式人均决策时间约 20 至 30 分钟，MeetSpot 单次请求约 10 秒",
        ],
    },
    {
        "title": "方案总览",
        "bullets": [
            "五步闭环：地址解析、公平中心计算、POI 检索、多因子评分、可解释推荐",
            "复杂度路由：简单请求走规则模式，复杂请求走 Agent 模式",
            "结果交付：地图、评分卡片、推理摘要、多轮调整",
        ],
    },
    {
        "title": "Agent 能力",
        "bullets": [
            "任务理解：意图分类（快速找点、复杂需求、多轮调整）",
            "工具调用：Geocode、Center、POI Search、Scoring、Result 五步工具链，保留调用记录",
            "多轮协商：基于推荐结果的继续调整，换主题、限预算、增减人数",
            "结果验证：置信度与质量门，候选不足时回退建议",
            "执行证据：可追溯的推理摘要（输入、中间结果、评分依据）",
        ],
    },
    {
        "title": "算法与创新",
        "bullets": [
            "球面几何公平中心，2 至 10 人规模",
            "规则评分与 LLM 语义评分双通道融合",
            "五步可解释推理链，推荐理由可追溯",
            "支持 350+ 城市、12 类场所主题",
        ],
    },
    {
        "title": "Demo 演示",
        "bullets": [
            "线上地址：https://meetspot-irq2.onrender.com/",
            "实测证据：3 个北京地址，12.4 秒返回 6 家咖啡馆推荐，含评分依据与地图",
            "素材：首页截图、结果页截图、推理链截图、AI 对话截图、Demo 视频",
        ],
    },
    {
        "title": "技术与工程",
        "bullets": [
            "FastAPI + SQLAlchemy 2.0，Docker 一键部署，Render 在线",
            "DeepSeek（deepseek-v4-flash）做语义评分，高德与 Google 双地图",
            "CI 全绿，43 个测试通过，多语言中英",
            "复杂度路由、规则/Agent 双模式、五步流水线",
        ],
    },
    {
        "title": "数据与合规",
        "bullets": [
            "只接收地址文本，不留存个人敏感信息",
            "调用公共地图 API 与 DeepSeek，商业 API 依赖如实披露",
            "输出提供依据与评分说明，不替代专业判断",
        ],
    },
    {
        "title": "开放与复用",
        "bullets": [
            "MIT 协议，GitHub 523 星、58 fork",
            "中英 README、API 文档、部署说明齐全",
            "地址解析、公平中心、评分引擎可拆分为独立组件，供本地生活决策类应用二次开发",
        ],
    },
    {
        "title": "迭代与落地",
        "bullets": [
            "近期：企业会议规划模式（批量地址、预算约束、行程说明）",
            "中期：多轮协商升级、结果导出与分享、日历集成",
            "长期：国际场景扩展，引擎作为开放能力输出",
        ],
    },
    {
        "title": "团队与进展",
        "bullets": [
            "项目保持活跃迭代，最近提交 2026 年 8 月",
            "CI 全绿，7 个 GitHub Actions workflow",
            "社区持续反馈，issue 驱动迭代",
            "原有基础：开源社区与线上 Demo 积累；本次新增：稳定性修复、Agent 闭环、评测基准与参赛材料",
        ],
    },
    {
        "title": "结尾",
        "bullets": [
            "主张：MeetSpot 是多人线下协作的公平决策引擎，不只是找地方",
            "现场可演示线上 Demo，代码与文档全部开源",
            "联系方式与项目链接",
        ],
    },
]


def build(output_path: str) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    brand_dark = RGBColor(0x05, 0x44, 0x5E)
    brand_accent = RGBColor(0x20, 0xD3, 0xFF)
    text_dark = RGBColor(0x11, 0x18, 0x27)

    def add_background(slide, color):
        bg = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height
        )
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        slide.shapes._spTree.remove(bg._element)
        slide.shapes._spTree.insert(2, bg._element)

    def add_brand_bar(slide):
        bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            0,
            0,
            prs.slide_width,
            Inches(0.12),
        )
        bar.fill.solid()
        bar.fill.fore_color.rgb = brand_accent
        bar.line.fill.background()

    # 封面
    cover = prs.slides.add_slide(prs.slide_layouts[6])
    add_background(cover, brand_dark)
    title_box = cover.shapes.add_textbox(
        Inches(1), Inches(2.4), Inches(11.3), Inches(1.4)
    )
    title_frame = title_box.text_frame
    title_frame.word_wrap = True
    title_p = title_frame.paragraphs[0]
    title_p.alignment = PP_ALIGN.CENTER
    title_run = title_p.add_run()
    title_run.text = SLIDES[0]["title"]
    title_run.font.size = Pt(44)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    subtitle_box = cover.shapes.add_textbox(
        Inches(1), Inches(4.1), Inches(11.3), Inches(1.6)
    )
    subtitle_frame = subtitle_box.text_frame
    subtitle_frame.word_wrap = True
    for i, line in enumerate(SLIDES[0]["bullets"]):
        p = subtitle_frame.paragraphs[0] if i == 0 else subtitle_frame.add_paragraph()
        p.alignment = PP_ALIGN.CENTER
        run = p.add_run()
        run.text = line
        run.font.size = Pt(20)
        run.font.color.rgb = RGBColor(0xC7, 0xED, 0xFA)

    for slide_data in SLIDES[1:]:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        add_background(slide, RGBColor(0xFF, 0xFF, 0xFF))
        add_brand_bar(slide)

        title_box = slide.shapes.add_textbox(
            Inches(0.7), Inches(0.35), Inches(12), Inches(0.9)
        )
        title_frame = title_box.text_frame
        title_p = title_frame.paragraphs[0]
        title_run = title_p.add_run()
        title_run.text = slide_data["title"]
        title_run.font.size = Pt(34)
        title_run.font.bold = True
        title_run.font.color.rgb = brand_dark

        body_box = slide.shapes.add_textbox(
            Inches(0.9), Inches(1.45), Inches(11.6), Inches(5.5)
        )
        body_frame = body_box.text_frame
        body_frame.word_wrap = True
        for i, bullet in enumerate(slide_data["bullets"]):
            p = body_frame.paragraphs[0] if i == 0 else body_frame.add_paragraph()
            p.space_after = Pt(14)
            run = p.add_run()
            run.text = bullet
            run.font.size = Pt(19)
            run.font.color.rgb = text_dark

        if slide_data["title"] == "Demo 演示":
            screenshot = Path(
                "hackathon/goai-2026-submission/assets/demo-result.png"
            )
            if not screenshot.exists():
                screenshot = Path("homepage-en.png")
            if screenshot.exists():
                slide.shapes.add_picture(
                    str(screenshot), Inches(1.0), Inches(4.6), width=Inches(7.6)
                )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    print(f"已生成: {output_path}")


if __name__ == "__main__":
    build("hackathon/goai-2026-submission/MeetSpot-GOAI2026-初赛PPT-v1.1.pptx")
