import discord
from discord.ext import tasks
from multiprocessing import Process, Queue


class DiscordBot:
    def __init__(self, token, channel_id):
        self.token = token
        self.channel_id = channel_id
        self.msg_queue = Queue()
        self.response_queue = Queue()
        self.user_response = ""
        self.msg_text_payload = "text"
        self.msg_img_payload = "img"

    async def on_ready(self):
        print(f'Logged in as {self.client.user.name}')
        self.channel = self.client.get_channel(self.channel_id)
        self.my_background_task.start()

    async def on_message(self, message):
        if message.author == self.client.user:
            return False
        print(f"Received: {message.content} {type(message.content)}")
        self.response_queue.put(str(message.content))

    @tasks.loop(seconds=0.1)
    async def my_background_task(self):
        if not self.msg_queue.empty():
            payload = self.msg_queue.get()

            msg_type = payload["type"]

            if msg_type == self.msg_text_payload:
                await self.channel.send(payload["content"])

            elif msg_type == self.msg_img_payload:
                await self.channel.send(content=payload.get("caption"), file=discord.File(payload["path"]))


    def run_process(self):
        self.client = discord.Client(intents=discord.Intents.all())

        self.client.event(self.on_ready)
        self.client.event(self.on_message)

        self.client.run(self.token)

    def start_bot(self):
        self.p = Process(target=self.run_process)
        self.p.start()

    def say(self, message):
        if not message or not str(message).strip():
            return
        self.msg_queue.put({
            "type": self.msg_text_payload,
            "content": message
        })

    def send_image(self, image_path, caption=None):
        self.msg_queue.put({
            "type": self.msg_text_payload,
            "path": image_path,
            "caption": caption
        })

    def ask(self, message):
        while not self.response_queue.empty():
            self.response_queue.get(block=False)

        self.say(message)

        return self.response_queue.get()
