import time
from typing import TypedDict, Literal, Optional, Any, Sequence, Union
import discord
from discord import app_commands
from discord.ext import tasks, commands
from multiprocessing import Process
from queue import Queue
from threading import Thread
import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from discord.utils import MISSING


@dataclass
class AskResult:
    response: str
    author_id: int | None = None
    message_obj: "SentMessage | None" = None

@dataclass
class ButtonContext:
    interaction: discord.Interaction
    item: dict                       # the full item dict (label, custom_id, style, etc.)
    user_id: int
    view: "MyView"                   # gives access to view.message for editing

    @property
    def label(self) -> str | None:
        return self.item.get("label")

    @property
    def custom_id(self) -> str | None:
        return self.item.get("custom_id")

    @property
    def message_obj(self) -> discord.Message | None:
        return self.view.message


class SentMessage:
    def __init__(self, message_obj: discord.Message, bot: "DiscordBot"):
        self._message = message_obj
        self._bot = bot

    def edit(self, *,
        content: Any = MISSING,
        embed: Optional[discord.Embed] = MISSING,
        embeds: Sequence[discord.Embed] = MISSING,
        attachments: Sequence[Union[discord.Attachment, discord.File]] = MISSING,
        suppress: bool = False,
        delete_after: Optional[float] = None,
        allowed_mentions: Optional[discord.AllowedMentions] = MISSING,
        view: Optional[Union[discord.ui.View, discord.ui.LayoutView]] = MISSING,
    ) -> "SentMessage":
        if content is not MISSING and content is not None:
            content = str(content)
        async def _edit():
            return await self._message.edit(
                content=content, embed=embed, embeds=embeds, attachments=attachments,
                suppress=suppress, delete_after=delete_after,
                allowed_mentions=allowed_mentions, view=view,
            )
        future = asyncio.run_coroutine_threadsafe(_edit(), self._bot.client.loop)
        return SentMessage(future.result(), self._bot)

    def delete(self, *, delay: Optional[float] = None) -> None:
        async def _delete():
            return await self._message.delete(delay=delay)
        future = asyncio.run_coroutine_threadsafe(_delete(), self._bot.client.loop)
        return future.result()

    def add_reaction(self, emoji) -> None:
        async def _add():
            return await self._message.add_reaction(emoji)
        future = asyncio.run_coroutine_threadsafe(_add(), self._bot.client.loop)
        return future.result()

    def remove_reaction(self, emoji, member) -> None:
        async def _remove():
            return await self._message.remove_reaction(emoji, member)
        future = asyncio.run_coroutine_threadsafe(_remove(), self._bot.client.loop)
        return future.result()

    def clear_reaction(self, emoji) -> None:
        async def _clear():
            return await self._message.clear_reaction(emoji)
        future = asyncio.run_coroutine_threadsafe(_clear(), self._bot.client.loop)
        return future.result()

    def clear_reactions(self) -> None:
        async def _clear_all():
            return await self._message.clear_reactions()
        future = asyncio.run_coroutine_threadsafe(_clear_all(), self._bot.client.loop)
        return future.result()

    @property
    def id(self) -> int:
        return self._message.id

    @property
    def content(self) -> str:
        return self._message.content


def standerd_button_item(label: str, style: Literal[discord.ButtonStyle.primary, discord.ButtonStyle.secondary, discord.ButtonStyle.success, discord.ButtonStyle.danger], on_click: Callable | None = None, emoji: str | None = None, disabled: bool = False, custom_id: str | None = None,row: int | None = None) -> dict:
    return {
        "type": "button",
        "style": style,
        "label": label,
        "disabled": disabled,
        "custom_id": custom_id,
        "emoji": emoji,
        "row": row,
        "on_click": on_click,
        "exclusive": True,
    }

def link_button_item(label: str, url: str, emoji: str | None = None, disabled: bool = False, row: int | None = None):
    return {
        "type": "button",
        "style": discord.ButtonStyle.link,
        "label": label,
        "disabled": disabled,
        "url": url,
        "emoji": emoji,
        "row": row,
        "exclusive": True,
    }

