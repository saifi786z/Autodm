#!/usr/bin/env python3
"""
Telegram Auto DM Bot - Complete Python Version
Features: Admin Panel, Channel Join, Payment System (UPI/QR/USDT), Broadcasting
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
import qrcode
from io import BytesIO

# ==================== CONFIGURATION ====================

API_ID = 38435572  # Replace with your API ID
API_HASH = "ff57bb1c607e93c8b850668ebd11f642"  # Replace with your API Hash
BOT_TOKEN = "8748735875:AAGixYIEqDh1DkqUku79FxZG4XKB68DIPRA"  # Replace with your bot token

# Admin IDs (telegram user IDs of admins)
ADMIN_IDS = [8674318569]  # Replace with your admin IDs

# Emoji IDs for Telegram Premium
EMOJIS = {
    "sparkle": "[6147565374289220368]",
    "fire": "[6147464060305676048]",
    "star": "[6147629438021408084]",
    "crown": "[6147868521670907133]",
    "rocket": "[6147617184479711380]",
    "gem": "[6147902731085420231]",
    "party": "[6147524086768604985]",
    "trophy": "[6147698410901214769]",
    "lightning": "[6147637448135414816]",
    "heart": "[6235628846855492222]",
    "shield": "[6147439566107186310]",
    "target": "[6147460667281511517]",
    "medal": "[6147815573314082674]",
    "check": "[6238042150324409739]",
    "cross": "[6237871554223412862]",
    "warning": "[6235449188373502693]",
    "info": "[6235375710073000908]",
    "question": "[6235475653961979149]",
    "plus": "[6237585380552480043]",
    "minus": "[6237742262822901946]",
    "arrow": "[6235646232883107337]",
    "diamond": "[6235252066554484059]",
    "circle": "[6235253239080555488]",
    "square": "[6237702328216982810]",
    "triangle": "[6237864166879663987]",
    "music": "[6237579651066107302]",
    "lock": "[6235722567336859128]",
    "unlock": "[6235640361662813672]",
    "bell": "[6237585097084638739]",
    "mega": "[6237905016313615867]",
    "money": "[6235722567336859128]",
    "wallet": "[6235447586350699315]",
    "bag": "[6235778118443865838]",
    "cart": "[6235355429237430006]",
    "delivery": "[6235640361662813672]"
}

# ==================== DATA MANAGEMENT ====================

DATA_FILE = "bot_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        "users": {},
        "pending_payments": [],
        "admin_settings": {
            "channel_link": "https://t.me/yourchannel",
            "channel_username": "yourchannel",
            "upi_id": "yourupi@upi",
            "upi_qr": None,
            "usdt_address": "0x...",
            "premium_plans": {
                "7_days": {"price": 100, "days": 7},
                "15_days": {"price": 150, "days": 15},
                "30_days": {"price": 250, "days": 30}
            },
            "broadcast": []
        }
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# ==================== BOT INITIALIZATION ====================

app = Client(
    "dm_forward_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

data = load_data()

# ==================== HELPER FUNCTIONS ====================

def get_emoji(name):
    return EMOJIS.get(name, "")

def get_user(user_id):
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "joined_channel": False,
            "is_premium": False,
            "premium_expiry": None,
            "referrals": 0,
            "dms_sent": 0,
            "pending_payment": None
        }
        save_data(data)
    return data["users"][str(user_id)]

def is_admin(user_id):
    return user_id in ADMIN_IDS

def format_message(text, emoji_name=None):
    if emoji_name:
        return f"{get_emoji(emoji_name)} {text}"
    return text

def create_button(text, callback_data, color="blue"):
    """
    Colors: blue, green, red
    Telegram's new colored buttons use specific callback_data prefixes
    """
    colors = {
        "blue": {"color": 0, "text": f"🔵 {text}"},
        "green": {"color": 1, "text": f"🟢 {text}"},
        "red": {"color": 2, "text": f"🔴 {text}"}
    }
    return InlineKeyboardButton(colors[color]["text"], callback_data=callback_data)

# ==================== CHANNEL CHECK ====================

async def check_channel_membership(user_id):
    """Check if user has joined the required channel"""
    channel_link = data["admin_settings"]["channel_link"]
    channel_username = data["admin_settings"]["channel_username"]
    
    try:
        member = await app.get_chat_member(channel_username, user_id)
        if member.status in ["member", "administrator", "creator"]:
            user = get_user(user_id)
            user["joined_channel"] = True
            save_data(data)
            return True
    except:
        pass
    return False

# ==================== COMMAND HANDLERS ====================

@app.on_message(filters.command("start"))
async def start_command(client, message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    # Check if user has joined channel
    if not user.get("joined_channel", False):
        channel_link = data["admin_settings"]["channel_link"]
        channel_username = data["admin_settings"]["channel_username"]
        
        text = f"""
{get_emoji('sparkle')} *Welcome to DMS Forward Bot!* {get_emoji('sparkle')}

