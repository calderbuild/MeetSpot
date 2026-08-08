"""MeetSpotAgent - 智能会面地点推荐 Agent

基于 ReAct 模式实现的智能推荐代理，通过工具调用完成地点推荐任务。
"""

import json
from typing import Any, Dict, List, Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.agent.tools import (
    CalculateCenterTool,
    GeocodeTool,
    GenerateRecommendationTool,
    SearchPOITool,
)
from app.logger import logger
from app.schema import AgentState, Message
from app.tool.tool_collection import ToolCollection


SYSTEM_PROMPT = """你是 MeetSpot 智能会面助手。

工具：
1. geocode(address)：地址转经纬度，支持简称与地标
2. calculate_center(coordinates, keywords)：计算公平中心
3. search_poi(center_lng, center_lat, keywords, radius)：搜索附近场所
4. generate_recommendation(...)：生成最终推荐

流程：先 geocode 所有地址，再 calculate_center，再 search_poi，最后 generate_recommendation。

输出要求：中文；推荐 3-5 个场所，说明距离、评分与推荐理由；考虑特殊需求（停车、安静、商务等）。
失败处理：地址解析失败时给出具体提示；搜索无结果时调整关键词或扩大半径。
"""


class MeetSpotAgent(BaseAgent):
    """MeetSpot 智能会面推荐 Agent

    基于 ReAct 模式的智能代理，通过 think() -> act() 循环完成推荐任务。
    """

    name: str = "MeetSpotAgent"
    description: str = "智能会面地点推荐助手"

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = "请继续执行下一步，或者如果已完成所有工具调用，请生成最终推荐结果。"

    max_steps: int = 15  # 允许更多步骤以完成复杂任务

    # 工具集合
    available_tools: ToolCollection = Field(default=None)

    # 当前工具调用
    tool_calls: List[Any] = Field(default_factory=list)

    # 存储中间结果
    geocode_results: List[Dict] = Field(default_factory=list)
    center_point: Optional[Dict] = None
    search_results: List[Dict] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        # 初始化工具集合
        if self.available_tools is None:
            self.available_tools = ToolCollection(
                GeocodeTool(),
                CalculateCenterTool(),
                SearchPOITool(),
                GenerateRecommendationTool()
            )

    async def step(self) -> str:
        """执行一步: think + act

        Returns:
            步骤执行结果的描述
        """
        # Think: 决定下一步行动
        should_continue = await self.think()

        if not should_continue:
            self.state = AgentState.FINISHED
            return "任务完成"

        # Act: 执行工具调用
        result = await self.act()
        return result

    async def think(self) -> bool:
        """思考阶段 - 决定下一步行动

        使用 LLM 分析当前状态，决定是否需要调用工具以及调用哪个工具。

        Returns:
            是否需要继续执行
        """
        # 构建消息
        messages = self.memory.messages.copy()

        # 添加提示引导下一步
        if self.next_step_prompt and self.current_step > 1:
            messages.append(Message.user_message(self.next_step_prompt))

        # 调用 LLM 获取响应
        response = await self.llm.ask_tool(
            messages=messages,
            system_msgs=[Message.system_message(self.system_prompt)],
            tools=self.available_tools.to_params(),
            tool_choice="auto"
        )

        if response is None:
            logger.warning("LLM 返回空响应")
            return False

        # 提取工具调用和内容
        self.tool_calls = response.tool_calls or []
        content = response.content or ""

        logger.info(f"Agent 思考: {content[:200]}..." if len(content) > 200 else f"Agent 思考: {content}")

        if self.tool_calls:
            tool_names = [tc.function.name for tc in self.tool_calls]
            logger.info(f"选择工具: {tool_names}")

        # 保存 assistant 消息到记忆
        if self.tool_calls:
            # 带工具调用的消息
            tool_calls_data = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in self.tool_calls
            ]
            self.memory.add_message(Message(
                role="assistant",
                content=content,
                tool_calls=tool_calls_data
            ))
        elif content:
            # 纯文本消息（可能是最终回复）
            self.memory.add_message(Message.assistant_message(content))
            # 如果没有工具调用且有内容，可能是最终回复
            if "推荐" in content and len(content) > 100:
                return False  # 结束循环

        return bool(self.tool_calls) or bool(content)

    async def act(self) -> str:
        """行动阶段 - 执行工具调用

        执行思考阶段决定的工具调用，并将结果添加到记忆。

        Returns:
            工具执行结果的描述
        """
        if not self.tool_calls:
            # 没有工具调用，返回最后一条消息的内容
            return self.memory.messages[-1].content or "无操作"

        results = []
        for call in self.tool_calls:
            tool_name = call.function.name
            tool_args = call.function.arguments

            try:
                # 解析参数
                args = json.loads(tool_args) if isinstance(tool_args, str) else tool_args

                # 执行工具
                logger.info(f"执行工具: {tool_name}, 参数: {args}")
                result = await self.available_tools.execute(name=tool_name, tool_input=args)

                # 保存中间结果
                self._save_intermediate_result(tool_name, result, args)

                # 将工具结果添加到记忆
                result_str = str(result)
                self.memory.add_message(Message.tool_message(
                    content=result_str,
                    tool_call_id=call.id,
                    name=tool_name
                ))

                logger.info(f"工具 {tool_name} 完成")
                results.append(f"{tool_name}: 成功")

            except Exception as e:
                error_msg = f"工具执行失败: {str(e)}"
                logger.error(f"{tool_name} {error_msg}")

                # 添加错误消息到记忆
                self.memory.add_message(Message.tool_message(
                    content=error_msg,
                    tool_call_id=call.id,
                    name=tool_name
                ))
                results.append(f"{tool_name}: 失败 - {str(e)}")

        return " | ".join(results)

    def _save_intermediate_result(self, tool_name: str, result: Any, args: Dict) -> None:
        """保存工具执行的中间结果

        Args:
            tool_name: 工具名称
            result: 工具执行结果
            args: 工具参数
        """
        try:
            # 解析结果
            if hasattr(result, 'output') and result.output:
                data = json.loads(result.output) if isinstance(result.output, str) else result.output
            else:
                return

            if tool_name == "geocode" and data:
                self.geocode_results.append({
                    "address": args.get("address", ""),
                    "lng": data.get("lng"),
                    "lat": data.get("lat"),
                    "formatted_address": data.get("formatted_address", "")
                })

            elif tool_name == "calculate_center" and data:
                self.center_point = data.get("center")

            elif tool_name == "search_poi" and data:
                places = data.get("places", [])
                self.search_results.extend(places)

        except Exception as e:
            logger.debug(f"保存中间结果时出错: {e}")

    async def recommend(
        self,
        locations: List[str],
        keywords: str = "咖啡馆",
        requirements: str = ""
    ) -> Dict:
        """执行推荐任务

        这是 Agent 的主要入口方法，接收用户输入并返回推荐结果。

        Args:
            locations: 参与者位置列表
            keywords: 搜索关键词（场所类型）
            requirements: 用户特殊需求

        Returns:
            包含推荐结果的字典
        """
        # 重置状态
        self.geocode_results = []
        self.center_point = None
        self.search_results = []
        self.current_step = 0
        self.state = AgentState.IDLE
        self.memory.clear()

        # 构建任务描述
        locations_str = "、".join(locations)
        task = f"""请帮我找到适合会面的地点：

**参与者位置**：{locations_str}
**想找的场所类型**：{keywords}
**特殊需求**：{requirements or "无特殊需求"}

请按照工作流程执行：
1. 先用 geocode 工具获取每个位置的坐标
2. 用 calculate_center 计算中心点
3. 用 search_poi 搜索附近的 {keywords}
4. 用 generate_recommendation 生成推荐

最后请用中文总结推荐结果。"""

        # 执行任务
        result = await self.run(task)

        # 格式化返回结果
        return self._format_result(result)

    def _format_result(self, raw_result: str) -> Dict:
        """格式化最终结果

        Args:
            raw_result: Agent 执行的原始结果

        Returns:
            格式化的结果字典
        """
        # 获取最后一条 assistant 消息作为最终推荐
        final_recommendation = ""
        for msg in reversed(self.memory.messages):
            if msg.role == "assistant" and msg.content:
                final_recommendation = msg.content
                break

        return {
            "success": self.state == AgentState.IDLE,  # IDLE 表示正常完成
            "recommendation": final_recommendation,
            "geocode_results": self.geocode_results,
            "center_point": self.center_point,
            "search_results": self.search_results[:10],  # 限制返回数量
            "steps_executed": self.current_step,
            "raw_output": raw_result
        }


# 创建默认 Agent 实例的工厂函数
def create_meetspot_agent() -> MeetSpotAgent:
    """创建 MeetSpotAgent 实例

    Returns:
        配置好的 MeetSpotAgent 实例
    """
    return MeetSpotAgent()
