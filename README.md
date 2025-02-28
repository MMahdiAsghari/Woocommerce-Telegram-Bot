# 🚀 WooCommerce Telegram Bot

A powerful Telegram bot for managing your WooCommerce store directly from Telegram. This bot allows you to monitor products, orders, and customers, update stock and prices, receive low stock alerts, and view store statistics—all with a user-friendly interface. 🛍️

---

## ✨ Features

### 🛒 Product Management
- 📋 List all products with details (ID, Name, Type, SKU, Price, Stock, Attributes).
- 🔎 View variation details for variable products via inline buttons.
- 🔍 Search products by name or SKU with detailed output.
- ✏️ Update product/variation prices and stock levels.

### 📦 Order Management
- 📑 View recent orders with pagination.
- 🛠️ Check detailed order info (customer, status, total, items, shipping).
- 🔄 Update order status (Pending, Processing, Completed, Cancelled).
- 📌 Bulk update order statuses.

### 👥 Customer Management
- 📃 List all customers with total spent and order count.
- 🔍 View customer details and order history.

### 🔔 Notifications
- ⚠️ Low stock alerts for products below a configurable threshold.
- 👀 Specific product stock monitoring via "Watch Product" setting.
- 🚨 API error notifications if WooCommerce connection fails repeatedly.

### 📊 Statistics
- 📈 View store stats (total orders, revenue, top product) for the last 50 orders.

### ⚙️ Settings
- 🔔 Toggle low stock and new order notifications.
- 🛠️ Set low stock threshold and watched product.
- 🌍 Switch between English and Farsi languages.
- 💲 Choose currency (USD, EUR, IRR, IRT) for price display.

### 🔒 Security
- 🔑 Admin-only access via Telegram ID whitelist.

---

## 🛠️ Prerequisites

- 🐍 Python 3.8+
- 🛒 WooCommerce store with API credentials (Consumer Key and Secret).
- 🤖 Telegram Bot Token (from [BotFather](https://t.me/BotFather)).
- 💬 Telegram Chat ID (for notifications).

---

## 📥 Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/MMahdiAsghari/woocommerce-telegram-bot.git
   cd woocommerce-telegram-bot
   ```

2. **Set Up Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables:**
   Create a `.env` file in the project root:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   WOOCOMMERCE_API_KEY=your_wc_api_key
   WOOCOMMERCE_API_SECRET=your_wc_api_secret
   WOOCOMMERCE_STORE_URL=https://yourstore.com
   ADMIN_IDS=your_telegram_id
   ```
   📝 *Replace placeholders with your actual values.*

5. **Run the Bot:**
   ```bash
   python bot.py
   ```

---

## 🎯 Usage

- ▶️ Start the bot with `/start` to see the welcome message.
- ⚙️ Use `/settings` to configure notifications, language, and currency.
- 🆘 Explore other commands with `/help`.

---

## 📁 Files

- `📜 bot.py` - Main bot script with all functionality.
- `📃 requirements.txt` - List of Python dependencies.
- `🔑 .env` - Environment variables (not tracked in Git).
- `⚙️ settings.json` - Persistent bot settings (auto-generated).

---

## 📦 Dependencies

- `📦 python-telegram-bot[job-queue]~=20.7`
- `📦 woocommerce~=3.0.0`
- `📦 python-dotenv~=1.0.1`

---

## 💡 Suggest a Feature

If you have an idea for a new feature or an improvement, feel free to open an issue or submit a pull request on [GitHub](https://github.com/MMahdiAsghari/woocommerce-telegram-bot/issues). You can also contact the developer directly with your suggestions. 🚀

---

## 🙌 Credits

- **👨‍💻 Developer:** Mahdi Asghari
- **🤖 AI Assistant:** Grok (xAI) - Assisted with coding and development.

---

## 📜 License

This project is licensed under the MIT License.