{get_emoji('warning')} *Please join our channel first to use this bot!* {get_emoji('warning')}

{get_emoji('arrow')} Click the button below to join:
        """
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{get_emoji('mega')} Join Channel", url=channel_link)],
            [create_button("✅ I've Joined", "check_join", "green")]
        ])
        
        await message.reply(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return
    
    # Main Menu
    await show_main_menu(message)

@app.on_callback_query(filters.regex("check_join"))
async def check_join_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if await check_channel_membership(user_id):
        await callback_query.message.delete()
        await callback_query.answer("✅ Channel joined successfully!", show_alert=True)
        await show_main_menu(callback_query.message)
    else:
        await callback_query.answer("❌ Please join the channel first!", show_alert=True)

async def show_main_menu(message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    premium_status = f"{get_emoji('crown')} Premium" if user["is_premium"] else f"{get_emoji('lock')} Free"
    
    text = f"""
{get_emoji('rocket')} *DMS FORWARD BOT* {get_emoji('rocket')}

{get_emoji('user')} *User:* {message.from_user.first_name}
{get_emoji('shield')} *Status:* {premium_status}
{get_emoji('target')} *DMs Sent:* {user['dms_sent']}
{get_emoji('crown')} *Referrals:* {user['referrals']}

{get_emoji('lightning')} *Choose an option below:* {get_emoji('lightning')}
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("📝 Set Message", "set_message", "blue")],
        [create_button("🚀 Start DM Campaign", "start_dm", "green")],
        [create_button("📊 My Stats", "my_stats", "blue")],
        [create_button("👥 Refer & Earn", "refer_earn", "green")],
        [create_button("💎 Go Premium", "go_premium", "red")],
        [create_button("📖 How to Use", "how_to_use", "blue")]
    ])
    
    await message.reply(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ==================== ADMIN PANEL ====================

@app.on_message(filters.command("admin") & filters.user(ADMIN_IDS))
async def admin_panel(client, message):
    text = f"""
{get_emoji('crown')} *ADMIN PANEL* {get_emoji('crown')}

{get_emoji('gear')} *Manage your bot settings here:*

{get_emoji('wallet')} Payment Settings
{get_emoji('mega')} Broadcast Message
{get_emoji('users')} User Management
{get_emoji('money')} Payment Approvals
{get_emoji('settings')} Bot Settings
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("💳 Payment Settings", "admin_payment", "blue")],
        [create_button("📢 Broadcast", "admin_broadcast", "green")],
        [create_button("👥 Users", "admin_users", "blue")],
        [create_button("💰 Approve Payments", "admin_approve", "red")],
        [create_button("⚙️ Settings", "admin_settings", "blue")]
    ])
    
    await message.reply(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("admin_payment") & filters.user(ADMIN_IDS))
async def admin_payment_settings(client, callback_query: CallbackQuery):
    settings = data["admin_settings"]
    
    text = f"""
{get_emoji('wallet')} *PAYMENT SETTINGS* {get_emoji('wallet')}

{get_emoji('money')} *UPI ID:* `{settings['upi_id']}`
{get_emoji('qr')} *UPI QR:* {'✅ Set' if settings['upi_qr'] else '❌ Not Set'}
{get_emoji('diamond')} *USDT Address:* `{settings['usdt_address']}`

{get_emoji('info')} *Premium Plans:*
• 7 Days - ₹{settings['premium_plans']['7_days']['price']}
• 15 Days - ₹{settings['premium_plans']['15_days']['price']}
• 30 Days - ₹{settings['premium_plans']['30_days']['price']}
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("📝 Set UPI ID", "set_upi", "blue")],
        [create_button("🖼️ Set UPI QR", "set_qr", "green")],
        [create_button("🔗 Set USDT Address", "set_usdt", "blue")],
        [create_button("💲 Set Plan Prices", "set_plans", "green")],
        [create_button("🔙 Back", "admin_back", "red")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ==================== PREMIUM PAYMENT SYSTEM ====================

@app.on_callback_query(filters.regex("go_premium"))
async def go_premium(client, callback_query: CallbackQuery):
    settings = data["admin_settings"]
    
    text = f"""
{get_emoji('crown')} *PREMIUM PLANS* {get_emoji('crown')}

{get_emoji('sparkle')} *Choose your plan:*

{get_emoji('gold')} 7 Days - ₹{settings['premium_plans']['7_days']['price']}
{get_emoji('diamond')} 15 Days - ₹{settings['premium_plans']['15_days']['price']}
{get_emoji('gem')} 30 Days - ₹{settings['premium_plans']['30_days']['price']}

{get_emoji('info')} *Payment Methods:*
💳 UPI: `{settings['upi_id']}`
🪙 USDT: `{settings['usdt_address']}`

{get_emoji('arrow')} Select a plan to continue:
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("7 Days - ₹" + str(settings['premium_plans']['7_days']['price']), "pay_7", "blue")],
        [create_button("15 Days - ₹" + str(settings['premium_plans']['15_days']['price']), "pay_15", "green")],
        [create_button("30 Days - ₹" + str(settings['premium_plans']['30_days']['price']), "pay_30", "red")],
        [create_button("🔙 Back", "back_menu", "blue")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("pay_"))
async def payment_process(client, callback_query: CallbackQuery):
    plan = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    settings = data["admin_settings"]
    plans = settings["premium_plans"]
    
    plan_days = {
        "7": plans["7_days"]["days"],
        "15": plans["15_days"]["days"],
        "30": plans["30_days"]["days"]
    }
    
    plan_price = {
        "7": plans["7_days"]["price"],
        "15": plans["15_days"]["price"],
        "30": plans["30_days"]["price"]
    }
    
    # Store pending payment
    user = get_user(user_id)
    user["pending_payment"] = {
        "plan": plan,
        "days": plan_days[plan],
        "price": plan_price[plan],
        "method": None,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    save_data(data)
    
    text = f"""
{get_emoji('money')} *PAYMENT DETAILS* {get_emoji('money')}

{get_emoji('cart')} *Plan:* {plan} Days
{get_emoji('wallet')} *Amount:* ₹{plan_price[plan]}
{get_emoji('bag')} *Days:* {plan_days[plan]}

{get_emoji('info')} *Payment Methods:*
💳 UPI: `{settings['upi_id']}`
🪙 USDT: `{settings['usdt_address']}`

{get_emoji('arrow')} *How to pay:*
1. Send payment to above UPI/USDT
2. Take screenshot of payment
3. Enter UTR/Transaction ID
4. Upload payment screenshot

{get_emoji('warning')} *After payment, send UTR number and screenshot!*
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("💳 Pay with UPI", "pay_upi", "blue")],
        [create_button("🪙 Pay with USDT", "pay_usdt", "green")],
        [create_button("🔙 Back", "go_premium", "red")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("pay_upi|pay_usdt"))
