import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
import requests
from woocommerce import API

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Currency symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "IRR": "IRR",
    "IRT": "تومان"
}

# Language dictionaries
LANGUAGES = {
    "en": {
        "welcome": "Hello {user}! 👋\nI’m your WooCommerce store assistant.\nUse /settings to configure notifications or /help for commands.",
        "settings": "⚙️ **Notification Settings**\n\nLow Stock Alerts: {low_stock_status}\nNew Order Alerts: {new_orders_status}\nWatched Product: {watched_product}\nLow Stock Threshold: {threshold} units\nLanguage: {lang}\nCurrency: {currency}",
        "toggle_low_stock": "Low stock notifications set to: {status}",
        "toggle_new_orders": "New order notifications set to: {status}",
        "threshold_prompt": "Please send the new low stock threshold (e.g., 10):",
        "threshold_set": "✅ Low stock threshold set to {threshold} units.",
        "threshold_error": "⚠️ Please enter a valid number (e.g., 10).",
        "watch_prompt": "Please send the product ID to watch (e.g., 15):",
        "watch_set": "✅ Watching product ID {product_id} for stock ≤ {threshold}.",
        "watch_error": "⚠️ Please enter a valid product ID.",
        "lang_set": "✅ Language set to {lang}.",
        "currency_prompt": "Please send the new currency (e.g., USD, EUR, IRR, IRT):",
        "currency_set": "✅ Currency set to {currency}.",
        "currency_error": "⚠️ Invalid currency. Use: USD, EUR, IRR, IRT",
        "not_authorized": "⚠️ You’re not authorized to use this bot!",
        "api_error": "⚠️ Repeated API failures detected: {error}",
        "stats": "📊 **Store Stats**\n\nTotal Orders: {total_orders}\nTotal Revenue: {currency_symbol}{total_revenue}\nTop Product: {top_product} ({currency_symbol}{top_revenue})",
        "search_no_query": "⚠️ Please provide a search term. Usage: /search <name or SKU>",
        "search_no_results": "No products found matching your search.",
        "products_no_results": "No products found."
    },
    "fa": {
        "welcome": "سلام {user}! 👋\nمن دستیار فروشگاه ووکامرس شما هستم.\nاز /settings برای تنظیم اعلان‌ها یا /help برای دستورات استفاده کنید.",
        "settings": "⚙️ **تنظیمات اعلان‌ها**\n\nاعلان‌های کمبود موجودی: {low_stock_status}\nاعلان‌های سفارش جدید: {new_orders_status}\nمحصول تحت نظر: {watched_product}\nحد آستانه کمبود موجودی: {threshold} واحد\nزبان: {lang}\nارز: {currency}",
        "toggle_low_stock": "اعلان‌های کمبود موجودی تنظیم شد به: {status}",
        "toggle_new_orders": "اعلان‌های سفارش جدید تنظیم شد به: {status}",
        "threshold_prompt": "لطفاً آستانه جدید کمبود موجودی را ارسال کنید (مثلاً 10):",
        "threshold_set": "✅ آستانه کمبود موجودی تنظیم شد به {threshold} واحد.",
        "threshold_error": "⚠️ لطفاً یک عدد معتبر وارد کنید (مثلاً 10).",
        "watch_prompt": "لطفاً شناسه محصول را برای نظارت ارسال کنید (مثلاً 15):",
        "watch_set": "✅ نظارت بر محصول با شناسه {product_id} برای موجودی ≤ {threshold}.",
        "watch_error": "⚠️ لطفاً یک شناسه محصول معتبر وارد کنید.",
        "lang_set": "✅ زبان تنظیم شد به {lang}.",
        "currency_prompt": "لطفاً ارز جدید را ارسال کنید (مثلاً USD، EUR، IRR، IRT):",
        "currency_set": "✅ ارز تنظیم شد به {currency}.",
        "currency_error": "⚠️ ارز نامعتبر. از این‌ها استفاده کنید: USD، EUR، IRR، IRT",
        "not_authorized": "⚠️ شما مجاز به استفاده از این ربات نیستید!",
        "api_error": "⚠️ خطاهای مکرر API شناسایی شد: {error}",
        "stats": "📊 **آمار فروشگاه**\n\nتعداد کل سفارش‌ها: {total_orders}\nدرآمد کل: {currency_symbol}{total_revenue}\nمحصول برتر: {top_product} ({currency_symbol}{top_revenue})",
        "search_no_query": "⚠️ لطفاً یک عبارت جستجو وارد کنید. استفاده: /search <نام یا SKU>",
        "search_no_results": "هیچ محصولی با جستجوی شما یافت نشد.",
        "products_no_results": "هیچ محصولی یافت نشد."
    }
}

# WooCommerce API setup
def get_woocommerce_api():
    """Initialize and return WooCommerce API client."""
    wc_api_key = os.getenv("WOOCOMMERCE_API_KEY")
    wc_api_secret = os.getenv("WOOCOMMERCE_API_SECRET")
    store_url = os.getenv("WOOCOMMERCE_STORE_URL")

    if not all([wc_api_key, wc_api_secret, store_url]):
        logger.error("Missing WooCommerce API credentials in .env file!")
        raise ValueError("Please set WOOCOMMERCE_API_KEY, WOOCOMMERCE_API_SECRET, and WOOCOMMERCE_STORE_URL in .env")

    wcapi = API(
        url=store_url,
        consumer_key=wc_api_key,
        consumer_secret=wc_api_secret,
        version="wc/v3",
        timeout=10
    )
    return wcapi