def dropdown_item():
    pass

class MyView(discord.ui.View):
    def __init__(self, items: list[dict], timeout_seconds: int | None = None, bot=None):
        super().__init__(timeout=timeout_seconds)
        self.bot = bot  # reference back to DiscordBot, so callbacks can call handle_button_click
        self.items: list[dict] = items
        self.message: discord.Message | None = None
        self.generate_objects()

    def generate_objects(self):
        self.clear_items()
        for item in self.items:
            if item.get("type") == "button":
                button = discord.ui.Button(style=item.get("style", discord.ButtonStyle.secondary), label=item.get("label"), emoji=item.get("emoji"), custom_id=item.get("custom_id"), disabled=item.get("disabled", False), row=item.get("row"), )

                async def button_callback(interaction: discord.Interaction, item=item):
                    if item.get("exclusive") and self.bot.view_item_running:
                        await interaction.response.send_message("⚠️ This is already running, please wait.", ephemeral=True)
                        return

                    await interaction.response.defer()

                    async def respond(msg, view=None):
                        return await interaction.followup.send(msg, view=view)

                    ctx = ButtonContext(interaction=interaction, item=item, user_id=interaction.user.id, view=self)

                    if item.get("exclusive"):
                        self.bot.view_item_running = True

                    self.bot.view_item_response["bool"] = True
                    self.bot.view_item_response["func"] = respond

                    await asyncio.to_thread(self.bot.handle_button_click, ctx)

                    self.bot.view_item_response["bool"] = False

                    if item.get("exclusive"):
                        self.bot.view_item_running = False

                button.callback = button_callback
                self.add_item(button)
            elif item.get("type") == "dropdown":
                pass


