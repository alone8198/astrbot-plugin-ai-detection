"""
AI检测插件 - AstrBot
=============================
检测用户输入和AI输出中的违规内容，支持黑名单机制和消息撤回。

功能:
    - 关键词预过滤（无需调用AI，速度快）
    - AI模型检测（可指定检测模型，从AstrBot已启用的模型中选择）
    - 检测用户输入 → 拦截 + 提示 + 记录违规
    - 检测AI输出 → 替换为简洁原因
    - 黑名单机制（多次违规自动加入，无法再使用AI）
    - 消息撤回（如果机器人有管理权限）
    - 管理员指令管理黑名单
"""

import json
from pathlib import Path
from typing import Dict, Set

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig
from astrbot.core.utils.io import get_astrbot_data_path


@register(
    "ai_detection_plugin",
    "alone8198",
    "检测用户输入和AI输出中的违规内容，支持黑名单机制和消息撤回",
    "1.0.0",
    "https://github.com/alone8198/astrbot_plugin_ai_detection",
)
class AIDetectionPlugin(Star):
    """AI内容检测插件 - 在LLM请求前和响应后两级拦截违规内容。"""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

        # 防递归标志：避免检测时再次触发自身钩子
        self._detecting = False

        # ---- 数据持久化 ----
        self.data_dir = (
            Path(get_astrbot_data_path())
            / "plugin_data"
            / self.meta.name
            / "ai_detection"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.blacklist_file = self.data_dir / "blacklist.json"
        self.violations_file = self.data_dir / "violations.json"

        self.blacklist: Set[str] = set()
        self.violations: Dict[str, int] = {}

        self._load_data()

        logger.info(
            f"[AI检测] 插件已加载 | "
            f"黑名单: {len(self.blacklist)}人 | "
            f"违规记录: {len(self.violations)}条 | "
            f"检测模型: {self.config.get('detection_provider', '未设置')} | "
            f"撤回消息: {'开启' if self.config.get('enable_recall') else '关闭'} | "
            f"检测用户输入: {'开启' if self.config.get('detect_user_input', True) else '关闭'} | "
            f"检测AI输出: {'开启' if self.config.get('detect_ai_output', True) else '关闭'}"
        )

    # ==========================================
    #  数据持久化
    # ==========================================

    def _load_data(self):
        """加载黑名单和违规记录。"""
        try:
            if self.blacklist_file.exists():
                self.blacklist = set(json.loads(self.blacklist_file.read_text(encoding="utf-8")))
            if self.violations_file.exists():
                self.violations = json.loads(self.violations_file.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"[AI检测] 加载数据失败: {e}")

    def _save_blacklist(self):
        self.blacklist_file.write_text(
            json.dumps(sorted(self.blacklist), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_violations(self):
        self.violations_file.write_text(
            json.dumps(self.violations, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ==========================================
    #  核心检测逻辑
    # ==========================================

    def _check_keywords(self, text: str) -> bool:
        """
        关键词预过滤。
        命中关键词直接判定为违规，无需调用AI检测，速度快。
        """
        raw = self.config.get("keyword_filter", "")
        if not raw:
            return False
        for kw in (k.strip() for k in raw.split(",") if k.strip()):
            if kw and kw in text:
                logger.info(f"[AI检测] 关键词命中: [{kw}]")
                return True
        return False

    async def _detect_via_llm(self, text: str) -> bool:
        """
        调用AI模型检测内容是否违规。
        使用配置中选择的检测模型。

        Returns:
            True 表示违规，False 表示正常。
        """
        provider_id = self.config.get("detection_provider", "")

        detection_prompt = self.config.get("detection_prompt", "")
        if not detection_prompt or "{content}" not in detection_prompt:
            detection_prompt = (
                "你是一个严格的内容安全检测助手。请判断以下消息是否包含违规内容"
                "（色情、暴力、政治敏感、违法信息、人身攻击、广告垃圾等）。"
                "如果违规，仅回复【违规】；如果正常，仅回复【正常】。\n\n"
                "消息：\n{content}"
            )

        prompt = detection_prompt.replace("{content}", text)

        try:
            self._detecting = True

            if not provider_id:
                # 未指定检测模型时，使用当前对话使用的模型
                provider_id = await self.context.get_current_chat_provider_id()
                logger.info(f"[AI检测] 使用当前对话模型: {provider_id}")

            response = await self.context.llm_generate(provider_id, prompt)

            # 统一处理各种响应格式
            result_text = ""
            if isinstance(response, str):
                result_text = response
            elif hasattr(response, "response"):
                result_text = response.response
            elif isinstance(response, dict):
                result_text = response.get("content", "") or response.get("response", "")
            else:
                result_text = str(response)

            is_bad = "违规" in result_text and "正常" not in result_text
            logger.info(
                f"[AI检测] 模型判定: {'违规' if is_bad else '正常'} | "
                f"原文: {result_text[:60]}"
            )
            return is_bad

        except Exception as e:
            logger.error(f"[AI检测] 调用检测模型失败: {e}")
            return False
        finally:
            self._detecting = False

    def _is_blacklisted(self, sender_id: str) -> bool:
        """检查用户是否已被加入黑名单。"""
        return sender_id in self.blacklist

    def _add_violation(self, sender_id: str) -> int:
        """
        增加用户的违规计数。
        达到阈值后自动加入黑名单。

        Returns:
            当前违规总次数。
        """
        count = self.violations.get(sender_id, 0) + 1
        self.violations[sender_id] = count
        self._save_violations()

        max_v = int(self.config.get("max_violations", 3))
        if count >= max_v:
            self.blacklist.add(sender_id)
            self._save_blacklist()
            logger.warning(
                f"[AI检测] 用户 {sender_id} 违规已达 {count} 次，已加入黑名单"
            )

        return count

    # ==========================================
    #  消息撤回（需要机器人管理权限）
    # ==========================================

    async def _recall_message(self, event: AstrMessageEvent):
        """
        尝试撤回用户发送的违规消息。
        目前支持: aiocqhttp (QQ OneBot v11)
        """
        if not self.config.get("enable_recall", False):
            return

        try:
            if not hasattr(event, "message_obj") or not hasattr(event.message_obj, "message_id"):
                logger.debug("[AI检测] 消息对象无 message_id，无法撤回")
                return

            platform_name = event.get_platform_name()
            message_id = event.message_obj.message_id

            if platform_name == "aiocqhttp":
                client = event.bot
                await client.api.call_action("delete_msg", message_id=message_id)
                logger.info(f"[AI检测] 已撤回消息 {message_id} (aiocqhttp)")

            elif platform_name == "qqofficial":
                logger.info("[AI检测] QQ官方API消息撤回待实现")

            else:
                logger.info(f"[AI检测] 平台 {platform_name} 暂不支持消息撤回")

        except Exception as e:
            logger.error(f"[AI检测] 撤回消息失败: {e}")

    # ==========================================
    #  钩子: 检测用户输入 (LLM请求前)
    # ==========================================

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req):
        """
        在 LLM 处理用户消息之前触发。
        如果用户输入违规:
            - 发送拦截提示
            - 记入违规次数
            - （可选）撤回消息
            - 停止事件传播，阻止 AI 处理
        """
        # 跳过自身发起的检测调用，防止递归
        if self._detecting:
            return

        # 如果关闭了用户输入检测，跳过
        if not self.config.get("detect_user_input", True):
            return

        sender_id = event.get_sender_id()

        # ---- 黑名单拦截 ----
        if self._is_blacklisted(sender_id):
            blacklist_msg = self.config.get(
                "blacklist_message",
                "⛔ 您已被加入黑名单，无法使用AI功能。请联系管理员处理。",
            )
            await event.send(event.plain_result(blacklist_msg))
            event.stop_event()
            return

        user_text = event.message_str
        if not user_text:
            return

        # ---- 第一关：关键词预过滤 ----
        is_bad = self._check_keywords(user_text)

        # ---- 第二关：AI智能检测 ----
        if not is_bad and self.config.get("detection_provider", ""):
            is_bad = await self._detect_via_llm(user_text)

        if not is_bad:
            return

        # ---- 违规处理流程 ----
        count = self._add_violation(sender_id)
        max_v = int(self.config.get("max_violations", 3))

        # 发送拦截通知
        tmpl = self.config.get(
            "block_message",
            "⚠️ 您的消息包含违规内容，已被拦截。违规次数: {count}/{max}",
        )
        await event.send(
            event.plain_result(tmpl.replace("{count}", str(count)).replace("{max}", str(max_v)))
        )

        # 如果达到黑名单阈值，追加通知
        if count >= max_v:
            await event.send(
                event.plain_result(
                    self.config.get(
                        "blacklist_message",
                        "⛔ 您已被加入黑名单，无法使用AI功能。请联系管理员处理。",
                    )
                )
            )

        # 尝试撤回用户的原消息
        await self._recall_message(event)

        # 停止事件传播，阻止后续的 LLM 调用
        event.stop_event()

    # ==========================================
    #  钩子: 检测AI输出 (LLM响应后)
    # ==========================================

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp):
        """
        在 LLM 生成回复后、发送给用户前触发。
        如果 AI 输出违规:
            - 将回应内容替换为简洁的拦截说明
        """
        if self._detecting:
            return

        if not self.config.get("detect_ai_output", True):
            return

        # 获取 AI 输出内容
        content = ""
        if hasattr(resp, "response"):
            content = str(resp.response)
        elif hasattr(resp, "content"):
            content = str(resp.content)

        if not content:
            return

        # ---- 两级检测 ----
        is_bad = self._check_keywords(content)
        if not is_bad and self.config.get("detection_provider", ""):
            is_bad = await self._detect_via_llm(content)

        if is_bad:
            replace_msg = self.config.get(
                "replace_message",
                "⚠️ 该回复因包含不良内容已被拦截替换",
            )

            if hasattr(resp, "response"):
                resp.response = replace_msg
            if hasattr(resp, "content"):
                resp.content = replace_msg

            logger.warning(f"[AI检测] AI输出已被拦截替换: {content[:80]}...")

    # ==========================================
    #  管理指令
    # ==========================================

    @filter.command("检测黑名单")
    async def cmd_blacklist(self, event: AstrMessageEvent):
        """查看黑名单列表"""
        if not self.blacklist:
            yield event.plain_result("📋 当前黑名单为空")
            return

        lines = [f"📋 黑名单 ({len(self.blacklist)} 人):"]
        for uid in sorted(self.blacklist):
            lines.append(f"  • {uid}（违规 {self.violations.get(uid, 0)} 次）")
        yield event.plain_result("\n".join(lines))

    @filter.command("移出黑名单")
    async def cmd_unban(self, event: AstrMessageEvent):
        """移出黑名单\n用法: /移出黑名单 <用户ID>"""
        parts = event.message_str.strip().split(maxsplit=1)
        if len(parts) < 2:
            yield event.plain_result("❌ 用法: /移出黑名单 <用户ID>")
            return

        uid = parts[1].strip()
        if uid not in self.blacklist:
            yield event.plain_result(f"❌ 用户 {uid} 不在黑名单中")
            return

        self.blacklist.remove(uid)
        self._save_blacklist()
        self.violations.pop(uid, None)
        self._save_violations()
        yield event.plain_result(f"✅ 已将 {uid} 移出黑名单并重置违规计数")

    @filter.command("清空违规")
    async def cmd_clear(self, event: AstrMessageEvent):
        """清空所有违规记录和黑名单"""
        self.blacklist.clear()
        self.violations.clear()
        self._save_blacklist()
        self._save_violations()
        yield event.plain_result("✅ 已清空所有违规记录和黑名单")

    @filter.command("检测统计")
    async def cmd_stats(self, event: AstrMessageEvent):
        """查看检测统计信息"""
        total = len(self.violations)
        blacklisted = len(self.blacklist)
        top = sorted(self.violations.items(), key=lambda x: -x[1])[:5]

        lines = [
            "📊 AI检测统计",
            f"  总违规用户: {total}",
            f"  当前黑名单: {blacklisted}",
        ]
        if top:
            lines.append("  违规最多的用户:")
            for uid, c in top:
                lines.append(f"    • {uid}: {c} 次")
        yield event.plain_result("\n".join(lines))

    # ==========================================
    #  清理
    # ==========================================

    async def terminate(self):
        """插件卸载/停用时调用。"""
        logger.info("[AI检测] 插件已卸载")