async def payment_method(client, callback_query: CallbackQuery):
    method = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    user = get_user(user_id)
    if user["pending_payment"]:
        user["pending_payment"]["method"] = method.upper()
        save_data(data)
    
    text = f"""
{get_emoji('check')} *Payment Method Selected: {method.upper()}* {get_emoji('check')}

{get_emoji('arrow')} *Please complete the payment and send:*

1️⃣ *UTR/Transaction ID:* 
2️⃣ *Payment Screenshot:* 

{get_emoji('warning')} Send both UTR and screenshot together!

{get_emoji('info')} Type /utr to send payment details
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("📤 Send UTR", "send_utr", "green")],
        [create_button("🔙 Back", "go_premium", "red")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_message(filters.command("utr"))
async def send_utr(client, message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user.get("pending_payment"):
        await message.reply("❌ No pending payment found!")
        return
    
    text = f"""
{get_emoji('arrow')} *Please send your payment details:*

1️⃣ *UTR/Transaction ID:*
2️⃣ *Payment Screenshot:* 

{get_emoji('info')} Send both details as:
`/payment UTR_NUMBER` 
*and then upload your screenshot*

{get_emoji('warning')} Your payment will be reviewed by admin!
    """
    
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("payment") & ~filters.user(ADMIN_IDS))
async def receive_payment(client, message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user.get("pending_payment"):
        await message.reply("❌ No pending payment found!")
        return
    
    utr = message.text.split(" ", 1)
    if len(utr) < 2:
        await message.reply("❌ Please send your UTR number!\nExample: `/payment UTR123456`")
        return
    
    utr = utr[1]
    user["pending_payment"]["utr"] = utr
    user["pending_payment"]["status"] = "waiting_screenshot"
    save_data(data)
    
    text = f"""
{get_emoji('check')} *UTR Received!* {get_emoji('check')}