class DiscordBot:
    def __init__(self, token, channel_or_person_id, is_dm=False, print_bot_data=True):
        self.token = token
        if is_dm:
            self.user_id = channel_or_person_id
        else:
            self.channel_id = channel_or_person_id
        self.is_dm = is_dm
        self.msg_queue = Queue()
        self.response_queue = Queue()
        self.return_message_obj = []
        self.previous_message_obj: discord.Message | None = None
        self.user_response = ""
        self.msg_text_payload = "text"
        self.msg_img_payload = "img"
        self.bot_on = False
        self.print_bot_data = print_bot_data
        self.discord_max_char_limit = 2000

        self.client = discord.Client(intents=discord.Intents.all())
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.view_item_response = {"bool": False, "func": None}
        self.view_item_running = False

        if not self.is_dm:
            self.guild_id = None
            self.tree = app_commands.CommandTree(self.client)
            self.command_response = {"bool": False, "func": None, "replied": False}
            self.command_running = False

    async def on_ready(self):
        if self.print_bot_data:
            print(f'Logged in as {self.client.user.name}')
        if self.is_dm:
            self.user = await self.client.fetch_user(self.user_id)
        else:
            self.channel = await self.client.fetch_channel(self.channel_id)
            if self.guild_id is None:
                self.guild_id = self.channel.guild.id
        self.my_background_task.start()
        self.bot_on = True

    async def on_message(self, message):
        if message.author == self.client.user:
            return False
        if self.is_dm:
            if message.author != self.user:
                return False
        if self.print_bot_data:
            print(f"Received: {message.content} {type(message.content)}")
        self.response_queue.put(f"{str(message.content)}:{message.author.id}")

    @tasks.loop(seconds=0.1)
    async def my_background_task(self):
        if not self.msg_queue.empty():
            payload = self.msg_queue.get()

            msg_type = payload["type"]

            if msg_type == self.msg_text_payload:
                message = [payload["content"]]
                if self.msg_queue.qsize() > 3 and payload["view"] is None:
                    return_to_queue = []
                    while not self.msg_queue.empty():
                        new_payload = self.msg_queue.get()
                        if new_payload["type"] != self.msg_text_payload:
                            return_to_queue.append(new_payload)
                        else:
                            message.append(f"{new_payload['content']}")

                    for i in return_to_queue:
                        self.msg_queue.put(i)

                message = self.split_by_char_limit(message)
                view = payload["view"]
                message_obj = None
                self.return_message_obj.clear()

                for item_list in message:
                    msg = "\n".join(item_list)

                    # Is OR Isn't DM
                    if self.view_item_response["bool"]:
                        message_obj = await self.view_item_response["func"](msg, view=view)
                    elif self.is_dm:
                        message_obj = await self.user.send(msg, view=view)

                    # Is Not DM
                    elif self.command_response["bool"]:
                        message_obj = await self.command_response["func"](msg, view=view)
                        self.command_response["bool"] = False
                        self.command_response["replied"] = True
                    else:
                        message_obj = await self.channel.send(msg, view=view)

                    if view is not None and hasattr(view, "message"):
                        view.message = message_obj

                self.return_message_obj.append(message_obj)

            elif msg_type == self.msg_img_payload:
                if self.is_dm:
                    await self.user.send(content=payload.get("caption"), file=discord.File(payload["path"]))
                else:
                    await self.channel.send(content=payload.get("caption"), file=discord.File(payload["path"]))

    def split_by_char_limit(self, items, headroom=100):
        """
        Splits a list of strings into multiple chunks such that the total
        character count of each chunk does not exceed (max_chars - headroom).

        - If an individual item exceeds the limit, it is split into safe-sized parts.
        - Returns a list of lists of strings.

        Parameters
        ----------
        items : list[str]
            List of string items to chunk.

        max_chars : int
            Maximum allowed characters per chunk (e.g. Discord limit).

        headroom : int
            Safety buffer to leave unused.

        Returns
        -------
        list[list[str]]
            Chunked list of string lists.
        """
        max_chars = self.discord_max_char_limit
        safe_limit = max_chars - headroom
        chunks = []
        current_chunk = []
        current_len = 0

        def flush_chunk():
            nonlocal current_chunk, current_len
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_len = 0

        for item in items:
            if not item:
                continue

            item = str(item)
            item_len = len(item)

            # Case 1: item itself is too large → split it
            if item_len > safe_limit:
                flush_chunk()
                start = 0
                while start < item_len:
                    part = item[start:start + safe_limit]
                    chunks.append([part])
                    start += safe_limit
                continue

            # Case 2: item fits, but not in current chunk
            if current_len + item_len > safe_limit:
                flush_chunk()

            current_chunk.append(item)
            current_len += item_len

        flush_chunk()
        return chunks

    def run_process(self):
        self.client.run(self.token)

    def start_bot(self):  # main function to start the bot
        self.p = Thread(target=self.run_process, daemon=True)
        self.p.start()

    def set_command(self, name, description, exclusive=False):
        safe_name = name.lower().replace(" ", "-")

        def decorator(handler):
            import inspect
            handler_params = inspect.signature(handler).parameters

            # Params we inject ourselves — not exposed to Discord
            injected = {"user_id", "respond"}
            discord_params = {k: v for k, v in handler_params.items() if k not in injected}

            async def wrapped(interaction: discord.Interaction, **discord_kwargs):
                await interaction.response.defer()

                # Start with the Discord-provided params, then inject ours
                kwargs = dict(discord_kwargs)
                if "user_id" in handler_params:
                    kwargs["user_id"] = interaction.user.id

                async def respond(message):
                    await interaction.followup.send(message)

                if exclusive and self.command_running:
                    await interaction.followup.send("⚠️ A command is already running, please wait.", ephemeral=True)
                    return

                if exclusive:
                    self.command_running = True

                self.command_response["bool"] = True
                self.command_response["func"] = respond

                def run_handler():
                    import asyncio as _asyncio
                    _asyncio.run(handler(**kwargs))

                await asyncio.to_thread(run_handler)

                if exclusive:
                    self.command_running = False

                if self.command_response["replied"]:
                    self.command_response["replied"] = False
                else:
                    await interaction.followup.send("✓", ephemeral=True)

            # Give wrapped the same signature discord.py needs to see
            new_sig_params = [
                inspect.Parameter("interaction", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=discord.Interaction)
            ] + list(discord_params.values())
            wrapped.__signature__ = inspect.Signature(new_sig_params)

            self.tree.command(name=safe_name, description=description)(wrapped)
            return handler

        return decorator

    def update_commands(self):
        if self.is_dm:
            raise TypeError("Can not set commands when bot is type DM")

        while not self.bot_on:
            pass

        guild_obj = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild_obj)
        future = asyncio.run_coroutine_threadsafe(self.tree.sync(guild=guild_obj), self.client.loop)
        synced = future.result()  # blocks until done, raises any errors
        print(f"Synced {len(synced)} command(s) to guild {self.guild_id}")

    def create_view(self, items: list[dict], timeout_seconds: int | None = None):
        async def _build():
            return MyView(items, timeout_seconds, bot=self)

        future = asyncio.run_coroutine_threadsafe(_build(), self.client.loop)
        return future.result()

    def handle_button_click(self, ctx: ButtonContext):
        if ctx.item.get("on_click"):
            ctx.item["on_click"](ctx)
        else:
            self.say(f"Button clicked: <@{ctx.user_id}>, {ctx.label}")
        # await interaction.response.send_message(f"Button clicked: {button.custom_id, button.label}", ephemeral=True)


    def say(self, message, return_message_obj: bool = False, *, view: discord.ui.View | None = None) -> SentMessage | None:

        if not message or not str(message).strip():
            return None

        self.return_message_obj.clear()

        self.msg_queue.put({"type": self.msg_text_payload, "content": str(message), "view": view})

        if not self.is_dm:
            while self.command_response["bool"]:
                time.sleep(0.01)

        if not return_message_obj:
            return None

        while len(self.return_message_obj) < 1:
            time.sleep(0.1)

        self.previous_message_obj = SentMessage(self.return_message_obj.pop(), self)
        return self.previous_message_obj

    def send_image(self, image_path, caption=None):
        self.msg_queue.put({"type": self.msg_img_payload, "path": image_path, "caption": caption})

    def ask(self, message: str, timeout: bool | None = None, return_message_author: bool = False, return_message_obj: bool = False, *, view: MyView | None = None) -> AskResult | str | None:
        """
        Sends a message and waits for a response.

        Args:
            message: The message to send
            timeout: The time to wait before moving on and returning None
            return_message_author: If True, also returns the responding user's Discord ID
            return_message_obj: If True, also returns the sent question as a SentMessage

        Returns:
            If neither flag is set: just the response string (or None on timeout).
            If either flag is set: an AskResult with .response, .author_id, .message_obj.
        """

        while not self.response_queue.empty():
            self.response_queue.get(block=False)

        get_obj = return_message_obj

        if view is not None:
            def ask_func(ctx: ButtonContext):
                self.response_queue.put(f"{ctx.label}:{ctx.user_id}")

            for item in view.items:
                item.update({"on_click": ask_func})

            get_obj = True

        message_obj = self.say(message, return_message_obj=get_obj, view=view)

        try:
            if timeout is None:
                raw = str(self.response_queue.get())
            else:
                raw = str(self.response_queue.get(timeout=float(timeout)))
        except Exception:
            return None

        if view is not None:
            for item in view.items:
                item.update({"disabled": True})
            view.generate_objects()
            message_obj.edit(view=view)

        response, author_id_str = raw.rsplit(":", 1)

        if not return_message_author and not return_message_obj:
            return response

        return AskResult(response=response, author_id=int(author_id_str) if return_message_author else None, message_obj=message_obj if return_message_obj else None)


