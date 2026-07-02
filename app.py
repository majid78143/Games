import os, time, random, string, hashlib
from datetime import datetime
from functools import wraps
import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from jinja2 import TemplateNotFound

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "19gamevip-secret-2024")

# ── Firebase Config ──────────────────────────────────────────────────────────
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyCuZDyri0F0ky2sHxFO-p2OKvEB2sQfihw",
    "authDomain": "dreamdrop-3ca3d.firebaseapp.com",
    "databaseURL": "https://dreamdrop-3ca3d-default-rtdb.firebaseio.com",
    "projectId": "dreamdrop-3ca3d",
    "storageBucket": "dreamdrop-3ca3d.firebasestorage.app",
    "messagingSenderId": "882827368473",
    "appId": "1:882827368473:web:bf146e6c9f5db32edbb288",
    "measurementId": "G-Z6B3CZZRC9"
}
DB_URL = FIREBASE_CONFIG["databaseURL"]
API_KEY = FIREBASE_CONFIG["apiKey"]

# ── Helpers ──────────────────────────────────────────────────────────────────
def ts():
    return int(time.time() * 1000)

def generate_id(length=12):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_coupon():
    return "19VIP-" + generate_id(4).upper() + "-" + generate_id(4).upper()

def format_ts(ms):
    return datetime.fromtimestamp(ms / 1000).strftime("%d %b %Y, %I:%M %p")

VIP_THRESHOLDS = [0, 1000, 5000, 15000, 35000, 70000, 120000, 200000, 300000, 450000, 600000]
VIP_NAMES = ["None", "VIP1", "VIP2", "VIP3", "VIP4", "VIP5", "VIP6", "VIP7", "VIP8", "VIP9", "VIP10"]
RANK_THRESHOLDS = [0, 500, 2000, 6000, 15000, 30000, 55000, 90000, 140000, 200000]
RANK_NAMES = ["Bronze", "Silver", "Gold", "Platinum", "Diamond", "Master", "Elite", "Champion", "Legend"]
RANK_COLORS = ["#CD7F32", "#A8A9AD", "#FFD700", "#E5E4E2", "#B9F2FF", "#9B59B6", "#E74C3C", "#F39C12", "#1A6FFF"]

def get_vip_level(xp):
    level = 0
    for i, t in enumerate(VIP_THRESHOLDS):
        if xp >= t: level = i
    return min(level, 10)

def get_rank(points):
    rank = 0
    for i, t in enumerate(RANK_THRESHOLDS):
        if points >= t: rank = i
    return min(rank, len(RANK_NAMES) - 1)

def get_rank_info(points):
    idx = get_rank(points)
    return {
        "name": RANK_NAMES[idx], "color": RANK_COLORS[idx], "index": idx,
        "next": RANK_NAMES[idx + 1] if idx < len(RANK_NAMES) - 1 else None,
        "next_threshold": RANK_THRESHOLDS[idx + 1] if idx + 1 < len(RANK_THRESHOLDS) else None
    }

# ── Auth Decorators ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user or not user.get("is_admin"):
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return decorated

# ── Firebase DB ──────────────────────────────────────────────────────────────
def db_get(path):
    try:
        r = requests.get(f"{DB_URL}/{path}.json", timeout=10)
        return r.json() if r.status_code == 200 else None
    except: return None

