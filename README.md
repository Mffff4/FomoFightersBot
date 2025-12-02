# FomoFightersBot

<div align="center">
  <a href="README.md">🇬🇧 English</a>
  <a href="README_RU.md">🇷🇺 Русский</a>
</div>

[<img src="https://res.cloudinary.com/dkgz59pmw/image/upload/v1736756459/knpk224-28px-channel_psjoqn.svg" alt="Channel Link" width="200">](https://t.me/+vpXdTJ_S3mo0ZjIy)
[<img src="https://res.cloudinary.com/dkgz59pmw/image/upload/v1736756459/knpk224-28px-chat_ixoikd.svg" alt="Chat Link" width="200">](https://t.me/+wWQuct9bljQ0ZDA6)

---

## 📑 Table of Contents
1. [Description](#-description)
2. [Key Features](#-key-features)
3. [Installation](#-installation)
4. [Settings](#-settings)
5. [Support and Donations](#-support-and-donations)
6. [Contact](#-contact)

---

## 📜 Description

**FomoFightersBot** is an automated bot designed for the Telegram game **Fomo Fighters**. It helps automate various in-game actions to streamline your progress.

> **⚠️ Important Note:** This project is currently in the early stages of development. The primary functionality is focused on the complete automation of the new player tutorial. Logic for long-term account management and advanced gameplay is not yet implemented.

---

## 🌟 Key Features

- **👨‍👩‍👧‍👦 Multi-Account Support:** Run the bot for multiple Telegram accounts simultaneously.
- **🌐 Proxy Integration:** Enhance security and avoid network restrictions by routing traffic through proxies.
- **🤖 Full Tutorial Automation:** Automatically completes the entire new player tutorial, including:
  - Building construction
  - Troop training
  - Attacking objectives
  - Claiming quest rewards
- **🔄 Automatic Updates:** The bot can check for updates and install them automatically to ensure you are always running the latest version.

---

## 🛠️ Installation

### Quick Start
1. **Download the project:**
   ```bash
   git clone https://github.com/your-username/FomoFightersBot.git
   cd FomoFightersBot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot:**
   - Rename `.env-example` to `.env`.
   - Edit the `.env` file to add your `API_ID` and `API_HASH`.
   - Place your session files in the `sessions` directory.
   - If using proxies, add them to `bot/config/proxies-template.txt` and rename it to `proxies.txt`.

4. **Run the bot:**
   - **Linux/macOS:** `sh run.sh`
   - **Windows:** `run.bat`

---

## ⚙️ Settings

Configure the bot by editing the `.env` file.

| Parameter | Description |
|---|---|
| `API_ID` | **Required.** Your Telegram application API ID. |
| `API_HASH` | **Required.** Your Telegram application API Hash. |
| `SESSION_START_DELAY` | Delay in seconds before starting each session. Default: `360`. |
| `REF_ID` | Referral ID for new accounts. |
| `USE_PROXY` | Whether to use proxies for Telegram connections. Default: `True`. |
| `SESSIONS_PER_PROXY`| Number of sessions to run per proxy address. Default: `1`. |
| `DISABLE_PROXY_REPLACE` | If `True`, prevents the bot from replacing a faulty proxy. Default: `False`. |
| `BLACKLISTED_SESSIONS`| A comma-separated list of session names to exclude from running. |
| `DEBUG_LOGGING` | If `True`, enables detailed debug-level logging. Default: `False`. |
| `AUTO_UPDATE` | If `True`, enables automatic updates. Default: `True`. |
| `CHECK_UPDATE_INTERVAL`| Interval in seconds to check for updates. Default: `300`. |

---

## ⚠️ Disclaimer

This software is provided "as is" without any warranty. By using this bot, you accept full responsibility for its use and any consequences that may arise.

The author is not responsible for:
- Any direct or indirect damages related to the use of the bot.
- Possible violations of the game's or Telegram's terms of service.
- Account blocking or other access restrictions.

Use this bot at your own risk.

---

## 💰 Support and Donations

Support the development:

| Currency      | Address |
|---------------|---------|
| **Bitcoin**   | `bc1pfuhstqcwwzmx4y9jx227vxcamldyx233tuwjy639fyspdrug9jjqer6aqe` |
| **Ethereum**  | `0x9c7ee1199f3fe431e45d9b1ea26c136bd79d8b54` |
| **TON**       | `UQBpZGp55xrezubdsUwuhLFvyqy6gldeo-h22OkDk006e1CL` |
| **BNB**       | `0x9c7ee1199f3fe431e45d9b1ea26c136bd79d8b54` |
| **Solana**    | `HXjHPdJXyyddd7KAVrmDg4o8pRL8duVRMCJJF2xU8JbK` |

---

## 📞 Contact

If you have questions or suggestions:
- **Telegram**: [Join our channel](https://t.me/+vpXdTJ_S3mo0ZjIy)