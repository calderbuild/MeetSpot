"""Agent 基类 - 参考 OpenManus BaseAgent 设计"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message, ROLE_TYPE


class BaseAgent(BaseModel, ABC):
    """Agent 基类

    提供基础的状态管理、记忆管理和执行循环。
    子类需要实现 step() 方法来定义具体行为。
    """

    # 核心属性
    name: str = Field(default="BaseAgent", description="Agent 名称")
    description: Optional[str] = Field(default=None, description="Agent 描述")

    # 提示词
    system_prompt: Optional[str] = Field(default=None, description="系统提示词")
    next_step_prompt: Optional[str] = Field(default=None, description="下一步提示词")

    # 依赖
    llm: Optional[LLM] = Field(default=None, description="LLM 实例")
    memory: Memory = Field(default_factory=Memory, description="Agent 记忆")
    state: AgentState = Field(default=AgentState.IDLE, description="当前状态")

    # 执行控制
    max_steps: int = Field(default=10, description="最大执行步数")
    current_step: int = Field(default=0, description="当前步数")

    # 重复检测阈值
    duplicate_threshold: int = 2

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """初始化 Agent"""
        if self.llm is None:
            try:
                self.llm = LLM()
            except Exception as e:
                logger.warning(f"无法初始化 LLM: {e}")
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """状态上下文管理器，用于安全的状态转换"""
        if not isinstance(new_state, AgentState):
            raise ValueError(f"无效状态: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR
            raise e
        finally:
            self.state = previous_state

    def update_memory(
        self,
        role: ROLE_TYPE,
        content: str,
        base64_image: Optional[str] = None,
        **kwargs,
    ) -> None:
        """添加消息到记忆"""
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"不支持的消息角色: {role}")

        if role == "tool":
            self.memory.add_message(message_map[role](content, **kwargs))
        else:
            self.memory.add_message(message_map[role](content, base64_image=base64_image))

    async def run(self, request: Optional[str] = None) -> str:
        """执行 Agent 主循环

        Args:
            request: 可选的初始用户请求

        Returns:
            执行结果摘要
        """
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"无法从状态 {self.state} 启动 Agent")

        if request:
            self.update_memory("user", request)

        results: List[str] = []
        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps
                and self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"执行步骤 {self.current_step}/{self.max_steps}")
                step_result = await self.step()

                # 检测卡住状态
                if self.is_stuck():
                    self.handle_stuck_state()

                results.append(f"Step {self.current_step}: {step_result}")

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"已终止: 达到最大步数 ({self.max_steps})")

        return "\n".join(results) if results else "未执行任何步骤"

    @abstractmethod
    async def step(self) -> str:
        """执行单步操作 - 子类必须实现"""
        pass

    def handle_stuck_state(self):
        """处理卡住状态"""
        stuck_prompt = "检测到重复响应。请考虑新策略，避免重复已尝试过的无效路径。"
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt or ''}"
        logger.warning("Agent 检测到卡住状态，已添加提示")

    def is_stuck(self) -> bool:
        """检测是否陷入循环"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # 统计相同内容出现次数
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """获取记忆中的消息列表"""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """设置记忆中的消息列表"""
        self.memory.messages = value