def db_set(path, data):
    try:
        r = requests.put(f"{DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code == 200
    except: return False

def db_push(path, data):
    try:
        r = requests.post(f"{DB_URL}/{path}.json", json=data, timeout=10)
        return r.json().get("name") if r.status_code == 200 else None
    except: return None

def db_update(path, data):
    try:
        r = requests.patch(f"{DB_URL}/{path}.json", json=data, timeout=10)
        return r.status_code == 200
    except: return False

def db_delete(path):
    try:
        r = requests.delete(f"{DB_URL}/{path}.json", timeout=10)
        return r.status_code == 200
    except: return False

# ── Firebase Auth ────────────────────────────────────────────────────────────
def auth_get_user(id_token):
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
        r = requests.post(url, json={"idToken": id_token}, timeout=10)
        data = r.json()
        return data["users"][0] if "users" in data else None
    except: return None

def auth_forgot_password(email):
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
        r = requests.post(url, json={"requestType": "PASSWORD_RESET", "email": email}, timeout=10)
        return r.json()
    except: return {"error": {"message": "Failed"}}

# ── AI Support ───────────────────────────────────────────────────────────────
KNOWLEDGE_BASE = {
    "greet": {"patterns": ["hello","hi","hey","namaste","helo","hii"], "responses": {"en": "Hello! I am 19AI, your support assistant for 19GameVIP.", "hi": "Namaste! Main 19AI hoon, aapka 19GameVIP support assistant."}},
    "vip": {"patterns": ["vip","vip1","vip2","vip levels","vip benefits"], "responses": {"en": "19GameVIP has 10 VIP levels (VIP1-VIP10). Each level unlocks higher rewards and bonuses.", "hi": "19GameVIP mein 10 VIP levels hain (VIP1-VIP10). Har level par zyada rewards milte hain."}},
    "deposit": {"patterns": ["deposit","add money","recharge","topup"], "responses": {"en": "Go to Wallet > Deposit. Enter amount and submit proof. Balance credited after verification.", "hi": "Wallet > Deposit par jaiye. Amount enter karein aur proof submit karein."}},
    "withdraw": {"patterns": ["withdraw","withdrawal","cashout","nikalna"], "responses": {"en": "Go to Wallet > Withdraw. Minimum 100. Processing 24-48 hours.", "hi": "Wallet > Withdraw par jaiye. Minimum 100. Processing 24-48 ghante."}},
    "games": {"patterns": ["games","game","play","prediction","dice","crash","slot"], "responses": {"en": "19GameVIP offers 19 games: Prediction, Dice, Wheel, Mines, Crash, Keno, Card, Slot, Coin and more.", "hi": "19GameVIP mein 19 games hain: Prediction, Dice, Wheel, Mines, Crash, Keno aur aur bhi."}},
    "support": {"patterns": ["help","support","problem","issue","contact","madad"], "responses": {"en": "I can help with games, payments, account, VIP. For critical issues contact admin via Support page.", "hi": "Main games, payments, account, VIP mein help kar sakta hoon."}},
    "default": {"responses": {"en": "I'm not sure I understand. I can help with: Games, VIP, Deposits, Withdrawals, Events.", "hi": "Mujhe samajh nahi aaya. Main in cheezein mein help kar sakta hoon: Games, VIP, Deposits, Withdrawals."}}
}

def detect_language(text):
    hindi_words = ["kya","hai","kaise","mujhe","aap","main","mein","kar","hoon","nahi","namaste"]
    lower = text.lower()
    for word in hindi_words:
        if word in lower.split(): return "hi"
    return "en"

def process_message(message, lang=None):
    if not lang: lang = detect_language(message)
    lower = message.lower().strip()
    tokens = set(lower.replace("?","").replace("!","").split())
    best_match, best_score = None, 0
    for key, data in KNOWLEDGE_BASE.items():
        if key == "default": continue
        score = sum(len(set(p.split()) & tokens) + (3 if p in lower else 0) for p in data.get("patterns", []))
        if score > best_score: best_score, best_match = score, key
    if best_match and best_score > 0:
        response = KNOWLEDGE_BASE[best_match]["responses"].get(lang) or KNOWLEDGE_BASE[best_match]["responses"]["en"]
    else:
        response = KNOWLEDGE_BASE["default"]["responses"].get(lang, KNOWLEDGE_BASE["default"]["responses"]["en"])
    return {"response": response, "lang": lang}

# ── Games ────────────────────────────────────────────────────────────────────
GAMES = [
    {"id": "prediction", "name": "Prediction", "icon": "prediction", "min_bet": 10, "max_bet": 10000},
    {"id": "dice", "name": "Dice", "icon": "dice", "min_bet": 10, "max_bet": 10000},
    {"id": "wheel", "name": "Wheel", "icon": "wheel", "min_bet": 10, "max_bet": 5000},
    {"id": "mines", "name": "Mines", "icon": "mines", "min_bet": 10, "max_bet": 5000},
    {"id": "crash", "name": "Crash", "icon": "crash", "min_bet": 10, "max_bet": 10000},
    {"id": "keno", "name": "Keno", "icon": "keno", "min_bet": 10, "max_bet": 2000},
    {"id": "card", "name": "Card", "icon": "card", "min_bet": 10, "max_bet": 5000},
    {"id": "slot", "name": "Slot", "icon": "slot", "min_bet": 5, "max_bet": 2000},
    {"id": "coin", "name": "Coin Flip", "icon": "coin", "min_bet": 10, "max_bet": 10000},
    {"id": "lucky", "name": "Lucky Number", "icon": "lucky", "min_bet": 10, "max_bet": 5000},
    {"id": "stock", "name": "Stock Prediction", "icon": "stock", "min_bet": 10, "max_bet": 10000},
    {"id": "casino", "name": "Casino", "icon": "casino", "min_bet": 50, "max_bet": 50000},
]

def _compute_result(game_id, bet, data):
    extra = {}
    if game_id == "prediction":
        choice = data.get("choice", "high")
        number = random.randint(0, 9)
        won = (choice == "high" and number >= 5) or (choice == "low" and number < 5)
        return f"{choice}_{'win' if won else 'loss'}", bet * 1.9 if won else 0, {"number": number}
    elif game_id == "dice":
        choice = int(data.get("choice", 1))
        roll = random.randint(1, 6)
        return str(roll), bet * 5.5 if roll == choice else 0, {"roll": roll}
    elif game_id == "coin":
        choice = data.get("choice", "heads")
        flip = random.choice(["heads", "tails"])
        return flip, bet * 1.95 if flip == choice else 0, {"flip": flip}
    elif game_id == "wheel":
        segments = [0, 1.5, 2, 3, 5, 0, 1.5, 2, 0, 10]
        seg = random.randint(0, len(segments) - 1)
        mult = segments[seg]
        return str(mult) + "x", bet * mult, {"segment": seg, "multiplier": mult}
    elif game_id == "crash":
        cashout = float(data.get("cashout", 1.5))
        crash_at = round(max(1.0, random.expovariate(0.4) + 1.0), 2)
        won = cashout <= crash_at
        return f"crash_{crash_at}", bet * cashout if won else 0, {"crash_at": crash_at, "cashout": cashout}
    elif game_id == "slot":
        symbols = ["7", "BAR", "BELL", "CHERRY", "LEMON", "ORANGE"]
        reels = [random.choice(symbols) for _ in range(3)]
        if reels[0] == reels[1] == reels[2]: mult = 10 if reels[0] == "7" else (5 if reels[0] == "BAR" else 3)
        elif reels[0] == reels[1] or reels[1] == reels[2]: mult = 1.5
        else: mult = 0
        return "-".join(reels), bet * mult, {"reels": reels, "multiplier": mult}
    elif game_id == "keno":
        chosen = data.get("chosen", [])[:10]
        drawn = random.sample(range(1, 81), 20)
        matches = len(set(chosen) & set(drawn))
        mult_table = [0, 0.5, 1, 2, 4, 8, 16, 32, 64, 128, 256]
        mult = mult_table[min(matches, 10)]
        return f"{matches}_matches", bet * mult, {"drawn": drawn, "matches": matches, "multiplier": mult}
    elif game_id == "card":
        choice = data.get("choice", "high")
        player, dealer = random.randint(1, 13), random.randint(1, 13)
        won = (choice == "high" and player > dealer) or (choice == "low" and player < dealer) or (choice == "tie" and player == dealer)
        return f"{player}_vs_{dealer}", (bet * 10 if choice == "tie" else bet * 1.95) if won else 0, {"player": player, "dealer": dealer}
    elif game_id == "lucky":
        chosen = int(data.get("chosen", 1))
        drawn = random.randint(1, 10)
        return str(drawn), bet * 9 if chosen == drawn else 0, {"drawn": drawn}
    elif game_id == "stock":
        direction = data.get("direction", "up")
        change = round(random.uniform(-5, 5), 2)
        actual = "up" if change > 0 else "down"
        return actual, bet * 1.9 if direction == actual else 0, {"change": change, "actual": actual}
    else:
        won = random.random() > 0.5
        return "win" if won else "loss", bet * 1.9 if won else 0, {}

def _record_game(uid, game_id, bet, result, payout):
    profile = db_get(f"users/{uid}") or {}
    balance = float(profile.get("balance", 0))
    new_balance = max(0, balance - bet + payout)
    won = payout > bet
    new_xp = profile.get("vip_xp", 0) + int(bet * 0.05) + (int(bet * 0.1) if won else 0)
    new_rp = profile.get("rank_points", 0) + int(bet * 0.02) + (10 if won else 0)
    db_update(f"users/{uid}", {
        "balance": new_balance, "vip_xp": new_xp,
        "vip_level": get_vip_level(new_xp), "rank_points": new_rp,
        "rank": RANK_NAMES[get_rank(new_rp)],
        "total_games": profile.get("total_games", 0) + 1,
        "total_wins": profile.get("total_wins", 0) + (1 if won else 0),
        "total_wagered": profile.get("total_wagered", 0) + bet,
    })
    hist_id = generate_id()
    db_set(f"game_history/{uid}/{hist_id}", {"id": hist_id, "game": game_id, "bet": bet, "result": result, "payout": payout, "won": won, "time": ts()})
    return new_balance

def _log(message):
    log_id = generate_id()
    admin_uid = session.get("user", {}).get("uid", "admin")
    db_set(f"logs/{log_id}", {"message": message, "admin": admin_uid, "time": ts()})

# ── Context Processor ────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {"firebase_config": FIREBASE_CONFIG, "app_name": "19GameVIP", "current_user": session.get("user")}

# ════════════════════════════════════════════════════════════
# AUTH ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/auth/login", methods=["GET", "POST"])
def login():
    if session.get("user"): return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/auth/register", methods=["GET", "POST"])
def register():
    if session.get("user"): return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/auth/forgot-password")
def forgot_password():
    return render_template("forgot_password.html")

@app.route("/auth/verify-email")
def verify_email():
    return render_template("verify_email.html")

@app.route("/auth/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/auth/session", methods=["POST"])
def set_session():
    data = request.get_json()
    id_token = data.get("idToken")
    refresh_token = data.get("refreshToken")
    if not id_token: return jsonify({"error": "No token"}), 400
    user_info = auth_get_user(id_token)
    if not user_info: return jsonify({"error": "Invalid token"}), 401
    uid = user_info["localId"]
    email = user_info.get("email", "")
    email_verified = user_info.get("emailVerified", False)
    db_user = db_get(f"users/{uid}")
    if not db_user:
        profile = {"uid": uid, "email": email, "username": email.split("@")[0], "display_name": email.split("@")[0], "avatar": "", "frame": "bronze", "balance": 0, "vip_xp": 0, "vip_level": 0, "rank_points": 0, "rank": "Bronze", "is_admin": False, "is_creator": False, "email_verified": email_verified, "created_at": ts(), "last_login": ts(), "total_games": 0, "total_wins": 0, "total_wagered": 0}
        db_set(f"users/{uid}", profile)
    else:
        db_set(f"users/{uid}/last_login", ts())
        profile = db_get(f"users/{uid}")
    session["user"] = {"uid": uid, "email": email, "display_name": profile.get("display_name", email.split("@")[0]), "avatar": profile.get("avatar", ""), "vip_level": profile.get("vip_level", 0), "rank": profile.get("rank", "Bronze"), "balance": profile.get("balance", 0), "is_admin": profile.get("is_admin", False), "is_creator": profile.get("is_creator", False), "email_verified": email_verified, "id_token": id_token, "refresh_token": refresh_token}
    db_set(f"login_history/{uid}/{generate_id()}", {"time": ts(), "device": request.headers.get("User-Agent", "")[:100], "ip": request.remote_addr})
    return jsonify({"success": True, "redirect": url_for("index")})

@app.route("/auth/api/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.get_json()
    email = data.get("email", "")
    if not email: return jsonify({"error": "Email required"}), 400
    result = auth_forgot_password(email)
    if "error" in result: return jsonify({"error": result["error"].get("message", "Failed")}), 400
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
# HOME ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/")
def index():
    banners = db_get("banners") or {}
    active_banners = [b for b in (banners.values() if isinstance(banners, dict) else []) if b.get("active")]
    events = db_get("events") or {}
    events_list = sorted(events.values(), key=lambda x: x.get("created_at", 0), reverse=True)[:3] if isinstance(events, dict) else []
    maintenance = db_get("settings/maintenance") or False
    return render_template("index.html", banners=active_banners, events=events_list, maintenance=maintenance)

@app.route("/notifications")
@login_required
def notifications():
    uid = session["user"]["uid"]
    notifs = db_get(f"notifications/{uid}") or {}
    notif_list = sorted(notifs.values(), key=lambda x: x.get("time", 0), reverse=True) if isinstance(notifs, dict) else []
    return render_template("notifications.html", notifications=notif_list)

# ════════════════════════════════════════════════════════════
# WALLET ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/wallet")
@login_required
def wallet():
    uid = session["user"]["uid"]
    profile = db_get(f"users/{uid}") or {}
    transactions = db_get(f"transactions/{uid}") or {}
    tx_list = sorted(transactions.values(), key=lambda x: x.get("time", 0), reverse=True)[:20] if isinstance(transactions, dict) else []
    settings = db_get("settings/payment") or {}
    return render_template("wallet.html", profile=profile, transactions=tx_list, payment_settings=settings)

@app.route("/wallet/deposit")
@login_required
def deposit():
    settings = db_get("settings/payment") or {}
    return render_template("deposit.html", payment_settings=settings)

@app.route("/wallet/withdraw")
@login_required
def withdraw():
    uid = session["user"]["uid"]
    profile = db_get(f"users/{uid}") or {}
    return render_template("withdraw.html", profile=profile)

@app.route("/wallet/redeem")
@login_required
def redeem():
    return render_template("redeem.html")

@app.route("/wallet/api/submit-deposit", methods=["POST"])
@login_required
def submit_deposit():
    uid = session["user"]["uid"]
    data = request.get_json()
    amount = float(data.get("amount", 0))
    if amount < 50: return jsonify({"error": "Minimum deposit is 50"}), 400
    tx_id = generate_id()
    tx = {"id": tx_id, "uid": uid, "type": "deposit", "amount": amount, "method": data.get("method", "manual"), "proof": data.get("proof", ""), "utr": data.get("utr", ""), "status": "pending", "time": ts()}
    db_set(f"transactions/{uid}/{tx_id}", tx)
    db_set(f"pending_deposits/{tx_id}", tx)
    return jsonify({"success": True, "tx_id": tx_id})

@app.route("/wallet/api/submit-withdraw", methods=["POST"])
@login_required
def submit_withdraw():
    uid = session["user"]["uid"]
    data = request.get_json()
    amount = float(data.get("amount", 0))
    if amount < 100: return jsonify({"error": "Minimum withdrawal is 100"}), 400
    profile = db_get(f"users/{uid}") or {}
    balance = float(profile.get("balance", 0))
    if amount > balance: return jsonify({"error": "Insufficient balance"}), 400
    tx_id = generate_id()
    tx = {"id": tx_id, "uid": uid, "type": "withdraw", "amount": amount, "upi": data.get("upi", ""), "status": "pending", "time": ts()}
    new_balance = balance - amount
    db_set(f"transactions/{uid}/{tx_id}", tx)
    db_set(f"pending_withdrawals/{tx_id}", tx)
    db_set(f"users/{uid}/balance", new_balance)
    session["user"]["balance"] = new_balance
    return jsonify({"success": True, "tx_id": tx_id})

@app.route("/wallet/api/redeem-coupon", methods=["POST"])
@login_required
def redeem_coupon():
    uid = session["user"]["uid"]
    data = request.get_json()
    code = data.get("code", "").strip().upper()
    if not code: return jsonify({"error": "Enter a coupon code"}), 400
    coupon = db_get(f"coupons/{code}")
    if not coupon: return jsonify({"error": "Invalid coupon code"}), 404
    if coupon.get("used"): return jsonify({"error": "Coupon already used"}), 400
    if coupon.get("expires_at") and coupon["expires_at"] < ts(): return jsonify({"error": "Coupon expired"}), 400
    redeemed_by = coupon.get("redeemed_by", [])
    if uid in redeemed_by: return jsonify({"error": "Already used this coupon"}), 400
    value = float(coupon.get("value", 0))
    profile = db_get(f"users/{uid}") or {}
    new_balance = float(profile.get("balance", 0)) + value
    db_set(f"users/{uid}/balance", new_balance)
    redeemed_by.append(uid)
    db_set(f"coupons/{code}/redeemed_by", redeemed_by)
    if coupon.get("single_use"): db_set(f"coupons/{code}/used", True)
    tx_id = generate_id()
    db_set(f"transactions/{uid}/{tx_id}", {"id": tx_id, "uid": uid, "type": "coupon", "amount": value, "code": code, "status": "completed", "time": ts()})
    session["user"]["balance"] = new_balance
    return jsonify({"success": True, "value": value, "balance": new_balance})

# ════════════════════════════════════════════════════════════
# GAMES ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/games")
def games():
    return render_template("games.html", games=GAMES)

@app.route("/games/<game_id>")
@login_required
def play(game_id):
    game = next((g for g in GAMES if g["id"] == game_id), None)
    if not game: return "Game not found", 404
    uid = session["user"]["uid"]
    profile = db_get(f"users/{uid}") or {}
    hist = db_get(f"game_history/{uid}") or {}
    hist_list = sorted([v for v in hist.values() if v.get("game") == game_id], key=lambda x: x.get("time", 0), reverse=True)[:10]
    try:
        return render_template(f"game_{game_id}.html", game=game, profile=profile, history=hist_list)
    except TemplateNotFound:
        return render_template("game_generic.html", game=game, profile=profile, history=hist_list)

@app.route("/games/api/play/<game_id>", methods=["POST"])
@login_required
def api_play(game_id):
    uid = session["user"]["uid"]
    data = request.get_json()
    bet = float(data.get("bet", 0))
    game = next((g for g in GAMES if g["id"] == game_id), None)
    if not game: return jsonify({"error": "Game not found"}), 404
    if bet < game["min_bet"] or bet > game["max_bet"]: return jsonify({"error": f"Bet must be between {game['min_bet']} and {game['max_bet']}"}), 400
    profile = db_get(f"users/{uid}") or {}
    if float(profile.get("balance", 0)) < bet: return jsonify({"error": "Insufficient balance"}), 400
    result, payout, extra = _compute_result(game_id, bet, data)
    new_balance = _record_game(uid, game_id, bet, result, payout)
    session["user"]["balance"] = new_balance
    return jsonify({"success": True, "result": result, "payout": payout, "balance": new_balance, **extra})

@app.route("/games/history")
@login_required
def game_history():
    uid = session["user"]["uid"]
    game_filter = request.args.get("game", "all")
    hist = db_get(f"game_history/{uid}") or {}
    hist_list = [v for v in hist.values() if game_filter == "all" or v.get("game") == game_filter]
    hist_list = sorted(hist_list, key=lambda x: x.get("time", 0), reverse=True)[:50]
    return render_template("game_history.html", history=hist_list, games=GAMES, filter=game_filter)

# ════════════════════════════════════════════════════════════
# PROFILE ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/profile")
@login_required
def profile():
    uid = session["user"]["uid"]
    p = db_get(f"users/{uid}") or {}
    vip_xp = p.get("vip_xp", 0)
    vip_level = get_vip_level(vip_xp)
    rank_info = get_rank_info(p.get("rank_points", 0))
    hist = db_get(f"game_history/{uid}") or {}
    hist_list = sorted(hist.values(), key=lambda x: x.get("time", 0), reverse=True)[:10] if isinstance(hist, dict) else []
    next_vip = VIP_THRESHOLDS[vip_level + 1] if vip_level < 10 else VIP_THRESHOLDS[10]
    vip_progress = min(int((vip_xp / next_vip) * 100), 100) if next_vip > 0 else 100
    return render_template("profile.html", profile=p, vip_level=vip_level, rank_info=rank_info, history=hist_list, vip_xp=vip_xp, vip_progress=vip_progress, next_vip_threshold=next_vip, vip_name=VIP_NAMES[vip_level])

@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def profile_edit():
    uid = session["user"]["uid"]
    p = db_get(f"users/{uid}") or {}
    if request.method == "POST":
        data = request.get_json()
        updates = {k: v for k, v in data.items() if k in ["display_name", "username", "avatar", "frame"]}
        if updates:
            db_update(f"users/{uid}", updates)
            for k, v in updates.items(): session["user"][k] = v
        return jsonify({"success": True})
    return render_template("profile_edit.html", profile=p)

@app.route("/profile/user/<uid>")
def profile_view(uid):
    p = db_get(f"users/{uid}")
    if not p: return "User not found", 404
    vip_level = get_vip_level(p.get("vip_xp", 0))
    rank_info = get_rank_info(p.get("rank_points", 0))
    return render_template("profile_view.html", profile=p, vip_level=vip_level, rank_info=rank_info, vip_name=VIP_NAMES[vip_level])

# ════════════════════════════════════════════════════════════
# EVENTS ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/events")
def events():
    all_events_data = db_get("events") or {}
    now = ts()
    all_events = []
    for eid, ev in (all_events_data.items() if isinstance(all_events_data, dict) else []):
        ev["id"] = eid
        if ev.get("active") and ev.get("end_at", 0) > now: all_events.append(ev)
    all_events.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    by_type = {"daily": [], "weekly": [], "monthly": [], "festival": [], "creator": []}
    for ev in all_events:
        t = ev.get("type", "daily")
        if t in by_type: by_type[t].append(ev)
    return render_template("events.html", events=all_events, by_type=by_type)

@app.route("/events/<event_id>")
def event_detail(event_id):
    event = db_get(f"events/{event_id}")
    if not event: return "Event not found", 404
    participants = db_get(f"event_participants/{event_id}") or {}
    p_list = sorted(participants.values(), key=lambda x: x.get("score", 0), reverse=True)[:10] if isinstance(participants, dict) else []
    uid = session.get("user", {}).get("uid")
    user_entry = participants.get(uid) if uid else None
    return render_template("event_detail.html", event=event, participants=p_list, user_entry=user_entry)

@app.route("/events/api/join/<event_id>", methods=["POST"])
@login_required
def join_event(event_id):
    uid = session["user"]["uid"]
    event = db_get(f"events/{event_id}")
    if not event: return jsonify({"error": "Event not found"}), 404
    if not event.get("active"): return jsonify({"error": "Event not active"}), 400
    if db_get(f"event_participants/{event_id}/{uid}"): return jsonify({"error": "Already joined"}), 400
    profile = db_get(f"users/{uid}") or {}
    db_set(f"event_participants/{event_id}/{uid}", {"uid": uid, "display_name": profile.get("display_name", "Player"), "score": 0, "joined_at": ts()})
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
# LEADERBOARD ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/leaderboard")
def leaderboard():
    period = request.args.get("period", "daily")
    game = request.args.get("game", "all")
    lb_data = db_get(f"leaderboards/{period}") or {}
    entries = [e for e in lb_data.values() if game == "all" or e.get("game") == game] if isinstance(lb_data, dict) else []
    entries = sorted(entries, key=lambda x: x.get("score", 0), reverse=True)[:100]
    for i, e in enumerate(entries): e["position"] = i + 1
    return render_template("leaderboard.html", entries=entries, period=period, game=game, games=["all", "prediction", "dice", "wheel", "mines", "crash", "keno", "card", "slot", "coin"])

# ════════════════════════════════════════════════════════════
# SUPPORT ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/support")
def support():
    socials = db_get("settings/socials") or {}
    return render_template("support.html", socials=socials)

@app.route("/support/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "").strip()
    if not message: return jsonify({"error": "Empty message"}), 400
    if len(message) > 500: return jsonify({"error": "Message too long"}), 400
    result = process_message(message, data.get("lang"))
    uid = session.get("user", {}).get("uid", "anonymous")
    db_set(f"support_chats/{uid}/{generate_id()}", {"message": message, "response": result["response"], "lang": result["lang"], "time": ts()})
    return jsonify(result)

# ════════════════════════════════════════════════════════════
# SETTINGS ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/settings")
@login_required
def settings():
    uid = session["user"]["uid"]
    p = db_get(f"users/{uid}") or {}
    return render_template("settings.html", profile=p)

@app.route("/settings/security")
@login_required
def settings_security():
    uid = session["user"]["uid"]
    login_hist = db_get(f"login_history/{uid}") or {}
    logins = sorted(login_hist.values(), key=lambda x: x.get("time", 0), reverse=True)[:10] if isinstance(login_hist, dict) else []
    return render_template("settings_security.html", logins=logins)

@app.route("/settings/notifications")
@login_required
def settings_notifications():
    uid = session["user"]["uid"]
    prefs = db_get(f"users/{uid}/notification_prefs") or {}
    return render_template("settings_notifications.html", prefs=prefs)

@app.route("/settings/api/update-profile", methods=["POST"])
@login_required
def update_profile():
    uid = session["user"]["uid"]
    data = request.get_json()
    updates = {k: v for k, v in data.items() if k in ["display_name", "username", "lang", "avatar", "frame"]}
    if updates:
        db_update(f"users/{uid}", updates)
        for k, v in updates.items(): session["user"][k] = v
    return jsonify({"success": True})

@app.route("/settings/api/update-notifications", methods=["POST"])
@login_required
def update_notifications():
    uid = session["user"]["uid"]
    db_set(f"users/{uid}/notification_prefs", request.get_json())
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
# CREATOR ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/creator")
def creator():
    creators_data = db_get("creators") or {}
    creator_list = [v for v in creators_data.values() if v.get("approved")] if isinstance(creators_data, dict) else []
    return render_template("creator.html", creators=creator_list)

@app.route("/creator/apply")
@login_required
def creator_apply():
    uid = session["user"]["uid"]
    existing = db_get(f"creator_applications/{uid}")
    return render_template("creator_apply.html", existing=existing)

@app.route("/creator/dashboard")
@login_required
def creator_dashboard():
    uid = session["user"]["uid"]
    creator_data = db_get(f"creators/{uid}")
    if not creator_data: return redirect(url_for("creator_apply"))
    referrals = db_get(f"creator_referrals/{uid}") or {}
    ref_list = list(referrals.values()) if isinstance(referrals, dict) else []
    earnings = db_get(f"creator_earnings/{uid}") or {}
    return render_template("creator_dashboard.html", creator=creator_data, referrals=ref_list, earnings=earnings)

@app.route("/creator/rewards")
@login_required
def creator_rewards():
    uid = session["user"]["uid"]
    creator_data = db_get(f"creators/{uid}")
    if not creator_data: return redirect(url_for("creator_apply"))
    reward_history = db_get(f"creator_rewards/{uid}") or {}
    rewards_list = sorted(reward_history.values(), key=lambda x: x.get("time", 0), reverse=True) if isinstance(reward_history, dict) else []
    return render_template("creator_rewards.html", creator=creator_data, rewards=rewards_list)

@app.route("/creator/events")
@login_required
def creator_events():
    uid = session["user"]["uid"]
    creator_data = db_get(f"creators/{uid}")
    if not creator_data: return redirect(url_for("creator_apply"))
    my_events = db_get(f"creator_events/{uid}") or {}
    events_list = list(my_events.values()) if isinstance(my_events, dict) else []
    return render_template("creator_events.html", creator=creator_data, events=events_list)

@app.route("/creator/api/apply", methods=["POST"])
@login_required
def creator_submit():
    uid = session["user"]["uid"]
    data = request.get_json()
    for field in ["name", "platform", "channel_url", "followers", "content_type"]:
        if not data.get(field): return jsonify({"error": f"Field '{field}' is required"}), 400
    db_set(f"creator_applications/{uid}", {**data, "uid": uid, "status": "pending", "applied_at": ts()})
    return jsonify({"success": True})

# ════════════════════════════════════════════════════════════
# ADMIN ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/admin")
@admin_required
def admin():
    users_data = db_get("users") or {}
    pending_dep = len(db_get("pending_deposits") or {})
    pending_with = len(db_get("pending_withdrawals") or {})
    creators_data = db_get("creator_applications") or {}
    pending_creators = len([v for v in creators_data.values() if v.get("status") == "pending"]) if isinstance(creators_data, dict) else 0
    return render_template("admin.html", user_count=len(users_data) if isinstance(users_data, dict) else 0, pending_dep=pending_dep, pending_with=pending_with, pending_creators=pending_creators)

@app.route("/admin/users")
@admin_required
def admin_users():
    all_users = db_get("users") or {}
    user_list = sorted(all_users.values(), key=lambda x: x.get("created_at", 0), reverse=True) if isinstance(all_users, dict) else []
    return render_template("admin_users.html", users=user_list)

@app.route("/admin/payments")
@admin_required
def admin_payments():
    deposits = db_get("pending_deposits") or {}
    withdrawals = db_get("pending_withdrawals") or {}
    return render_template("admin_payments.html", deposits=list(deposits.values()) if isinstance(deposits, dict) else [], withdrawals=list(withdrawals.values()) if isinstance(withdrawals, dict) else [])

@app.route("/admin/banners")
@admin_required
def admin_banners():
    banners = db_get("banners") or {}
    return render_template("admin_banners.html", banners=list(banners.values()) if isinstance(banners, dict) else [])

@app.route("/admin/events")
@admin_required
def admin_events():
    events_data = db_get("events") or {}
    return render_template("admin_events.html", events=list(events_data.values()) if isinstance(events_data, dict) else [])

@app.route("/admin/creators")
@admin_required
def admin_creators():
    applications = db_get("creator_applications") or {}
    approved = db_get("creators") or {}
    return render_template("admin_creators.html", applications=list(applications.values()) if isinstance(applications, dict) else [], creators=list(approved.values()) if isinstance(approved, dict) else [])

@app.route("/admin/coupons")
@admin_required
def admin_coupons():
    coupons = db_get("coupons") or {}
    return render_template("admin_coupons.html", coupons=list(coupons.values()) if isinstance(coupons, dict) else [])

@app.route("/admin/settings")
@admin_required
def admin_settings():
    return render_template("admin_settings.html", payment_settings=db_get("settings/payment") or {}, social_settings=db_get("settings/socials") or {}, image_settings=db_get("settings/image_hosting") or {}, maintenance=db_get("settings/maintenance") or False)

@app.route("/admin/logs")
@admin_required
def admin_logs():
    logs_data = db_get("logs") or {}
    logs_list = sorted(logs_data.values(), key=lambda x: x.get("time", 0), reverse=True)[:100] if isinstance(logs_data, dict) else []
    return render_template("admin_logs.html", logs=logs_list)

@app.route("/admin/api/approve-deposit", methods=["POST"])
@admin_required
def approve_deposit():
    data = request.get_json()
    tx_id = data.get("tx_id")
    tx = db_get(f"pending_deposits/{tx_id}")
    if not tx: return jsonify({"error": "Not found"}), 404
    uid = tx["uid"]
    profile = db_get(f"users/{uid}") or {}
    db_set(f"users/{uid}/balance", float(profile.get("balance", 0)) + float(tx["amount"]))
    db_set(f"transactions/{uid}/{tx_id}/status", "approved")
    db_delete(f"pending_deposits/{tx_id}")
    _log(f"Deposit approved: {tx_id} for user {uid}")
    return jsonify({"success": True})

@app.route("/admin/api/reject-deposit", methods=["POST"])
@admin_required
def reject_deposit():
    data = request.get_json()
    tx_id = data.get("tx_id")
    tx = db_get(f"pending_deposits/{tx_id}")
    if not tx: return jsonify({"error": "Not found"}), 404
    db_set(f"transactions/{tx['uid']}/{tx_id}/status", "rejected")
    db_delete(f"pending_deposits/{tx_id}")
    return jsonify({"success": True})

@app.route("/admin/api/approve-withdrawal", methods=["POST"])
@admin_required
def approve_withdrawal():
    data = request.get_json()
    tx_id = data.get("tx_id")
    tx = db_get(f"pending_withdrawals/{tx_id}")
    if not tx: return jsonify({"error": "Not found"}), 404
    db_set(f"transactions/{tx['uid']}/{tx_id}/status", "approved")
    db_delete(f"pending_withdrawals/{tx_id}")
    _log(f"Withdrawal approved: {tx_id}")
    return jsonify({"success": True})

@app.route("/admin/api/ban-user", methods=["POST"])
@admin_required
def ban_user():
    data = request.get_json()
    uid = data.get("uid")
    db_set(f"users/{uid}/banned", True)
    _log(f"User banned: {uid}")
    return jsonify({"success": True})

@app.route("/admin/api/add-balance", methods=["POST"])
@admin_required
def add_balance():
    data = request.get_json()
    uid = data.get("uid")
    amount = float(data.get("amount", 0))
    profile = db_get(f"users/{uid}") or {}
    new_balance = float(profile.get("balance", 0)) + amount
    db_set(f"users/{uid}/balance", new_balance)
    _log(f"Balance added: {uid} +{amount}")
    return jsonify({"success": True, "balance": new_balance})

@app.route("/admin/api/set-vip", methods=["POST"])
@admin_required
def set_vip():
    data = request.get_json()
    uid = data.get("uid")
    level = int(data.get("level", 0))
    xp = VIP_THRESHOLDS[level] if 0 <= level <= 10 else 0
    db_update(f"users/{uid}", {"vip_level": level, "vip_xp": xp})
    return jsonify({"success": True})

@app.route("/admin/api/create-coupon", methods=["POST"])
@admin_required
def create_coupon():
    data = request.get_json()
    code = data.get("code") or generate_coupon()
    expires_days = int(data.get("expires_days", 30))
    coupon = {"code": code, "value": float(data.get("value", 100)), "single_use": data.get("single_use", True), "used": False, "redeemed_by": [], "created_at": ts(), "expires_at": ts() + (expires_days * 86400 * 1000)}
    db_set(f"coupons/{code}", coupon)
    _log(f"Coupon created: {code}")
    return jsonify({"success": True, "code": code})

@app.route("/admin/api/create-event", methods=["POST"])
@admin_required
def create_event():
    data = request.get_json()
    event_id = generate_id()
    db_set(f"events/{event_id}", {"id": event_id, "title": data.get("title", ""), "description": data.get("description", ""), "type": data.get("type", "daily"), "reward": data.get("reward", ""), "active": True, "created_at": ts(), "end_at": ts() + int(data.get("duration_hours", 24)) * 3600000})
    return jsonify({"success": True, "event_id": event_id})

@app.route("/admin/api/create-banner", methods=["POST"])
@admin_required
def create_banner():
    data = request.get_json()
    banner_id = generate_id()
    db_set(f"banners/{banner_id}", {"id": banner_id, "title": data.get("title", ""), "image": data.get("image", ""), "link": data.get("link", ""), "active": True, "created_at": ts()})
    return jsonify({"success": True, "banner_id": banner_id})

@app.route("/admin/api/approve-creator", methods=["POST"])
@admin_required
def approve_creator():
    data = request.get_json()
    uid = data.get("uid")
    app_data = db_get(f"creator_applications/{uid}")
    if not app_data: return jsonify({"error": "Application not found"}), 404
    ref_code = "REF" + uid[:8].upper()
    db_set(f"creators/{uid}", {**app_data, "approved": True, "approved_at": ts(), "ref_code": ref_code, "total_referrals": 0, "total_earnings": 0})
    db_set(f"creator_applications/{uid}/status", "approved")
    db_set(f"users/{uid}/is_creator", True)
    return jsonify({"success": True, "ref_code": ref_code})

@app.route("/admin/api/save-settings", methods=["POST"])
@admin_required
def save_settings():
    data = request.get_json()
    section = data.get("section")
    if section in ["payment", "socials", "image_hosting"]:
        db_set(f"settings/{section}", data.get("data", {}))
        return jsonify({"success": True})
    return jsonify({"error": "Invalid section"}), 400

@app.route("/admin/api/toggle-maintenance", methods=["POST"])
@admin_required
def toggle_maintenance():
    current = db_get("settings/maintenance") or False
    db_set("settings/maintenance", not current)
    return jsonify({"success": True, "maintenance": not current})

# ════════════════════════════════════════════════════════════
# API ROUTES
# ════════════════════════════════════════════════════════════
@app.route("/api/status")
def api_status():
    return jsonify({"status": "ok", "maintenance": db_get("settings/maintenance") or False, "time": ts()})

@app.route("/api/user/balance")
def api_user_balance():
    user = session.get("user")
    if not user: return jsonify({"error": "Not authenticated"}), 401
    profile = db_get(f"users/{user['uid']}") or {}
    return jsonify({"balance": profile.get("balance", 0), "vip_level": profile.get("vip_level", 0)})

@app.route("/api/leaderboard/<period>")
def api_leaderboard(period):
    if period not in ["daily", "weekly", "monthly", "alltime"]: return jsonify({"error": "Invalid period"}), 400
    data = db_get(f"leaderboards/{period}") or {}
    entries = sorted(data.values(), key=lambda x: x.get("score", 0), reverse=True)[:10] if isinstance(data, dict) else []
    return jsonify({"entries": entries})

@app.route("/api/notifications/count")
def api_notification_count():
    user = session.get("user")
    if not user: return jsonify({"count": 0})
    notifs = db_get(f"notifications/{user['uid']}") or {}
    unread = sum(1 for n in notifs.values() if not n.get("read")) if isinstance(notifs, dict) else 0
    return jsonify({"count": unread})

# ── Error Handlers ───────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e): return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e): return render_template("500.html"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