# Function to fetch all products from WooCommerce
def fetch_products():
    """Fetch all products from WooCommerce and return them."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get("products", params={"per_page": 50})
        response.raise_for_status()
        products = response.json()
        logger.info(f"Fetched {len(products)} products from WooCommerce.")
        return products
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch products: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching products: {str(e)}")
        return None

# Function to search products by name or SKU
def search_products(query):
    """Search products by name or SKU and return matching results."""
    try:
        wcapi = get_woocommerce_api()
        params = {"per_page": 50}
        if query.isalnum() and not query.isalpha():
            params["sku"] = query
        else:
            params["search"] = query
        response = wcapi.get("products", params=params)
        response.raise_for_status()
        products = response.json()
        logger.info(f"Found {len(products)} products matching query: {query}")
        return products
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to search products: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error searching products: {str(e)}")
        return None

# Function to fetch product variations
def fetch_variations(product_id):
    """Fetch variations for a given product ID."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get(f"products/{product_id}/variations", params={"per_page": 50})
        response.raise_for_status()
        variations = response.json()
        logger.info(f"Fetched {len(variations)} variations for product ID {product_id}")
        return variations
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch variations for product {product_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching variations: {str(e)}")
        return None

# Function to update product or variation
def update_product(product_id, price=None, stock=None, variation_id=None):
    """Update price and/or stock for a product or variation."""
    try:
        wcapi = get_woocommerce_api()
        data = {}
        if price is not None:
            data["regular_price"] = str(price)
        if stock is not None:
            data["stock_quantity"] = int(stock)
            data["manage_stock"] = True

        if not data:
            return False, "No updates provided."

        endpoint = f"products/{product_id}"
        if variation_id:
            endpoint += f"/variations/{variation_id}"

        response = wcapi.put(endpoint, data)
        response.raise_for_status()
        logger.info(f"Updated {'variation' if variation_id else 'product'} ID {product_id}{'/' + str(variation_id) if variation_id else ''}: Price={price}, Stock={stock}")
        return True, "Update successful!"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update product/variation {product_id}/{variation_id}: {str(e)}")
        return False, f"Update failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error updating product: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

# Function to fetch recent orders
def fetch_orders(limit=10):
    """Fetch recent orders from WooCommerce."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get("orders", params={"per_page": limit, "orderby": "date", "order": "desc"})
        response.raise_for_status()
        orders = response.json()
        logger.info(f"Fetched {len(orders)} recent orders from WooCommerce.")
        return orders
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch orders: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching orders: {str(e)}")
        return None

# Function to fetch a single order by ID
def fetch_order(order_id):
    """Fetch details of a specific order."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get(f"orders/{order_id}")
        response.raise_for_status()
        order = response.json()
        logger.info(f"Fetched details for order ID {order_id}")
        return order
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch order {order_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching order {order_id}: {str(e)}")
        return None

# Function to update order status
def update_order_status(order_id, status):
    """Update the status of an order."""
    try:
        wcapi = get_woocommerce_api()
        data = {"status": status.lower()}
        response = wcapi.put(f"orders/{order_id}", data)
        response.raise_for_status()
        logger.info(f"Updated order {order_id} status to {status}")
        return True, f"Order status updated to {status}!"
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to update order {order_id} status: {str(e)}")
        return False, f"Update failed: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error updating order {order_id}: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

# Function to fetch all customers
def fetch_customers():
    """Fetch all customers from WooCommerce."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get("customers", params={"per_page": 50})
        response.raise_for_status()
        customers = response.json()
        logger.info(f"Fetched {len(customers)} customers from WooCommerce.")
        return customers
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch customers: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching customers: {str(e)}")
        return None

# Function to fetch customer details by ID
def fetch_customer(customer_id):
    """Fetch details of a specific customer."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get(f"customers/{customer_id}")
        response.raise_for_status()
        customer = response.json()
        logger.info(f"Fetched details for customer ID {customer_id}")
        return customer
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch customer {customer_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching customer {customer_id}: {str(e)}")
        return None

# Function to fetch customer orders
def fetch_customer_orders(customer_id):
    """Fetch all orders for a specific customer."""
    try:
        wcapi = get_woocommerce_api()
        response = wcapi.get("orders", params={"customer": customer_id, "per_page": 50, "orderby": "date", "order": "desc"})
        response.raise_for_status()
        orders = response.json()
        logger.info(f"Fetched {len(orders)} orders for customer ID {customer_id}")
        return orders
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch orders for customer {customer_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching customer orders {customer_id}: {str(e)}")
        return None

# Function to check low stock and send notifications
async def check_low_stock(context: ContextTypes.DEFAULT_TYPE):
    """Periodically check for low stock and notify."""
    if not context.bot_data.get('is_running', False) or not context.bot_data.get('notify_low_stock', True):
        return

    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        logger.error("TELEGRAM_CHAT_ID not set in .env file!")
        return

    lang = context.bot_data.get('language', 'en')
    currency = context.bot_data.get('currency', 'USD')
    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    products = fetch_products()
    attempts = 0
    while products is None and attempts < 3:
        logger.error("Failed to fetch products for low stock check, retrying...")
        products = fetch_products()
        attempts += 1
    if products is None:
        await context.bot.send_message(chat_id=chat_id, text=LANGUAGES[lang]["api_error"].format(error="Failed to fetch products after 3 attempts"))
        logger.error("API failure persisted after retries.")
        return

    low_stock_threshold = context.bot_data.get('low_stock_threshold', 5)
    watched_product_id = context.bot_data.get('watched_product_id')
    low_stock_products = [
        p for p in products 
        if p.get('stock_quantity') is not None and p.get('stock_quantity') <= low_stock_threshold
    ]

    # Check watched product specifically
    if watched_product_id:
        watched_product = next((p for p in products if str(p['id']) == str(watched_product_id)), None)
        if watched_product and watched_product.get('stock_quantity', float('inf')) <= low_stock_threshold:
            low_stock_products.append(watched_product) if watched_product not in low_stock_products else None

    if low_stock_products:
        message = "⚠️ **Low Stock Alert**\n\n"
        for product in low_stock_products:
            name = product.get('name', 'Unnamed Product')
            price = product.get('price', 'N/A')
            stock = product.get('stock_quantity', 0)
            message += f"ID: {product['id']} | {name}\nPrice: {currency_symbol}{price} | Stock: {stock}\n\n"
        try:
            await context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            logger.info(f"Sent low stock alert for {len(low_stock_products)} products.")
        except Exception as e:
            logger.error(f"Failed to send low stock alert: {str(e)}")

# Function to notify API errors
async def notify_api_error(context: ContextTypes.DEFAULT_TYPE, error_message):
    """Notify admin of repeated API failures."""
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        return
    lang = context.bot_data.get('language', 'en')
    try:
        await context.bot.send_message(chat_id=chat_id, text=LANGUAGES[lang]["api_error"].format(error=error_message))
        logger.info("Sent API error notification.")
    except Exception as e:
        logger.error(f"Failed to send API error notification: {str(e)}")

# Enhanced function to format products for Telegram display
def format_products(products, page=0, per_page=5, currency='USD'):
    """Format a detailed, paginated list of products with variation buttons."""
    lang = 'en'  # Default language; updated dynamically in the handler
    if not products:
        return LANGUAGES[lang]["products_no_results"], None

    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    start_idx = page * per_page
    end_idx = start_idx + per_page
    total_pages = (len(products) + per_page - 1) // per_page

    if start_idx >= len(products):
        return "No more products to show.", None

    product_subset = products[start_idx:end_idx]
    message = "🛍️ **Product List**\n\n"
    for product in product_subset:
        name = product.get('name', 'Unnamed Product')
        sku = product.get('sku', 'N/A')
        price = product.get('price', 'N/A')
        stock = product.get('stock_quantity', 'N/A') if product.get('stock_quantity') is not None else 'N/A'
        product_type = product.get('type', 'Simple')
        attributes = " / ".join([f"{attr.get('name', 'Attr')}: {', '.join(attr.get('options', []))}" for attr in product.get('attributes', [])]) or "N/A"

        message += (
            f"**ID: {product['id']} | {name}**\n"
            f"Type: {product_type}\n"
            f"SKU: {sku}\n"
            f"Price: {currency_symbol}{price}\n"
            f"Stock: {stock}\n"
            f"Attributes: {attributes}\n"
        )

        if product_type == "variable":
            variations = fetch_variations(product['id'])
            if variations:
                variation_ids = ", ".join([str(v['id']) for v in variations])
                message += f"Variations: {variation_ids}\n"
                message += f"[Click to view variation details]\n"
            else:
                message += "Variations: None\n"
        message += "─" * 20 + "\n\n"

    message += f"Page {page + 1} of {total_pages}"

    # Build the keyboard as a list of lists
    keyboard = []
    for product in product_subset:
        if product.get('type') == "variable":
            keyboard.append([InlineKeyboardButton(f"Variations for {product['id']}", callback_data=f"vars_{product['id']}")])
    # Add pagination buttons as separate rows
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⏮ Previous", callback_data=f"products_{page-1}"))
    if end_idx < len(products):
        pagination_row.append(InlineKeyboardButton("Next ⏭", callback_data=f"products_{page+1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    return message, reply_markup

# Function to format variations for a product
def format_variations(product_id, currency='USD'):
    """Format variation details for a specific product."""
    variations = fetch_variations(product_id)
    if not variations:
        return "No variations found for this product."

    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    message = f"📋 **Variations for Product ID: {product_id}**\n\n"
    for variation in variations:
        var_id = variation.get('id')
        var_price = variation.get('price', 'N/A')
        var_stock = variation.get('stock_quantity', 'N/A') if variation.get('stock_quantity') is not None else 'N/A'
        var_attrs = " / ".join([f"{attr.get('name', 'Attr')}: {attr.get('option', 'N/A')}" for attr in variation.get('attributes', [])]) or "N/A"
        message += (
            f"Variation ID: {var_id}\n"
            f"Attributes: {var_attrs}\n"
            f"Price: {currency_symbol}{var_price}\n"
            f"Stock: {var_stock}\n"
            f"─" * 20 + "\n\n"
        )
    return message.strip()

# Enhanced function to format search results
def format_search_results(products, currency='USD'):
    """Format detailed search results including variable product info."""
    if not products:
        return "No products found matching your search."

    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    message = "🔍 **Search Results**\n\n"
    for product in products:
        name = product.get('name', 'Unnamed Product')
        sku = product.get('sku', 'N/A')
        price = product.get('price', 'N/A')
        stock = product.get('stock_quantity', 'N/A') if product.get('stock_quantity') is not None else 'N/A'
        product_type = product.get('type', 'Simple')
        is_variable = product_type == "variable"
        attributes = " / ".join([f"{attr.get('name', 'Attr')}: {', '.join(attr.get('options', []))}" for attr in product.get('attributes', [])]) or "N/A"
        
        message += (
            f"ID: {product['id']} | {name}\n"
            f"Type: {product_type}\n"
            f"SKU: {sku}\n"
            f"Price: {currency_symbol}{price}\n"
            f"Stock: {stock}\n"
            f"Attributes: {attributes}\n"
        )
        
        if is_variable:
            variations = fetch_variations(product['id'])
            if variations:
                variation_ids = ", ".join([str(v['id']) for v in variations])
                message += f"Variation IDs: {variation_ids}\n"
                for variation in variations:
                    var_attrs = " / ".join([f"{attr.get('name', 'Attr')}: {attr.get('option', 'N/A')}" for attr in variation.get('attributes', [])])
                    var_price = variation.get('price', 'N/A')
                    var_stock = variation.get('stock_quantity', 'N/A') if variation.get('stock_quantity') is not None else 'N/A'
                    message += f"  - Var ID: {variation['id']} | {var_attrs} | Price: {currency_symbol}{var_price} | Stock: {var_stock}\n"
            else:
                message += "Variation IDs: None\n"
        
        message += "\n"
    
    return message

# Function to format orders for Telegram display
def format_orders(orders, page=0, per_page=5, currency='USD'):
    """Format a subset of orders for display with pagination."""
    if not orders:
        return "No recent orders found.", None

    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    start_idx = page * per_page
    end_idx = start_idx + per_page
    total_pages = (len(orders) + per_page - 1) // per_page

    if start_idx >= len(orders):
        return "No more orders to show.", None

    order_subset = orders[start_idx:end_idx]
    message = "📦 **Recent Orders**\n\n"
    for order in order_subset:
        customer = f"{order.get('billing', {}).get('first_name', '')} {order.get('billing', {}).get('last_name', '')}".strip() or "Unknown"
        total = order.get('total', 'N/A')
        status = order.get('status', 'N/A').capitalize()
        message += f"ID: {order['id']} | Customer: {customer}\nTotal: {currency_symbol}{total} | Status: {status}\n\n"

    message += f"Page {page + 1} of {total_pages}"

    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⏮ Previous", callback_data=f"orders_{page-1}"))
    if end_idx < len(orders):
        keyboard.append(InlineKeyboardButton("Next ⏭", callback_data=f"orders_{page+1}"))
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    return message, reply_markup

# Function to format a single order's details
def format_order_details(order, currency='USD'):
    """Format detailed information for a specific order."""
    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    customer = f"{order.get('billing', {}).get('first_name', '')} {order.get('billing', {}).get('last_name', '')}".strip() or "Unknown"
    status = order.get('status', 'N/A').capitalize()
    total = order.get('total', 'N/A')
    date = order.get('date_created', 'N/A').split("T")[0] if order.get('date_created') else 'N/A'
    
    shipping = order.get('shipping', {})
    shipping_address = f"{shipping.get('address_1', '')}, {shipping.get('city', '')}, {shipping.get('state', '')} {shipping.get('postcode', '')}".strip(", ")
    if not shipping_address:
        shipping_address = "Not provided"

    items = order.get('line_items', [])
    items_text = "\n".join([f"- {item.get('name', 'Unknown')} (Qty: {item.get('quantity', 'N/A')}, {currency_symbol}{item.get('total', 'N/A')})" for item in items]) or "No items"

    message = (
        f"📦 **Order Details - ID: {order['id']}**\n\n"
        f"Customer: {customer}\n"
        f"Status: {status}\n"
        f"Total: {currency_symbol}{total}\n"
        f"Date: {date}\n\n"
        f"**Shipping Address:**\n{shipping_address}\n\n"
        f"**Items:**\n{items_text}"
    )

    status_options = ["Pending", "Processing", "Completed", "Cancelled"]
    current_status = status.lower()
    keyboard = [
        [InlineKeyboardButton(status, callback_data=f"status_{order['id']}_{status.lower()}") for status in status_options if status.lower() != current_status]
    ]
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard[0] else None

    return message, reply_markup

# Function to format all customers for Telegram display
def format_customers(customers, page=0, per_page=5, currency='USD'):
    """Format a subset of customers for display with pagination."""
    if not customers:
        return "No customers found.", None

    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    start_idx = page * per_page
    end_idx = start_idx + per_page
    total_pages = (len(customers) + per_page - 1) // per_page

    if start_idx >= len(customers):
        return "No more customers to show.", None

    customer_subset = customers[start_idx:end_idx]
    message = "👥 **Customer List**\n\n"
    for customer in customer_subset:
        name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Unknown"
        email = customer.get('email', 'N/A')
        total_spent = customer.get('total_spent', '0.00')
        orders = fetch_customer_orders(customer['id'])
        order_count = len(orders) if orders is not None else 0
        message += f"ID: {customer['id']} | {name}\nEmail: {email} | Total Spent: {currency_symbol}{total_spent} | Orders: {order_count}\n\n"

    message += f"Page {page + 1} of {total_pages}"

    keyboard = []
    if page > 0:
        keyboard.append(InlineKeyboardButton("⏮ Previous", callback_data=f"customers_{page-1}"))
    if end_idx < len(customers):
        keyboard.append(InlineKeyboardButton("Next ⏭", callback_data=f"customers_{page+1}"))
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    return message, reply_markup

# Function to format customer details and order history
def format_customer_details(customer, orders, currency='USD'):
    """Format customer information and their order history."""
    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip() or "Unknown"
    email = customer.get('email', 'N/A')
    total_spent = customer.get('total_spent', '0.00')
    order_count = len(orders) if orders else 0

    message = (
        f"👤 **Customer Details - ID: {customer['id']}**\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n"
        f"Total Spent: {currency_symbol}{total_spent}\n"
        f"Order Count: {order_count}\n\n"
    )

    if not orders:
        message += "No orders found for this customer."
        return message, None

    message += "**Order History:**\n"
    keyboard = []
    for order in orders[:10]:
        total = order.get('total', 'N/A')
        status = order.get('status', 'N/A').capitalize()
        button_text = f"Order {order['id']} - {currency_symbol}{total} ({status})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"order_{order['id']}")])
    reply_markup = InlineKeyboardMarkup([keyboard]) if keyboard else None

    return message, reply_markup

# Load and save settings
def load_settings():
    """Load settings from settings.json."""
    try:
        with open("settings.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_settings(bot_data):
    """Save settings to settings.json."""
    with open("settings.json", "w") as f:
        json.dump({
            "is_running": bot_data.get('is_running', False),
            "notify_low_stock": bot_data.get('notify_low_stock', True),
            "notify_new_orders": bot_data.get('notify_new_orders', True),
            "low_stock_threshold": bot_data.get('low_stock_threshold', 5),
            "watched_product_id": bot_data.get('watched_product_id'),
            "language": bot_data.get('language', 'en'),
            "currency": bot_data.get('currency', 'USD')
        }, f)

# Check admin authorization
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the user is an authorized admin."""
    admin_ids = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    lang = context.bot_data.get('language', 'en')
    if not admin_ids or user_id not in admin_ids:
        await (update.message.reply_text(LANGUAGES[lang]["not_authorized"]) if update.message else update.callback_query.edit_message_text(LANGUAGES[lang]["not_authorized"]))
        return False
    return True

# Define the /start command handler without Start button
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message."""
    if not await check_admin(update, context):
        return
    user = update.message.from_user.first_name
    lang = context.bot_data.get('language', 'en')
    welcome_message = LANGUAGES[lang]["welcome"].format(user=user)
    await update.message.reply_text(welcome_message)
    logger.info(f"User {user} triggered /start.")

# Define the /settings command handler with currency option
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display settings for notifications and currency."""
    if not await check_admin(update, context):
        return
    lang = context.bot_data.get('language', 'en')
    notify_low_stock = context.bot_data.get('notify_low_stock', True)
    notify_new_orders = context.bot_data.get('notify_new_orders', True)
    low_stock_threshold = context.bot_data.get('low_stock_threshold', 5)
    watched_product_id = context.bot_data.get('watched_product_id', "None")
    currency = context.bot_data.get('currency', 'USD')

    low_stock_status = "Enabled" if notify_low_stock else "Disabled"
    new_orders_status = "Enabled" if notify_new_orders else "Disabled"
    lang_display = "English" if lang == "en" else "Farsi"

    message = LANGUAGES[lang]["settings"].format(
        low_stock_status=low_stock_status,
        new_orders_status=new_orders_status,
        watched_product=watched_product_id,
        threshold=low_stock_threshold,
        lang=lang_display,
        currency=currency
    )

    keyboard = [
        [
            InlineKeyboardButton("Toggle Low Stock", callback_data="toggle_low_stock"),
            InlineKeyboardButton("Toggle New Orders", callback_data="toggle_new_orders")
        ],
        [
            InlineKeyboardButton("Set Threshold", callback_data="set_threshold"),
            InlineKeyboardButton("Watch Product", callback_data="watch_product")
        ],
        [
            InlineKeyboardButton("Set Currency", callback_data="set_currency"),
            InlineKeyboardButton("Language: English" if lang == "fa" else "زبان: فارسی", callback_data="toggle_lang")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

# Define the /stats command handler
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display store statistics."""
    if not await check_admin(update, context):
        return
    lang = context.bot_data.get('language', 'en')
    currency = context.bot_data.get('currency', 'USD')
    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    orders = fetch_orders(limit=50)
    if orders is None:
        await update.message.reply_text("⚠️ Failed to fetch orders for stats.")
        return

    total_orders = len(orders)
    total_revenue = sum(float(order.get('total', 0)) for order in orders)

    product_sales = {}
    for order in orders:
        for item in order.get('line_items', []):
            product_id = item.get('product_id')
            total = float(item.get('total', 0))
            product_sales[product_id] = product_sales.get(product_id, 0) + total

    if product_sales:
        top_product_id = max(product_sales, key=product_sales.get)
        top_product = next((p.get('name', 'Unknown') for p in fetch_products() if p['id'] == top_product_id), "Unknown")
        top_revenue = product_sales[top_product_id]
    else:
        top_product = "N/A"
        top_revenue = 0

    message = LANGUAGES[lang]["stats"].format(
        total_orders=total_orders,
        total_revenue=total_revenue,
        top_product=top_product,
        top_revenue=top_revenue,
        currency_symbol=currency_symbol
    )
    await update.message.reply_text(message, parse_mode='Markdown')

# Define the /bulkupdate command handler
async def bulkupdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bulk update orders or products/variations."""
    if not await check_admin(update, context):
        return
    args = context.args
    if len(args) < 3:
        await update.message.reply_text("⚠️ Usage: /bulkupdate <type> <new_value> <id1> <id2> ... (type: order_status, product_price, product_stock)")
        return

    update_type, new_value = args[0], args[1]
    ids = args[2:]

    if update_type == "order_status":
        valid_statuses = ["pending", "processing", "completed", "cancelled"]
        if new_value.lower() not in valid_statuses:
            await update.message.reply_text("⚠️ Invalid status. Use: pending, processing, completed, cancelled")
            return
        for order_id in ids:
            success, message = update_order_status(order_id, new_value)
            await update.message.reply_text(f"Order {order_id}: {message}")
    elif update_type in ["product_price", "product_stock"]:
        try:
            value = float(new_value) if update_type == "product_price" else int(new_value)
            for id_str in ids:
                parts = id_str.split("-")
                product_id = parts[0]
                variation_id = parts[1] if len(parts) > 1 else None
                price = value if update_type == "product_price" else None
                stock = value if update_type == "product_stock" else None
                success, message = update_product(product_id, price, stock, variation_id)
                target = f"Variation {variation_id}" if variation_id else f"Product {product_id}"
                await update.message.reply_text(f"{target}: {message}")
        except ValueError:
            await update.message.reply_text("⚠️ Invalid value. Use a number for price or stock.")
    else:
        await update.message.reply_text("⚠️ Invalid type. Use: order_status, product_price, product_stock")

# Define a /help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    if not await check_admin(update, context):
        return
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Welcome message\n"
        "/settings - Configure notifications and currency\n"
        "/help - Show this message\n"
        "/products - List all products with details\n"
        "/search <query> - Search products by name or SKU\n"
        "/update <product_id> <price> <stock> - Update product price and stock\n"
        "/orders - View recent orders\n"
        "/order <order_id> - View order details\n"
        "/customers - List all customers\n"
        "/customer <customer_id> - View customer details and order history\n"
        "/stats - Show store statistics\n"
        "/bulkupdate <type> <new_value> <id1> <id2> ... - Bulk update orders or products (type: order_status, product_price, product_stock)"
    )
    logger.info("Help command triggered.")

# Define the enhanced /products command handler
async def products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a detailed, paginated list of products."""
    if not await check_admin(update, context):
        return
    lang = context.bot_data.get('language', 'en')
    currency = context.bot_data.get('currency', 'USD')
    products_list = fetch_products()
    if products_list is None:
        await update.message.reply_text("⚠️ Failed to fetch products. Check your store connection.")
        return
    if not products_list:
        await update.message.reply_text(LANGUAGES[lang]["products_no_results"])
        return

    message, reply_markup = format_products(products_list, page=0, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info("Displayed enhanced products list to user.")

# Define the enhanced /search command handler
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for products by name or SKU with detailed information."""
    if not await check_admin(update, context):
        return
    lang = context.bot_data.get('language', 'en')
    currency = context.bot_data.get('currency', 'USD')
    query = " ".join(context.args).strip() if context.args else None
    if not query:
        await update.message.reply_text(LANGUAGES[lang]["search_no_query"])
        return

    products_list = search_products(query)
    if products_list is None:
        await update.message.reply_text("⚠️ Failed to search products. Check your store connection.")
        return
    if not products_list:
        await update.message.reply_text(LANGUAGES[lang]["search_no_results"])
        return

    message = format_search_results(products_list, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown')
    logger.info(f"Displayed detailed search results for query: {query}")

# Define the /update command handler
async def update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Update price and stock for a product or variation."""
    if not await check_admin(update, context):
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("⚠️ Usage: /update <product_id> [price] [stock]")
        return

    try:
        product_id = int(args[0])
        price = float(args[1]) if len(args) > 1 and args[1] != "-" else None
        stock = int(args[2]) if len(args) > 2 and args[2] != "-" else None
    except ValueError:
        await update.message.reply_text("⚠️ Invalid input. Use numbers for product ID, price, and stock. Use '-' to skip.")
        return

    wcapi = get_woocommerce_api()
    try:
        product_response = wcapi.get(f"products/{product_id}")
        product_response.raise_for_status()
        product = product_response.json()
    except requests.exceptions.RequestException:
        await update.message.reply_text(f"⚠️ Product ID {product_id} not found.")
        return

    currency = context.bot_data.get('currency', 'USD')
    currency_symbol = CURRENCY_SYMBOLS.get(currency, '$')
    if product.get("type") == "variable":
        variations = fetch_variations(product_id)
        if variations is None:
            await update.message.reply_text("⚠️ Failed to fetch variations.")
            return
        if not variations:
            await update.message.reply_text("This variable product has no variations.")
            return

        keyboard = []
        for variation in variations:
            attrs = " / ".join([f"{attr.get('name', 'Attr')}: {attr.get('option', 'N/A')}" for attr in variation.get('attributes', [])])
            button_text = f"{variation['id']} - {attrs or 'No attributes'} (Price: {currency_symbol}{variation['price']}, Stock: {variation['stock_quantity'] or 'N/A'})"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"update_{product_id}_{variation['id']}_{price}_{stock}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"Select a variation for {product['name']} to update:", reply_markup=reply_markup)
    else:
        success, message = update_product(product_id, price, stock)
        await update.message.reply_text(f"📦 {message}")

# Define the /orders command handler
async def orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a paginated list of recent orders."""
    if not await check_admin(update, context):
        return
    currency = context.bot_data.get('currency', 'USD')
    orders_list = fetch_orders(limit=10)
    if orders_list is None:
        await update.message.reply_text("⚠️ Failed to fetch orders. Check your store connection.")
        return

    message, reply_markup = format_orders(orders_list, page=0, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info("Displayed recent orders to user.")

# Define the /order command handler
async def order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display details of a specific order and allow status updates."""
    if not await check_admin(update, context):
        return
    currency = context.bot_data.get('currency', 'USD')
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /order <order_id>")
        return

    try:
        order_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid order ID. Please use a number.")
        return

    order_data = fetch_order(order_id)
    if order_data is None:
        await update.message.reply_text(f"⚠️ Order ID {order_id} not found or failed to fetch.")
        return

    message, reply_markup = format_order_details(order_data, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info(f"Displayed details for order ID {order_id}")

# Define the /customers command handler
async def customers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a paginated list of all customers."""
    if not await check_admin(update, context):
        return
    currency = context.bot_data.get('currency', 'USD')
    customers_list = fetch_customers()
    if customers_list is None:
        await update.message.reply_text("⚠️ Failed to fetch customers. Check your store connection.")
        return

    message, reply_markup = format_customers(customers_list, page=0, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info("Displayed customers list to user.")

# Define the /customer command handler
async def customer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display customer details and order history."""
    if not await check_admin(update, context):
        return
    currency = context.bot_data.get('currency', 'USD')
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /customer <customer_id>")
        return

    try:
        customer_id = int(args[0])
    except ValueError:
        await update.message.reply_text("⚠️ Invalid customer ID. Please use a number.")
        return

    customer_data = fetch_customer(customer_id)
    if customer_data is None:
        await update.message.reply_text(f"⚠️ Customer ID {customer_id} not found or failed to fetch.")
        return

    orders_data = fetch_customer_orders(customer_id)
    if orders_data is None:
        await update.message.reply_text(f"⚠️ Failed to fetch orders for customer ID {customer_id}.")
        return

    message, reply_markup = format_customer_details(customer_data, orders_data, currency=currency)
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    logger.info(f"Displayed details for customer ID {customer_id}")

# Handle button clicks for pagination, updates, and UI
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks for pagination, updates, variations, and UI."""
    query = update.callback_query
    await query.answer()

    if not await check_admin(update, context):
        return

    callback_data = query.data
    lang = context.bot_data.get('language', 'en')
    currency = context.bot_data.get('currency', 'USD')
    if callback_data == "toggle_low_stock":
        context.bot_data['notify_low_stock'] = not context.bot_data.get('notify_low_stock', True)
        status = "Enabled" if context.bot_data['notify_low_stock'] else "Disabled"
        await query.edit_message_text(LANGUAGES[lang]["toggle_low_stock"].format(status=status))
        save_settings(context.bot_data)
    elif callback_data == "toggle_new_orders":
        context.bot_data['notify_new_orders'] = not context.bot_data.get('notify_new_orders', True)
        status = "Enabled" if context.bot_data['notify_new_orders'] else "Disabled"
        await query.edit_message_text(LANGUAGES[lang]["toggle_new_orders"].format(status=status))
        save_settings(context.bot_data)
    elif callback_data == "set_threshold":
        await query.edit_message_text(LANGUAGES[lang]["threshold_prompt"])
        context.user_data['awaiting_threshold'] = True
    elif callback_data == "watch_product":
        await query.edit_message_text(LANGUAGES[lang]["watch_prompt"])
        context.user_data['awaiting_watch_product'] = True
    elif callback_data == "set_currency":
        await query.edit_message_text(LANGUAGES[lang]["currency_prompt"])
        context.user_data['awaiting_currency'] = True
    elif callback_data == "toggle_lang":
        new_lang = "fa" if context.bot_data.get('language', 'en') == "en" else "en"
        context.bot_data['language'] = new_lang
        lang_display = "Farsi" if new_lang == "fa" else "English"
        await query.edit_message_text(LANGUAGES[new_lang]["lang_set"].format(lang=lang_display))
        save_settings(context.bot_data)
    elif callback_data.startswith("products_"):
        page = int(callback_data.split("_")[1])
        products_list = fetch_products()
        if products_list is None:
            await query.edit_message_text("⚠️ Failed to fetch products.")
            return
        message, reply_markup = format_products(products_list, page=page, currency=currency)
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        logger.info(f"Updated product list to page {page + 1}.")
    elif callback_data.startswith("vars_"):
        product_id = callback_data.split("_")[1]
        message = format_variations(product_id, currency=currency)
        await query.edit_message_text(message, parse_mode='Markdown')
        logger.info(f"Displayed variations for product ID {product_id}")
    elif callback_data.startswith("orders_"):
        page = int(callback_data.split("_")[1])
        orders_list = fetch_orders(limit=10)
        if orders_list is None:
            await query.edit_message_text("⚠️ Failed to fetch orders.")
            return
        message, reply_markup = format_orders(orders_list, page=page, currency=currency)
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        logger.info(f"Updated orders list to page {page + 1}.")
    elif callback_data.startswith("customers_"):
        page = int(callback_data.split("_")[1])
        customers_list = fetch_customers()
        if customers_list is None:
            await query.edit_message_text("⚠️ Failed to fetch customers.")
            return
        message, reply_markup = format_customers(customers_list, page=page, currency=currency)
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        logger.info(f"Updated customers list to page {page + 1}.")
    elif callback_data.startswith("update_"):
        _, product_id, variation_id, price, stock = callback_data.split("_")
        price = float(price) if price != "None" else None
        stock = int(stock) if stock != "None" else None
        success, message = update_product(product_id, price, stock, variation_id)
        await query.edit_message_text(f"📦 Variation {variation_id}: {message}")
        logger.info(f"User updated variation {variation_id} for product {product_id}")
    elif callback_data.startswith("status_"):
        _, order_id, status = callback_data.split("_")
        success, message = update_order_status(order_id, status)
        if success:
            order_data = fetch_order(order_id)
            if order_data:
                message, reply_markup = format_order_details(order_data, currency=currency)
                await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
            else:
                await query.edit_message_text("⚠️ Failed to refresh order details after update.")
        else:
            await query.edit_message_text(f"⚠️ {message}")
    elif callback_data.startswith("order_"):
        order_id = callback_data.split("_")[1]
        order_data = fetch_order(order_id)
        if order_data is None:
            await query.edit_message_text(f"⚠️ Order ID {order_id} not found or failed to fetch.")
            return
        message, reply_markup = format_order_details(order_data, currency=currency)
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
        logger.info(f"Displayed details for order ID {order_id} from customer view")

# Handle text input for threshold, watch product, and currency settings
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user input for settings."""
    if not await check_admin(update, context):
        return
    lang = context.bot_data.get('language', 'en')
    if context.user_data.get('awaiting_threshold', False):
        try:
            threshold = int(update.message.text)
            if threshold < 0:
                raise ValueError("Threshold must be non-negative.")
            context.bot_data['low_stock_threshold'] = threshold
            await update.message.reply_text(LANGUAGES[lang]["threshold_set"].format(threshold=threshold))
            save_settings(context.bot_data)
            context.user_data['awaiting_threshold'] = False
        except ValueError:
            await update.message.reply_text(LANGUAGES[lang]["threshold_error"])
    elif context.user_data.get('awaiting_watch_product', False):
        try:
            product_id = int(update.message.text)
            products = fetch_products()
            if products and any(p['id'] == product_id for p in products):
                context.bot_data['watched_product_id'] = str(product_id)
                threshold = context.bot_data.get('low_stock_threshold', 5)
                await update.message.reply_text(LANGUAGES[lang]["watch_set"].format(product_id=product_id, threshold=threshold))
                save_settings(context.bot_data)
            else:
                raise ValueError("Product not found.")
            context.user_data['awaiting_watch_product'] = False
        except ValueError:
            await update.message.reply_text(LANGUAGES[lang]["watch_error"])
    elif context.user_data.get('awaiting_currency', False):
        currency = update.message.text.upper()
        if currency in CURRENCY_SYMBOLS:
            context.bot_data['currency'] = currency
            await update.message.reply_text(LANGUAGES[lang]["currency_set"].format(currency=currency))
            save_settings(context.bot_data)
            context.user_data['awaiting_currency'] = False
        else:
            await update.message.reply_text(LANGUAGES[lang]["currency_error"])

# Main function to run the bot
def main():
    """Run the bot with enhanced features."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("No TELEGRAM_BOT_TOKEN found in environment variables!")
        raise ValueError("Please set TELEGRAM_BOT_TOKEN in .env file.")

    application = Application.builder().token(bot_token).build()

    # Load settings from file
    saved_settings = load_settings()
    application.bot_data.update(saved_settings)

    # Ensure bot is running and tasks are scheduled on startup
    if not application.bot_data.get('is_running', False):
        application.bot_data['is_running'] = True
        application.job_queue.run_repeating(check_low_stock, interval=3600, first=10)
        logger.info("Background tasks scheduled on startup.")
    else:
        logger.info("Bot was already running; tasks continued.")

    # Add command and message handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("bulkupdate", bulkupdate))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("products", products))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("update", update))
    application.add_handler(CommandHandler("orders", orders))
    application.add_handler(CommandHandler("order", order))
    application.add_handler(CommandHandler("customers", customers))
    application.add_handler(CommandHandler("customer", customer))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Test WooCommerce API connection on startup
    logger.info("Testing WooCommerce API connection...")
    products_data = fetch_products()
    if products_data is None:
        logger.error("WooCommerce API connection failed. Check credentials and store URL.")
    else:
        logger.info("WooCommerce API connection successful!")

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()