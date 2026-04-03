import time

import discord
from discord import app_commands
from discord.ext import tasks
from multiprocessing import Process, Queue
from threading import Thread
import asyncio


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
        self.user_response = ""
        self.msg_text_payload = "text"
        self.msg_img_payload = "img"
        self.bot_on = False
        self.print_bot_data = print_bot_data
        self.discord_max_char_limit = 2000

        self.client = discord.Client(intents=discord.Intents.all())
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

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
                if self.msg_queue.qsize() > 3:
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

                for item_list in message:
                    msg = "\n".join(item_list)
                    if self.is_dm:
                        await self.user.send(msg)
                    elif self.command_response["bool"]:
                        await self.command_response["func"](msg)
                        self.command_response["bool"] = False
                        self.command_response["replied"] = True
                    else:
                        await self.channel.send(msg)

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

    def say(self, message):
        if not message or not str(message).strip():
            return
        self.msg_queue.put({"type": self.msg_text_payload, "content": message})

        if not self.is_dm:
            while self.command_response["bool"]:
                time.sleep(0.01)


    def send_image(self, image_path, caption=None):
        self.msg_queue.put({"type": self.msg_img_payload, "path": image_path, "caption": caption})

    def ask(self, message, timeout=None, return_message_author=False):
        """
        Sends a message and waits for a response.

        timeout:
        - None  -> wait forever
        - float -> wait up to that many seconds, then return None
        """

        while not self.response_queue.empty():
            self.response_queue.get(block=False)

        self.say(message)

        if timeout is None:
            user_response = str(self.response_queue.get()).rsplit(":", 1)
            if return_message_author:
                return user_response[0], int(user_response[1])
            else:
                return user_response[0]

        try:
            user_response = str(self.response_queue.get(timeout=float(timeout))).rsplit(":", 1)
            if return_message_author:
                return user_response[0], int(user_response[1])
            else:
                return user_response[0]
        except Exception:
            return None