{get_emoji('tick')} UTR: `{utr}`

{get_emoji('arrow')} *Now please upload your payment screenshot!*

{get_emoji('warning')} Send the screenshot as a photo or file.
    """
    
    await message.reply(text, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.photo & ~filters.user(ADMIN_IDS))
async def receive_screenshot(client, message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    if not user.get("pending_payment") or user["pending_payment"].get("status") != "waiting_screenshot":
        return
    
    # Save screenshot
    file_id = message.photo.file_id
    user["pending_payment"]["screenshot"] = file_id
    user["pending_payment"]["status"] = "pending_approval"
    save_data(data)
    
    # Notify admin
    payment = user["pending_payment"]
    admin_text = f"""
{get_emoji('bell')} *NEW PAYMENT PENDING* {get_emoji('bell')}

{get_emoji('user')} User: {message.from_user.first_name}
🆔 ID: `{user_id}`
{get_emoji('wallet')} Plan: {payment['plan']} Days
{get_emoji('money')} Amount: ₹{payment['price']}
{get_emoji('bag')} Method: {payment['method']}
{get_emoji('arrow')} UTR: `{payment.get('utr', 'N/A')}`

{get_emoji('info')} Use /approve {user_id} to approve
Use /reject {user_id} to reject
    """
    
    # Send to all admins
    for admin_id in ADMIN_IDS:
        try:
            if payment.get('screenshot'):
                await app.send_photo(admin_id, payment['screenshot'], caption=admin_text, parse_mode=ParseMode.MARKDOWN)
            else:
                await app.send_message(admin_id, admin_text, parse_mode=ParseMode.MARKDOWN)
        except:
            pass
    
    await message.reply(f"""
{get_emoji('check')} *Payment Submitted!* {get_emoji('check')}

{get_emoji('clock')} Your payment is pending admin approval.
You will be notified once approved.

{get_emoji('warning')} This usually takes 5-10 minutes.
    """, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN PAYMENT APPROVAL ====================

@app.on_message(filters.command("approve") & filters.user(ADMIN_IDS))
async def approve_payment(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /approve USER_ID")
        return
    
    user_id = int(args[1])
    user = get_user(user_id)
    
    if not user.get("pending_payment"):
        await message.reply("❌ No pending payment found for this user!")
        return
    
    payment = user["pending_payment"]
    
    # Activate premium
    expiry_date = datetime.now() + timedelta(days=payment['days'])
    user["is_premium"] = True
    user["premium_expiry"] = expiry_date.isoformat()
    user["pending_payment"]["status"] = "approved"
    save_data(data)
    
    # Notify user
    try:
        await app.send_message(user_id, f"""
{get_emoji('crown')} *PREMIUM ACTIVATED!* {get_emoji('crown')}

{get_emoji('sparkle')} Your premium plan has been activated!

{get_emoji('gem')} *Plan:* {payment['plan']} Days
{get_emoji('calendar')} *Expires:* {expiry_date.strftime('%Y-%m-%d')}

{get_emoji('rocket')} Enjoy unlimited DM sending! {get_emoji('rocket')}
        """, parse_mode=ParseMode.MARKDOWN)
    except:
        pass
    
    await message.reply(f"✅ Payment approved for user {user_id}!")

@app.on_message(filters.command("reject") & filters.user(ADMIN_IDS))
async def reject_payment(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /reject USER_ID")
        return
    
    user_id = int(args[1])
    user = get_user(user_id)
    
    if user.get("pending_payment"):
        user["pending_payment"]["status"] = "rejected"
        save_data(data)
        
        # Notify user
        try:
            await app.send_message(user_id, f"""
{get_emoji('cross')} *Payment Rejected* {get_emoji('cross')}

