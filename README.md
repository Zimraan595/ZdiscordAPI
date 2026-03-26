# ZdiscordAPI

A simple Python abstraction layer for Discord bots. Write Discord bots without touching `discord.py` directly — just send messages, ask questions, receive replies, and register slash commands with clean, minimal code.

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Bot Modes](#bot-modes)
- [Constructor](#constructor)
- [Starting the Bot](#starting-the-bot)
- [Sending Messages](#sending-messages)
  - [say()](#say)
  - [send_image()](#send_image)
- [Receiving Messages](#receiving-messages)
  - [ask()](#ask)
- [Slash Commands](#slash-commands)
  - [set_command()](#set_command)
  - [update_commands()](#update_commands)
  - [Accessing the User ID](#accessing-the-user-id)
- [Notes & Tips](#notes--tips)

---

## Installation

This is a local editable package. Install it into your project's virtual environment once:

```bash
pip install -e "C:\Users\<you>\Documents\GitHub\ZdiscordAPI\discord_shared"
```

Then import it in any project:

```python
from discord_shared import DiscordBot
```

---

## Quick Start

```python
from discord_shared import DiscordBot

bot = DiscordBot(token="YOUR_BOT_TOKEN", channel_or_person_id=YOUR_CHANNEL_ID)
bot.start_bot()

bot.say("Hello, world!")
response = bot.ask("What is your name?")
print(f"User said: {response}")
```

---

## Bot Modes

`DiscordBot` supports two modes:

| Mode | Description |
|------|-------------|
| **Channel** (default) | Sends and receives messages in a specific server channel |
| **DM** | Sends and receives messages as a direct message to a specific user |

Set DM mode with `is_dm=True` and pass a **user ID** instead of a channel ID.

---

## Constructor

```python
DiscordBot(token, channel_or_person_id, is_dm=False, print_bot_data=True)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | `str` | Yes | Your Discord bot token |
| `channel_or_person_id` | `int` | Yes | Channel ID (default) or User ID (if `is_dm=True`) |
| `is_dm` | `bool` | No | Set to `True` to send/receive via DM instead of a channel. Default: `False` |
| `print_bot_data` | `bool` | No | Whether to print login info and received messages to the console. Default: `True` |

**Channel mode:**
```python
bot = DiscordBot(token="TOKEN", channel_or_person_id=1234567890)
```

**DM mode:**
```python
bot = DiscordBot(token="TOKEN", channel_or_person_id=9876543210, is_dm=True)
```

**Suppress console output:**
```python
bot = DiscordBot(token="TOKEN", channel_or_person_id=1234567890, print_bot_data=False)
```

---

## Starting the Bot

```python
bot.start_bot()
```

Starts the bot in a background thread. Your script continues running immediately — the bot connects to Discord asynchronously behind the scenes.

> You can check `bot.bot_on` to know when the bot has fully connected and is ready.

```python
import time
bot.start_bot()
while not bot.bot_on:
    time.sleep(0.1)
print("Bot is ready!")
```

---

## Sending Messages

### `say()`

Sends a text message to the configured channel or DM.

```python
bot.say(message)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `message` | `str` | The message to send. Supports Discord markdown. |

**Examples:**
```python
bot.say("Server is online!")
bot.say("## Big Header\n- bullet one\n- bullet two")  # Markdown supported
bot.say(f"Current status: **{status}**")
```

**Details:**
- Empty or whitespace-only messages are silently ignored
- Messages are queued and sent by a background loop — the call returns immediately
- If many messages are queued at once, they are **batched** into single Discord messages to reduce spam
- Discord's 2000 character limit is handled automatically — long messages are split across multiple sends

---

### `send_image()`

Sends an image file to the configured channel or DM, with an optional caption.

```python
bot.send_image(image_path, caption=None)
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `image_path` | `str` | Yes | Absolute or relative path to the image file |
| `caption` | `str` | No | Optional text to display above the image |

**Examples:**
```python
bot.send_image("screenshot.png")
bot.send_image("graph.png", caption="Here is today's performance graph:")
bot.send_image(r"C:\Users\me\charts\output.png", caption="**Report**")
```

---

## Receiving Messages

### `ask()`

Sends a message and **blocks until the user replies**, then returns the response.

```python
response = bot.ask(message, timeout=None, return_message_author=False)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | `str` | — | The question/message to send before waiting |
| `timeout` | `float` or `None` | `None` | Seconds to wait for a reply. `None` = wait forever. Returns `None` on timeout. |
| `return_message_author` | `bool` | `False` | If `True`, returns a tuple of `(message, author)` instead of just the message |

**Wait forever:**
```python
answer = bot.ask("Are you ready? (yes/no)")
```

**With a timeout:**
```python
answer = bot.ask("Reply within 30 seconds:", timeout=30)
if answer is None:
    print("No response received.")
```

**Get the author too:**
```python
message, author = bot.ask("Who wants to start?", return_message_author=True)
print(f"{author} said: {message}")
```

**Details:**
- Any pending unread messages in the queue are **cleared** before sending, so only a fresh reply is returned
- In DM mode, only messages from the configured user are received
- In channel mode, messages from any user in the channel are received (excluding the bot itself)

---

## Slash Commands

Slash commands allow users to interact with the bot via Discord's `/command` interface.

> Slash commands are only available in **channel mode** (not DM mode).

### `set_command()`

A decorator that registers a slash command handler.

```python
@bot.set_command(name, description)
async def your_handler():
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The command name. Spaces are automatically converted to hyphens (e.g. `"server status"` → `/server-status`) |
| `description` | `str` | Short description shown in Discord's command picker |

**Basic command (no return value):**
```python
@bot.set_command("ping", "Check if the bot is alive")
async def ping_command():
    pass  # Sends an ephemeral "✓" to the user
```

**Command that sends a visible reply:**
```python
@bot.set_command("server status", "Get the current server status")
async def server_status_command():
    return f"The server is currently **{server_status}**"
```

**Return value behaviour:**

| Handler returns | What Discord shows |
|----------------|-------------------|
| A non-empty string | The string posted publicly in the channel |
| `None` / nothing | A silent `✓` visible only to the user who ran the command |

---

### Accessing the User ID

If your handler needs to know **who ran the command**, add a `user_id` parameter. It will be automatically injected — no other changes needed.

```python
@bot.set_command("claim", "Claim your reward")
async def claim_command(user_id):
    return f"<@{user_id}> claimed their reward!"  # Mentions the user
```

> `user_id` is the only special injected parameter. Any handler without it works exactly the same as before — you don't need to add it if you don't use it.

---

### `update_commands()`

Syncs all registered slash commands to Discord so they appear in the `/` menu.

```python
bot.update_commands()
```

**Rules:**
- Must be called **after** all `@set_command` decorators have been applied
- Blocks until the bot is fully connected (`bot_on == True`) before syncing
- Will raise `TypeError` if called on a DM-mode bot
- Commands are synced to the guild (server) the bot's channel belongs to — guild ID is resolved automatically

**Typical usage pattern:**

```python
bot.start_bot()

@bot.set_command("hello", "Say hello")
async def hello_command():
    return "Hello!"

@bot.set_command("status", "Get status")
async def status_command():
    return f"Status: {current_status}"

bot.update_commands()  # Push all commands to Discord
```

---

## Notes & Tips

**Discord character limit**
Messages longer than 2000 characters are automatically split and sent as multiple messages. You don't need to handle this yourself.

**Message batching**
If you call `say()` many times rapidly, the bot will batch consecutive text messages together into one Discord message to avoid spam. Image messages are never batched.

**Thread safety**
`say()`, `send_image()`, and `ask()` are all safe to call from any thread. The bot runs in a background daemon thread and communicates via queues.

**Slash command names**
Discord requires command names to be lowercase and contain only letters, numbers, hyphens, or underscores. Spaces in the `name` argument are automatically converted to hyphens.

**Slash command response time**
Discord requires a response within **3 seconds**. `set_command` handles this automatically by deferring the interaction immediately, giving your handler up to 15 minutes to complete.

**Guild ID**
The guild (server) ID is resolved automatically from the channel. You do not need to provide it manually.
