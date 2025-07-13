# Bailitheoir

A minimal Discord bot to detect and log Rune Slayer boss spawns via webhook.

---

### Features

- **Real-time detection**: Parses chat for boss names, regions, and server names
- **Modular data**: All bosses, keywords, regions, and roles in JSON files
- **Auto-config**: Generates `config.ini` with defaults on first run
- **Webhook & pings**: Sends embeds to Discord; optional role mentions

---

### Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/PureIsntHere/Bailitheoir.git
   cd Bailitheoir
   ```
2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
3. **Run**  
   ```bash
   python scraper.py
   ```

> On first run, `config.ini` is created in the root. Fill in your `DISCORD_TOKEN` and `DISCORD_WEBHOOK_URL`, and set `TEST_MODE` as needed.

---

### Configuration

- **config.ini** — bot token, webhook URL, and test mode
- **data/** — JSON files for:
  - `skip_bosses.json`
  - `server_keywords.json`
  - `boss_list.json`
  - `region_list.json`
  - `region_aliases.json`
  - `boss_attributes.json`
  - `boss_ping_roles.json`

Modify any JSON to customize behavior without touching code.

---

### Contributing

1. Fork this repo  
2. Create a feature branch  
3. Submit a pull request

---

### License

MIT