{get_emoji('warning')} Your payment was rejected.

{get_emoji('info')} Please check payment details and try again.
Contact admin for support.
            """, parse_mode=ParseMode.MARKDOWN)
        except:
            pass
        
        await message.reply(f"❌ Payment rejected for user {user_id}!")
    else:
        await message.reply("❌ No pending payment found!")

# ==================== BROADCAST SYSTEM ====================

@app.on_callback_query(filters.regex("admin_broadcast") & filters.user(ADMIN_IDS))
async def broadcast_panel(client, callback_query: CallbackQuery):
    text = f"""
{get_emoji('mega')} *BROADCAST SYSTEM* {get_emoji('mega')}

{get_emoji('info')} Send a message to all users!

{get_emoji('arrow')} *How to broadcast:*
1️⃣ Type: /broadcast YOUR_MESSAGE
2️⃣ Bot will send to all users

{get_emoji('warning')} Be careful! This sends to ALL users.
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("🔙 Back", "admin_back", "red")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast_message(client, message):
    text = message.text.replace("/broadcast", "", 1).strip()
    
    if not text:
        await message.reply("❌ Please provide a message!\nUsage: /broadcast Your message here")
        return
    
    # Send to all users
    total_users = len(data["users"])
    sent = 0
    
    status_msg = await message.reply(f"📤 Broadcasting to {total_users} users...")
    
    for user_id in data["users"]:
        try:
            await app.send_message(int(user_id), f"""
{get_emoji('mega')} *ANNOUNCEMENT* {get_emoji('mega')}

{text}

{get_emoji('info')} *DMS Forward Bot*
            """, parse_mode=ParseMode.MARKDOWN)
            sent += 1
            await asyncio.sleep(0.1)  # Rate limit
        except:
            pass
    
    await status_msg.edit_text(f"""
✅ *Broadcast Complete!*

{get_emoji('check')} Sent: {sent}/{total_users} users
{get_emoji('cross')} Failed: {total_users - sent}
    """)

# ==================== SETTINGS MANAGEMENT ====================

