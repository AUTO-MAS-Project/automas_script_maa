#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2024-2025 DLmaster361
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

#   Contact: DLmaster_361@163.com

from typing import Any

from app.core import Config
from app.services import Notify
from app.utils import get_logger

from ...template_renderer import render_template

logger = get_logger("MAA 通知工具")


def _has_success(result: Any) -> bool:
    return isinstance(result, dict) and any(bool(ok) for ok in result.values())


async def _send_payload_with_notify(
    notify_service: Any | None,
    payload: dict[str, Any],
    channels: list[str] | None = None,
) -> bool:
    if notify_service is None or not callable(getattr(notify_service, "send_payload", None)):
        return False

    try:
        return _has_success(await notify_service.send_payload(payload, channels=channels))
    except Exception as exc:
        logger.warning(f"notify 服务发送失败，将回退旧通知实现: {type(exc).__name__}: {exc}")
        return False


async def _send_user_direct_with_notify(
    notify_service: Any | None,
    *,
    title: str,
    mail_html: str,
    serverchan_content: str,
    user_config: Any | None,
    channels: list[str] | None = None,
) -> None:
    if notify_service is None or user_config is None:
        return
    if not user_config.get("Notify", "Enabled"):
        return

    channel_selected = getattr(notify_service, "is_channel_selected", None)
    if not callable(channel_selected):
        return

    if user_config.get("Notify", "IfSendMail") and channel_selected(channels, "mail"):
        to_address = user_config.get("Notify", "ToAddress")
        if to_address and callable(getattr(notify_service, "send_mail", None)):
            try:
                await notify_service.send_mail(
                    mode="网页",
                    title=title,
                    content=mail_html,
                    to_address=to_address,
                )
            except Exception as exc:
                logger.warning(f"notify 用户邮件通知发送失败: {type(exc).__name__}: {exc}")
        elif not to_address:
            logger.error("用户邮箱地址为空, 无法发送用户单独的邮件通知")

    if user_config.get("Notify", "IfServerChan") and channel_selected(
        channels, "serverchan"
    ):
        send_key = user_config.get("Notify", "ServerChanKey")
        if send_key and callable(getattr(notify_service, "send_serverchan", None)):
            try:
                await notify_service.send_serverchan(
                    title=title,
                    content=serverchan_content,
                    send_key=send_key,
                )
            except Exception as exc:
                logger.warning(f"notify 用户 ServerChan 通知发送失败: {type(exc).__name__}: {exc}")
        elif not send_key:
            logger.error("用户ServerChan密钥为空, 无法发送用户单独的ServerChan通知")


async def _notify_should_send_task_result(notify_service: Any | None, message: dict[str, Any]) -> bool:
    checker = getattr(notify_service, "should_send_task_result", None)
    if callable(checker):
        return bool(await checker(message))
    return True


async def _notify_should_send_statistic(notify_service: Any | None) -> bool:
    checker = getattr(notify_service, "should_send_statistic", None)
    if callable(checker):
        return bool(await checker())
    return True


async def _notify_should_send_six_star(notify_service: Any | None) -> bool:
    checker = getattr(notify_service, "should_send_six_star", None)
    if callable(checker):
        return bool(await checker())
    return True


