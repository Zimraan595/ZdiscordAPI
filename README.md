# ZdiscordAPI

A simple Python abstraction layer for Discord bots. Write Discord bots without touching `discord.py` directly — just send messages, ask questions, receive replies, register slash commands, and add interactive buttons with clean, minimal code.

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
- [Message Objects](#message-objects)
  - [SentMessage](#sentmessage)
- [Receiving Messages](#receiving-messages)
  - [ask()](#ask)
  - [AskResult](#askresult)
- [Buttons & Views](#buttons--views)
  - [Creating Buttons](#creating-buttons)
  - [create_view()](#create_view)
  - [Button Callbacks (on_click)](#button-callbacks-on_click)
  - [ButtonContext](#buttoncontext)
  - [Asking with Buttons](#asking-with-buttons)
  - [Exclusive Buttons](#exclusive-buttons)
  - [Dropdowns (Work in Progress)](#dropdowns-work-in-progress)
- [Slash Commands](#slash-commands)
  - [set_command()](#set_command)
  - [Responding from a Command](#responding-from-a-command)
  - [Accessing the User ID](#accessing-the-user-id)
  - [update_commands()](#update_commands)
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
bot.say(message, return_message_obj=False, *, view=None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | any | — | The message to send. Anything convertible with `str()` works (strings, ints, etc.). Supports Discord markdown. |
| `return_message_obj` | `bool` | `False` | If `True`, blocks until the message is actually sent, then returns a [`SentMessage`](#sentmessage) you can later edit, delete, or react to. |
| `view` | `MyView` or `None` | `None` | Keyword-only. A view created with [`create_view()`](#create_view) to attach buttons to the message. |

**Fire-and-forget (default, fast):**
```python
bot.say("Server is online!")
bot.say("## Big Header\n- bullet one\n- bullet two")  # Markdown supported
bot.say(f"Current status: **{status}**")
```

**Get the message object back so you can edit it later:**
```python
countdown = bot.say("Countdown", return_message_obj=True)
for i in range(5):
    countdown.edit(content=f"{5 - i}")
    time.sleep(1)
countdown.delete()
```

**Attach buttons:**
```python
view = bot.create_view([
    zdiscord_api.standerd_button_item("Approve", discord.ButtonStyle.green),
    zdiscord_api.standerd_button_item("Deny", discord.ButtonStyle.red),
])
bot.say("New request received", view=view)
```

**Details:**
- Empty or whitespace-only messages are silently ignored
- With `return_message_obj=False` (the default), messages are queued and sent by a background loop — the call returns immediately. If many messages are queued at once, they are **batched** into single Discord messages to reduce spam. This makes the default mode suitable for very fast logging.
- With `return_message_obj=True`, the call **blocks** until the message is actually sent — so batching does not apply to that call. Only request the message object when you actually plan to use it.
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

## Message Objects

### `SentMessage`

Returned by `say(..., return_message_obj=True)` (and inside [`AskResult`](#askresult)). Wraps a sent Discord message and gives you thread-safe methods to act on it later — from any thread, without touching `discord.py` or `async` yourself.

**Methods:**

| Method | Description |
|--------|-------------|
| `edit(...)` | Edits the message. Returns a **new** `SentMessage` for the edited message (chainable). |
| `delete(*, delay=None)` | Deletes the message. Optional `delay` in seconds. |
| `add_reaction(emoji)` | Adds a reaction from the bot (e.g. `"👍"`). |
| `remove_reaction(emoji, member)` | Removes a specific member's reaction. |
| `clear_reaction(emoji)` | Removes all reactions of one emoji. |
| `clear_reactions()` | Removes every reaction from the message. |

**Properties:**

| Property | Description |
|----------|-------------|
| `id` | The Discord message ID. |
| `content` | The message's text content. |

**`edit()` parameters** (mirrors Discord's own edit — only pass what you want to change; anything you don't pass is left untouched):

| Parameter | Description |
|-----------|-------------|
| `content` | New text. Anything `str()`-convertible. Pass `None` to remove the text entirely. |
| `embed` / `embeds` | Replace the embed(s). |
| `attachments` | Replace/keep attachments. |
| `suppress` | `True` hides all embeds, `False` brings them back. |
| `delete_after` | Seconds to wait before auto-deleting the edited message. |
| `allowed_mentions` | Control which mentions actually ping. |
| `view` | Replace the buttons. Pass `None` to **remove** all buttons from the message. |

**Example — a live-updating message:**
```python
status = bot.say("Starting job...", return_message_obj=True)
status = status.edit(content="Job 50% complete")
status = status.edit(content="Job done ✅")
status.add_reaction("🎉")
```

> **Important:** editing with `view=None` removes the buttons. If you only want to change the text, just don't pass `view` at all — the existing buttons stay.

---

## Receiving Messages

### `ask()`

Sends a message and **blocks until the user replies** — either by typing a message or by clicking a button (if a view is attached) — then returns the response.

```python
response = bot.ask(message, timeout=None, return_message_author=False, return_message_obj=False, *, view=None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | `str` | — | The question/message to send before waiting |
| `timeout` | `float` or `None` | `None` | Seconds to wait for a reply. `None` = wait forever. Returns `None` on timeout. |
| `return_message_author` | `bool` | `False` | If `True`, also returns the responding user's Discord ID |
| `return_message_obj` | `bool` | `False` | If `True`, also returns the sent question as a [`SentMessage`](#sentmessage) |
| `view` | `MyView` or `None` | `None` | Keyword-only. Attach buttons — clicking one counts as the answer (see [Asking with Buttons](#asking-with-buttons)) |

**Return value:**
- If **neither** `return_message_author` nor `return_message_obj` is set: just the response string (or `None` on timeout).
- If **either** flag is set: an [`AskResult`](#askresult) object.

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
result = bot.ask("Who wants to start?", return_message_author=True)
print(f"<@{result.author_id}> said: {result.response}")
```

**Details:**
- Any pending unread messages in the queue are **cleared** before sending, so only a fresh reply is returned
- In DM mode, only messages from the configured user are received
- In channel mode, messages from any user in the channel are received (excluding the bot itself)

---

### `AskResult`

Returned by `ask()` whenever `return_message_author` or `return_message_obj` is set. A small object with named fields — no tuple-order to remember.

| Field | Type | Description |
|-------|------|-------------|
| `response` | `str` | What the user answered — the typed message, or the clicked button's label |
| `author_id` | `int` or `None` | The responding user's Discord ID (only set if `return_message_author=True`) |
| `message_obj` | `SentMessage` or `None` | The question message the bot sent (only set if `return_message_obj=True`) |

```python
result = bot.ask("Continue?", return_message_author=True, return_message_obj=True)
print(result.response)      # "yes" — or a button label like "Approve"
print(result.author_id)     # 772970758019743745
result.message_obj.delete() # clean up the question afterwards
```

---

## Buttons & Views

Buttons let users interact with your bot by clicking instead of typing. A **view** is a container holding one or more buttons, attached to a message via `say(view=...)` or `ask(view=...)`.

There are two usage patterns:

| Pattern | How | Behavior |
|---------|-----|----------|
| **Event-based** | `say()` + `on_click` functions | Each button runs its own function every time it's clicked, forever (until timeout). Good for polls, counters, persistent controls. |
| **Blocking** | `ask()` + a view | Waits for **one** click (or a typed reply), returns which button was pressed, then disables the buttons. Good for confirmations, approve/deny. |

### Creating Buttons

Buttons are described as plain items created by helper functions:

**`standerd_button_item()`** — a normal clickable button:

```python
zdiscord_api.standerd_button_item(label, style, on_click=None, emoji=None, disabled=False, custom_id=None, row=None)
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `label` | `str` | The text on the button (max 80 chars) |
| `style` | `discord.ButtonStyle` | Color: `.primary` (blurple), `.secondary` (grey), `.success` (green), `.danger` (red) |
| `on_click` | function or `None` | Function to run when clicked — see [Button Callbacks](#button-callbacks-on_click). **Must be a plain function, NOT `async`.** |
| `emoji` | `str` or `None` | Optional emoji, e.g. `"👍"` |
| `disabled` | `bool` | Greyed out / unclickable if `True` |
| `custom_id` | `str` or `None` | Internal ID string (max 100 chars). Auto-generated if omitted. |
| `row` | `int` or `None` | Which row (0–4) the button sits on. Auto-placed if omitted. |

**`link_button_item()`** — a button that opens a URL (no callback possible — Discord opens the link directly):

```python
zdiscord_api.link_button_item(label, url, emoji=None, disabled=False, row=None)
```

### `create_view()`

Builds a view (button container) from a list of button items.

```python
view = bot.create_view(items, timeout_seconds=None)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `items` | `list[dict]` | — | Button items from `standerd_button_item()` / `link_button_item()` |
| `timeout_seconds` | `int` or `None` | `None` | How long the buttons stay clickable. `None` = forever. |

> **Must be called after the bot is connected** (`bot.bot_on == True`). The view is built safely on the bot's internal event loop for you.

**Layout limits (enforced by Discord):** max 5 rows per message, max 5 buttons per row — so 25 buttons max per message.

### Button Callbacks (`on_click`)

The `on_click` function runs every time its button is clicked.

> ⚠️ **`on_click` must be a plain (non-`async`) function.** ZdiscordAPI automatically runs it on a separate worker thread, which is exactly what makes it safe to call `bot.say()` and `bot.ask()` inside it. Do **not** define it with `async def`.

The function receives one argument: a [`ButtonContext`](#buttoncontext).

```python
click_counts = {}

def count_click(ctx):
    click_counts[ctx.label] = click_counts.get(ctx.label, 0) + 1
    bot.say(f"<@{ctx.user_id}> clicked {ctx.label}! Total: {click_counts[ctx.label]}")

view = bot.create_view([
    zdiscord_api.standerd_button_item("Vote A", discord.ButtonStyle.primary, on_click=count_click),
    zdiscord_api.standerd_button_item("Vote B", discord.ButtonStyle.primary, on_click=count_click),
])
bot.say("Cast your vote:", view=view)
```

When `say()` is called from inside an `on_click`, the message is automatically routed as a reply to the button interaction — you don't need to do anything special.

If a button has **no** `on_click`, clicking it sends a default "Button clicked" message.

### `ButtonContext`

The single object passed to every `on_click` function. Type it in your editor (`ctx.`) to see everything available via autocomplete.

| Attribute / Property | Type | Description |
|----------------------|------|-------------|
| `ctx.label` | `str` | The clicked button's label — handy when one function serves multiple buttons |
| `ctx.custom_id` | `str` or `None` | The clicked button's custom ID |
| `ctx.user_id` | `int` | Discord ID of whoever clicked |
| `ctx.message_obj` | `discord.Message` or `None` | The message the buttons are attached to |
| `ctx.item` | `dict` | The full raw button item dict |
| `ctx.interaction` | `discord.Interaction` | The raw interaction (advanced use — for reading `ctx.interaction.guild`, `.channel`, etc.) |
| `ctx.view` | `MyView` | The view the button belongs to |

**Example — one handler reused across many buttons:**
```python
shopping_list = {}

def add_item(ctx):
    shopping_list[ctx.label] = shopping_list.get(ctx.label, 0) + 1
    summary = "\n".join(f"{k}: {v}" for k, v in shopping_list.items())
    bot.say(f"**Shopping list:**\n{summary}")

view = bot.create_view([
    zdiscord_api.standerd_button_item("Apples", discord.ButtonStyle.success, on_click=add_item),
    zdiscord_api.standerd_button_item("Bread", discord.ButtonStyle.success, on_click=add_item),
    zdiscord_api.standerd_button_item("Milk", discord.ButtonStyle.success, on_click=add_item),
])
bot.say("Click to add items:", view=view)
```

### Asking with Buttons

Pass a view into `ask()` and the buttons become answer options. The first thing that happens — a button click **or** a typed message — is returned as the response. For button clicks, the response is the **button's label** (as if the user had typed it).

After the answer arrives, the buttons are automatically **disabled** (greyed out) so the question can't be answered twice.

```python
view = bot.create_view([
    zdiscord_api.standerd_button_item("Approve", discord.ButtonStyle.green),
    zdiscord_api.standerd_button_item("Deny", discord.ButtonStyle.red),
])

result = bot.ask("Approve this request?", return_message_author=True, view=view)

if result.response == "Approve":
    bot.say(f"Approved by <@{result.author_id}> ✅")
else:
    bot.say("Request denied ❌")
```

> When a view is passed to `ask()`, any `on_click` functions on those buttons are **overridden** — the buttons' only job becomes answering the question. Don't reuse the same view object across multiple `ask()` calls; create a fresh one each time.

### Exclusive Buttons

Buttons are **exclusive** by default: while one button's `on_click` is still running, clicking any button shows the user an ephemeral "⚠️ This is already running, please wait." message instead of starting a second run. This prevents overlapping executions from interfering with each other.

### Dropdowns (Work in Progress)

Dropdown (select menu) support is planned but not yet implemented. `dropdown_item()` exists as a placeholder and currently does nothing.

---

## Slash Commands

Slash commands allow users to interact with the bot via Discord's `/command` interface.

> Slash commands are only available in **channel mode** (not DM mode).

### `set_command()`

A decorator that registers a slash command handler.

```python
@bot.set_command(name, description, exclusive=False)
async def your_handler():
    ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | The command name. Spaces are automatically converted to hyphens (e.g. `"server status"` → `/server-status`) |
| `description` | `str` | Short description shown in Discord's command picker |
| `exclusive` | `bool` | If `True`, only one instance of this command can run at a time — others get a "please wait" message |

### Responding from a Command

To respond, just call `bot.say()` inside your handler — as many times as you want, whenever you want. ZdiscordAPI automatically detects that a command is running and routes the message as a reply to the command interaction. You can also call `bot.ask()` to have a full back-and-forth conversation inside a single command.

There is **no 3-second time pressure on your code**: the interaction is acknowledged immediately behind the scenes, and your handler can then take as long as it needs.

```python
@bot.set_command("ping", "Check if the bot is alive")
async def ping_command():
    bot.say("Pong! 🏓")
```

```python
@bot.set_command("server status", "Get the current server status")
async def server_status_command():
    bot.say(f"The server is currently **{server_status}**")
    bot.say("Anything else you need?")   # multiple say() calls are fine
```

**Interactive command using ask():**
```python
@bot.set_command("setup", "Run the setup wizard")
async def setup_command():
    name = bot.ask("What should I call this configuration?")
    confirm = bot.ask(f"Create configuration '{name}'? (yes/no)")
    if confirm.lower() == "yes":
        bot.say(f"✅ Created **{name}**")
    else:
        bot.say("Cancelled.")
```

If your handler never calls `say()`, the user just sees a silent `✓` (visible only to them) confirming the command ran.

### Accessing the User ID

If your handler needs to know **who ran the command**, add a `user_id` parameter. It will be automatically injected — no other changes needed.

```python
@bot.set_command("claim", "Claim your reward")
async def claim_command(user_id):
    bot.say(f"<@{user_id}> claimed their reward!")  # Mentions the user
```

> `user_id` is the only special injected parameter. Any handler without it works exactly the same as before — you don't need to add it if you don't use it.

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
    bot.say("Hello!")

@bot.set_command("status", "Get status")
async def status_command():
    bot.say(f"Status: {current_status}")

bot.update_commands()  # Push all commands to Discord
```

---

## Notes & Tips

**Discord character limit**
Messages longer than 2000 characters are automatically split and sent as multiple messages. You don't need to handle this yourself.

**Message batching**
If you call `say()` many times rapidly (with the default `return_message_obj=False`), the bot will batch consecutive text messages together into one Discord message to avoid spam. Image messages are never batched, and messages requesting a `SentMessage` back are sent individually.

**Thread safety**
`say()`, `send_image()`, `ask()`, and all `SentMessage` methods are safe to call from any regular thread. The bot runs in a background daemon thread and communicates via queues.

**Don't call blocking functions from async code**
`say()` and `ask()` are designed for regular (synchronous) code — your main script, command handlers, and `on_click` functions (which ZdiscordAPI runs on worker threads for you). Never call them from your own `async def` code running on the bot's event loop — that would freeze the bot.

**Button callbacks are plain functions**
`on_click` functions must **not** be `async`. Write them as ordinary `def` functions — ZdiscordAPI handles the async machinery for you, and `say()`/`ask()` work normally inside them.

**Button layout**
Up to 5 rows of 5 buttons each (25 max) per message. Buttons are auto-placed left-to-right, top-to-bottom in the order you list them, unless you set `row=` explicitly.

**Slash command names**
Discord requires command names to be lowercase and contain only letters, numbers, hyphens, or underscores. Spaces in the `name` argument are automatically converted to hyphens.

**Slash command response time**
Discord requires interactions to be acknowledged within **3 seconds**. ZdiscordAPI handles this automatically for both commands and buttons by deferring immediately — your handlers can take as long as they need.

**Guild ID**
The guild (server) ID is resolved automatically from the channel. You do not need to provide it manually.