@app.on_callback_query(filters.regex("set_upi") & filters.user(ADMIN_IDS))
async def set_upi(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text("""
{get_emoji('wallet')} *Set UPI ID* {get_emoji('wallet')}

{get_emoji('arrow')} Send your UPI ID:
Example: `yourupi@upi`

{get_emoji('info')} Type: /setupi yourupi@upi
    """, parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("setupi") & filters.user(ADMIN_IDS))
async def set_upi_command(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /setupi UPI_ID")
        return
    
    data["admin_settings"]["upi_id"] = args[1]
    save_data(data)
    await message.reply(f"✅ UPI ID updated to: `{args[1]}`")

@app.on_message(filters.command("setusdt") & filters.user(ADMIN_IDS))
async def set_usdt(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /setusdt ADDRESS")
        return
    
    data["admin_settings"]["usdt_address"] = args[1]
    save_data(data)
    await message.reply(f"✅ USDT Address updated to: `{args[1]}`")

@app.on_message(filters.command("setchannel") & filters.user(ADMIN_IDS))
async def set_channel(client, message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /setchannel @channelusername")
        return
    
    data["admin_settings"]["channel_username"] = args[1].replace("@", "")
    data["admin_settings"]["channel_link"] = f"https://t.me/{data['admin_settings']['channel_username']}"
    save_data(data)
    await message.reply(f"✅ Channel updated to: @{data['admin_settings']['channel_username']}")

# ==================== SAMPLE CALLBACK HANDLERS ====================

@app.on_callback_query(filters.regex("set_message"))
async def set_message_callback(client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(f"""
{get_emoji('sparkle')} *SET MESSAGE* {get_emoji('sparkle')}

{get_emoji('arrow')} *How to set your message:*

1️⃣ Click 'Set Message'
2️⃣ Type your promotional message
3️⃣ Press send

{get_emoji('info')} You can send:
• Text messages
• Links
• Images

{get_emoji('warning')} Type your message now!
    """, parse_mode=ParseMode.MARKDOWN)
    
    # Store user state
    user = get_user(callback_query.from_user.id)
    user["state"] = "setting_message"
    save_data(data)

@app.on_callback_query(filters.regex("start_dm"))
async def start_dm_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    if not user.get("is_premium", False):
        text = f"""
{get_emoji('lock')} *PREMIUM REQUIRED* {get_emoji('lock')}

{get_emoji('warning')} This feature requires premium!

{get_emoji('crown')} Get premium to:
• Send unlimited DMs
• Send to channel members
• Priority support

{get_emoji('arrow')} Click below to upgrade!
        """
        
        keyboard = InlineKeyboardMarkup([
            [create_button("💎 Go Premium", "go_premium", "red")],
            [create_button("🔙 Back", "back_menu", "blue")]
        ])
        
        await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
        return
    
    text = f"""
{get_emoji('rocket')} *START DM CAMPAIGN* {get_emoji('rocket')}

{get_emoji('arrow')} *Choose where to send:*

👤 *Personal DMs* - Send to all your contacts
📢 *Channel DMs* - Send to channel pending requests

{get_emoji('info')} Make sure you have set a message first!
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("👤 Personal DMs", "dm_personal", "blue")],
        [create_button("📢 Channel Pending", "dm_channels", "green")],
        [create_button("🔙 Back", "back_menu", "red")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("my_stats"))
async def my_stats_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    premium_status = f"{get_emoji('crown')} Active" if user["is_premium"] else f"{get_emoji('lock')} Inactive"
    expiry = user["premium_expiry"][:10] if user["premium_expiry"] else "N/A"
    
    text = f"""
{get_emoji('target')} *YOUR STATS* {get_emoji('target')}

{get_emoji('user')} *User:* {callback_query.from_user.first_name}
{get_emoji('shield')} *Premium:* {premium_status}
{get_emoji('calendar')} *Expires:* {expiry}
{get_emoji('crown')} *Referrals:* {user['referrals']}
{get_emoji('target')} *DMs Sent:* {user['dms_sent']}

{get_emoji('gem')} *Total Earnings:* {user['referrals'] * 1} day(s)
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("🔙 Back", "back_menu", "blue")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("refer_earn"))
async def refer_earn_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = get_user(user_id)
    
    refer_link = f"https://t.me/{app.me.username}?start=ref_{user_id}"
    
    text = f"""
{get_emoji('crown')} *REFER & EARN* {get_emoji('crown')}

{get_emoji('arrow')} *Your Referral Link:*
`{refer_link}`

{get_emoji('chart')} *Stats:*
• Referrals: {user['referrals']}
• Days Earned: {user['referrals'] * 1}

{get_emoji('info')} *How it works:*
1️⃣ Share your link
2️⃣ Friend joins with your link
3️⃣ Friend adds account & sends DM
4️⃣ You get +1 day premium!

{get_emoji('rocket')} Share your link now!
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("🔗 Share Link", "share_link", "green")],
        [create_button("🔙 Back", "back_menu", "blue")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("how_to_use"))
async def how_to_use_callback(client, callback_query: CallbackQuery):
    text = f"""
{get_emoji('info')} *HOW TO USE* {get_emoji('info')}

{get_emoji('step')} *STEP 1 - Add Account*
📱 Tap Add Account → Enter phone → Enter OTP

{get_emoji('step')} *STEP 2 - Set Message*
📝 Tap Set Message → Send your promotional text/image

{get_emoji('step')} *STEP 3 - Start Campaign*
🚀 Tap Start DM Campaign → Choose destination

{get_emoji('step')} *STEP 4 - Track Progress*
📊 Check My Stats for updates

{get_emoji('warning')} *Terms:*
• Use responsibly - no spam
• Not responsible for account restrictions
• Premium plans are non-refundable
    """
    
    keyboard = InlineKeyboardMarkup([
        [create_button("🔙 Back", "back_menu", "blue")]
    ])
    
    await callback_query.message.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@app.on_callback_query(filters.regex("back_menu"))
async def back_menu(client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await show_main_menu(callback_query.message)

@app.on_callback_query(filters.regex("admin_back") & filters.user(ADMIN_IDS))
async def admin_back(client, callback_query: CallbackQuery):
    await callback_query.message.delete()
    await admin_panel(client, callback_query.message)

# ==================== RUN BOT ====================

if __name__ == "__main__":
    print("🤖 DMS Forward Bot is starting...")
    print("📌 Bot Token:", BOT_TOKEN)
    print("👑 Admins:", ADMIN_IDS)
    print("🚀 Bot is running!")
    app.run()