async def push_notification(
    mode: str,
    title: str,
    message: dict,
    user_config: Any | None,
    *,
    notify_service: Any | None = None,
    notify_channels: list[str] | None = None,
) -> None:
    """通过所有渠道推送通知"""

    logger.info(f"开始推送通知, 模式: {mode}, 标题: {title}")

    if mode == "代理结果" and (
        Config.get("Notify", "SendTaskResultTime") == "任何时刻"
        or (
            Config.get("Notify", "SendTaskResultTime") == "仅失败时"
            and message["uncompleted_count"] != 0
        )
    ):
        message_text = (
            f"任务开始时间: {message['start_time']}, 结束时间: {message['end_time']}\n"
            f"已完成数: {message['completed_count']}, 未完成数: {message['uncompleted_count']}\n\n"
            f"{message['result']}"
        )
        message_html = render_template("MAA_result.html", message)
        serverchan_message = message_text.replace("\n", "\n\n")
        if notify_service is not None:
            if not await _notify_should_send_task_result(notify_service, message):
                return
            sent = await _send_payload_with_notify(
                notify_service,
                {
                    "kind": "proxy_result",
                    "title": title,
                    "text": message_text,
                    "serverchan_content": f"{serverchan_message}\nAUTO-MAS 敬上",
                    "koishi_message": f"{title}\n\n{message_text}\nAUTO-MAS 敬上",
                    "mail_mode": "网页",
                    "mail_content": message_html,
                    "data": message,
                },
                channels=notify_channels,
            )
            if sent:
                return
            if notify_channels is not None:
                return

        if Config.get("Notify", "IfSendMail"):
            await Notify.send_mail(
                "网页", title, message_html, Config.get("Notify", "ToAddress")
            )
        if Config.get("Notify", "IfServerChan"):
            await Notify.ServerChanPush(
                title,
                f"{serverchan_message}\nAUTO-MAS 敬上",
                Config.get("Notify", "ServerChanKey"),
            )
        # 发送Koishi通知
        if Config.get("Notify", "IfKoishiSupport"):
            await Notify.send_koishi(f"{title}\n\n{message_text}\nAUTO-MAS 敬上")
    elif mode == "统计信息":
        formatted = []
        if "drop_statistics" in message:
            for stage, items in message["drop_statistics"].items():
                formatted.append(f"掉落统计（{stage}）:")
                for item, quantity in items.items():
                    formatted.append(f"  {item}: {quantity}")
        drop_text = "\n".join(formatted)
        formatted = ["招募统计:"]
        if "recruit_statistics" in message:
            for star, count in message["recruit_statistics"].items():
                formatted.append(f"  {star}: {count}")
        recruit_text = "\n".join(formatted)
        message_text = (
            f"开始时间: {message['start_time']}\n"
            f"结束时间: {message['end_time']}\n"
            f"理智剩余: {message.get('sanity', '未知')}\n"
            f"回复时间: {message.get('sanity_full_at', '未知')}\n"
            f"MAA执行结果: {message['maa_result']}\n"
            f"{recruit_text}\n"
            f"{drop_text}"
        )
        message_html = render_template("MAA_statistics.html", message)
        serverchan_message = message_text.replace("\n", "\n\n")
        if notify_service is not None:
            if not await _notify_should_send_statistic(notify_service):
                if (
                    user_config is not None
                    and user_config.get("Notify", "Enabled")
                    and user_config.get("Notify", "IfSendStatistic")
                ):
                    await _send_user_direct_with_notify(
                        notify_service,
                        title=title,
                        mail_html=message_html,
                        serverchan_content=f"{serverchan_message}\nAUTO-MAS 敬上",
                        user_config=user_config,
                        channels=notify_channels,
                    )
                return
            sent = await _send_payload_with_notify(
                notify_service,
                {
                    "kind": "statistic",
                    "title": title,
                    "text": message_text,
                    "serverchan_content": f"{serverchan_message}\nAUTO-MAS 敬上",
                    "koishi_message": f"{title}\n\n{message_text}\nAUTO-MAS 敬上",
                    "mail_mode": "网页",
                    "mail_content": message_html,
                    "data": message,
                },
                channels=notify_channels,
            )
            if sent:
                if (
                    user_config is not None
                    and user_config.get("Notify", "Enabled")
                    and user_config.get("Notify", "IfSendStatistic")
                ):
                    await _send_user_direct_with_notify(
                        notify_service,
                        title=title,
                        mail_html=message_html,
                        serverchan_content=f"{serverchan_message}\nAUTO-MAS 敬上",
                        user_config=user_config,
                        channels=notify_channels,
                    )
                return
            if notify_channels is not None:
                return

        if Config.get("Notify", "IfSendStatistic"):
            if Config.get("Notify", "IfSendMail"):
                await Notify.send_mail(
                    "网页", title, message_html, Config.get("Notify", "ToAddress")
                )
            if Config.get("Notify", "IfServerChan"):
                await Notify.ServerChanPush(
                    title,
                    f"{serverchan_message}\nAUTO-MAS 敬上",
                    Config.get("Notify", "ServerChanKey"),
                )
            # 发送Koishi通知
            if Config.get("Notify", "IfKoishiSupport"):
                await Notify.send_koishi(f"{title}\n\n{message_text}\nAUTO-MAS 敬上")
        if (
            user_config is not None
            and user_config.get("Notify", "Enabled")
            and user_config.get("Notify", "IfSendStatistic")
        ):
            if user_config.get("Notify", "IfSendMail"):
                if user_config.get("Notify", "ToAddress"):
                    await Notify.send_mail(
                        "网页",
                        title,
                        message_html,
                        user_config.get("Notify", "ToAddress"),
                    )
                else:
                    logger.error("用户邮箱地址为空, 无法发送用户单独的邮件通知")
            if user_config.get("Notify", "IfServerChan"):
                if user_config.get("Notify", "ServerChanKey"):
                    await Notify.ServerChanPush(
                        title,
                        f"{serverchan_message}\nAUTO-MAS 敬上",
                        user_config.get("Notify", "ServerChanKey"),
                    )
                else:
                    logger.error(
                        "用户ServerChan密钥为空, 无法发送用户单独的ServerChan通知"
                    )
    elif mode == "公招六星":
        message_html = render_template("MAA_six_star.html", message)
        if notify_service is not None:
            if not await _notify_should_send_six_star(notify_service):
                if (
                    user_config is not None
                    and user_config.get("Notify", "Enabled")
                    and user_config.get("Notify", "IfSendSixStar")
                ):
                    await _send_user_direct_with_notify(
                        notify_service,
                        title=title,
                        mail_html=message_html,
                        serverchan_content="好羡慕~\nAUTO-MAS 敬上",
                        user_config=user_config,
                        channels=notify_channels,
                    )
                return
            sent = await _send_payload_with_notify(
                notify_service,
                {
                    "kind": "six_star",
                    "title": title,
                    "text": "好羡慕~",
                    "serverchan_content": "好羡慕~\nAUTO-MAS 敬上",
                    "koishi_message": f"{title}\n\n好羡慕~\nAUTO-MAS 敬上",
                    "mail_mode": "网页",
                    "mail_content": message_html,
                    "data": message,
                },
                channels=notify_channels,
            )
            if sent:
                if (
                    user_config is not None
                    and user_config.get("Notify", "Enabled")
                    and user_config.get("Notify", "IfSendSixStar")
                ):
                    await _send_user_direct_with_notify(
                        notify_service,
                        title=title,
                        mail_html=message_html,
                        serverchan_content="好羡慕~\nAUTO-MAS 敬上",
                        user_config=user_config,
                        channels=notify_channels,
                    )
                return
            if notify_channels is not None:
                return

        if Config.get("Notify", "IfSendSixStar"):
            if Config.get("Notify", "IfSendMail"):
                await Notify.send_mail(
                    "网页", title, message_html, Config.get("Notify", "ToAddress")
                )
            if Config.get("Notify", "IfServerChan"):
                await Notify.ServerChanPush(
                    title,
                    "好羡慕~\nAUTO-MAS 敬上",
                    Config.get("Notify", "ServerChanKey"),
                )
            # 发送Koishi通知
            if Config.get("Notify", "IfKoishiSupport"):
                await Notify.send_koishi(f"{title}\n\n好羡慕~\nAUTO-MAS 敬上")
        if (
            user_config is not None
            and user_config.get("Notify", "Enabled")
            and user_config.get("Notify", "IfSendSixStar")
        ):
            if user_config.get("Notify", "IfSendMail"):
                if user_config.get("Notify", "ToAddress"):
                    await Notify.send_mail(
                        "网页",
                        title,
                        message_html,
                        user_config.get("Notify", "ToAddress"),
                    )
                else:
                    logger.error("用户邮箱地址为空, 无法发送用户单独的邮件通知")
            if user_config.get("Notify", "IfServerChan"):
                if user_config.get("Notify", "ServerChanKey"):
                    await Notify.ServerChanPush(
                        title,
                        "好羡慕~\nAUTO-MAS 敬上",
                        user_config.get("Notify", "ServerChanKey"),
                    )
                else:
                    logger.error(
                        "用户ServerChan密钥为空, 无法发送用户单独的ServerChan通知"
                    )
