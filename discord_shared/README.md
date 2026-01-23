# discord-shared (local editable package)

This is a local Python package meant to live in your Documents folder so you can reuse one shared Discord helper module across multiple repos.

## Folder placement (recommended)
Put this folder at:

- Windows: `C:\Users\<you>\Documents\py-libs\discord_shared\`
- macOS/Linux: `~/Documents/py-libs/discord_shared/`

## Install into a repo (editable)
Activate your repo's virtual environment, then:

```bash
pip install -e "C:\Users\<you>\Documents\py-libs\discord_shared"
```

## Import
```py
from discord_shared import DiscordBot
# or:
from discord_shared.zdiscord_api import DiscordBot
```

## Updating
Edit `src/discord_shared/zdiscord_api.py` in this folder. Any repo that installed it with `-e` will immediately use the updated code.
