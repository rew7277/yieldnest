import os
import secrets
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, send_file
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
import qrcode

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
raw_db = os.getenv("DATABASE_URL", "sqlite:///yieldnest.db")
if raw_db.startswith("postgres://"):
    raw_db = raw_db.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = raw_db
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

BRAND_NAME = os.getenv("BRAND_NAME", "YieldNest")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@example.com")

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Fund(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    tagline = db.Column(db.String(220), nullable=True)
    description = db.Column(db.Text, nullable=False)
    slot_value = db.Column(db.Numeric(12, 2), nullable=False)
    min_slots = db.Column(db.Integer, default=1, nullable=False)
    max_slots = db.Column(db.Integer, default=100, nullable=False)
    expected_interest_rate = db.Column(db.Numeric(6, 2), nullable=False)
    maturity_date = db.Column(db.Date, nullable=False)
    early_exit_charge_percent = db.Column(db.Numeric(6, 2), default=0, nullable=False)
    phonepe_number = db.Column(db.String(30), nullable=False)
    phonepe_upi_id = db.Column(db.String(120), nullable=False)
    risk_note = db.Column(db.Text, default="Expected returns are subject to plan terms and approval.")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Investment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    fund_id = db.Column(db.Integer, db.ForeignKey("fund.id"), nullable=False)
    slots = db.Column(db.Integer, nullable=False)
    principal_amount = db.Column(db.Numeric(12, 2), nullable=False)
    expected_maturity_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(30), default="payment_pending", nullable=False)
    payment_status = db.Column(db.String(30), default="not_submitted", nullable=False)
    utr_reference = db.Column(db.String(120), nullable=True)
    payer_name = db.Column(db.String(120), nullable=True)
    payer_upi_id = db.Column(db.String(120), nullable=True)
    payer_phonepe_number = db.Column(db.String(30), nullable=True)
    screenshot_url = db.Column(db.String(500), nullable=True)
    qr_token = db.Column(db.String(80), nullable=True, index=True)
    qr_created_at = db.Column(db.DateTime, nullable=True)
    qr_expires_at = db.Column(db.DateTime, nullable=True)
    qr_regenerate_after = db.Column(db.DateTime, nullable=True)
    admin_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime, nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="investments")
    fund = db.relationship("Fund", backref="investments")


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_brand():
    return {"brand_name": BRAND_NAME, "support_email": SUPPORT_EMAIL, "today": date.today()}


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def money(value):
    return Decimal(value).quantize(Decimal("0.01"))


def maturity_amount(principal, interest_rate):
    return money(Decimal(principal) * (Decimal("1") + (Decimal(interest_rate) / Decimal("100"))))


def ensure_qr_token(inv, force=False):
    """Create a unique UPI QR token. QR is valid 60 seconds; next QR unlocks after 2 minutes."""
    now = datetime.utcnow()
    if (
        not force
        and inv.qr_token
        and inv.qr_regenerate_after
        and now < inv.qr_regenerate_after
    ):
        return inv
    inv.qr_token = secrets.token_urlsafe(18)
    inv.qr_created_at = now
    inv.qr_expires_at = now + timedelta(seconds=60)
    inv.qr_regenerate_after = now + timedelta(seconds=120)
    db.session.commit()
    return inv


def build_upi_uri(inv):
    note = f"YN-{inv.id}-{inv.qr_token[:8]}"
    params = {
        "pa": inv.fund.phonepe_upi_id,
        "pn": BRAND_NAME,
        "am": f"{Decimal(inv.principal_amount):.2f}",
        "cu": "INR",
        "tn": note,
        "tr": note,
    }
    return "upi://pay?" + urlencode(params)


@app.template_filter("inr")
def inr(value):
    try:
        return f"₹{Decimal(value):,.2f}"
    except Exception:
        return value


@app.route("/")
def index():
    funds = Fund.query.filter_by(is_active=True).order_by(Fund.created_at.desc()).limit(6).all()
    return render_template("index.html", funds=funds)


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Name, email and an 8+ character password are required.", "error")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))
        user = User(name=name, email=email, phone=phone)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        flash("Account created successfully.", "success")
        return redirect(url_for("user_dashboard"))
    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("admin_dashboard" if user.role == "admin" else "user_dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def user_dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))
    funds = Fund.query.filter_by(is_active=True).order_by(Fund.created_at.desc()).all()
    investments = Investment.query.filter_by(user_id=current_user.id).order_by(Investment.created_at.desc()).all()
    return render_template("user/dashboard.html", funds=funds, investments=investments)


@app.route("/fund/<int:fund_id>")
@login_required
def fund_detail(fund_id):
    fund = Fund.query.get_or_404(fund_id)
    return render_template("user/fund_detail.html", fund=fund)


@app.route("/fund/<int:fund_id>/invest", methods=["POST"])
@login_required
def invest(fund_id):
    fund = Fund.query.get_or_404(fund_id)
    slots = int(request.form.get("slots", 0))
    if slots < fund.min_slots or slots > fund.max_slots:
        flash(f"Please choose between {fund.min_slots} and {fund.max_slots} slots.", "error")
        return redirect(url_for("fund_detail", fund_id=fund.id))
    principal = money(Decimal(slots) * Decimal(fund.slot_value))
    inv = Investment(
        user_id=current_user.id,
        fund_id=fund.id,
        slots=slots,
        principal_amount=principal,
        expected_maturity_amount=maturity_amount(principal, fund.expected_interest_rate),
    )
    db.session.add(inv)
    db.session.commit()
    flash("Slot request created. Scan the secure QR and submit payment details.", "success")
    return redirect(url_for("payment_submit", investment_id=inv.id))


@app.route("/investment/<int:investment_id>/payment", methods=["GET", "POST"])
@login_required
def payment_submit(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id and current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect(url_for("user_dashboard"))
    if request.method == "POST":
        submitted_token = request.form.get("qr_token", "").strip()
        now = datetime.utcnow()
        if not inv.qr_token or submitted_token != inv.qr_token or not inv.qr_expires_at or now > inv.qr_expires_at:
            flash("This QR session has expired. Please generate a fresh QR and submit again.", "error")
            return redirect(url_for("payment_submit", investment_id=inv.id))
        inv.payer_name = request.form.get("payer_name", "").strip()
        inv.payer_upi_id = request.form.get("payer_upi_id", "").strip()
        inv.payer_phonepe_number = request.form.get("payer_phonepe_number", "").strip()
        inv.utr_reference = request.form.get("utr_reference", "").strip()
        inv.screenshot_url = request.form.get("screenshot_url", "").strip()
        if not inv.utr_reference or not inv.payer_name:
            flash("Payer name and UTR/reference number are required.", "error")
            return redirect(url_for("payment_submit", investment_id=inv.id))
        inv.payment_status = "submitted"
        inv.status = "verification_pending"
        inv.paid_at = now
        db.session.commit()
        flash("Payment notification submitted. We will verify it shortly.", "success")
        return redirect(url_for("user_dashboard"))
    now = datetime.utcnow()
    if not inv.qr_token or not inv.qr_regenerate_after or now >= inv.qr_regenerate_after:
        ensure_qr_token(inv, force=True)
    return render_template("user/payment.html", inv=inv, now=now)


@app.route("/investment/<int:investment_id>/qr.png")
@login_required
def payment_qr_png(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id and current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect(url_for("user_dashboard"))
    if not inv.qr_token or not inv.qr_expires_at or datetime.utcnow() > inv.qr_expires_at:
        img = qrcode.make("EXPIRED")
    else:
        img = qrcode.make(build_upi_uri(inv))
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", max_age=0)


@app.route("/investment/<int:investment_id>/qr/refresh", methods=["POST"])
@login_required
def refresh_payment_qr(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    if inv.user_id != current_user.id and current_user.role != "admin":
        flash("Access denied.", "error")
        return redirect(url_for("user_dashboard"))
    now = datetime.utcnow()
    if inv.qr_regenerate_after and now < inv.qr_regenerate_after:
        flash("New QR can be generated after the 2-minute refresh window.", "error")
    else:
        ensure_qr_token(inv, force=True)
        flash("Fresh QR generated. Complete payment within 60 seconds.", "success")
    return redirect(url_for("payment_submit", investment_id=inv.id))


@app.route("/admin")
@login_required
@admin_required
def admin_dashboard():
    stats = {
        "users": User.query.filter_by(role="user").count(),
        "funds": Fund.query.count(),
        "pending": Investment.query.filter_by(status="verification_pending").count(),
        "approved": Investment.query.filter_by(status="approved").count(),
    }
    recent = Investment.query.order_by(Investment.created_at.desc()).limit(8).all()
    return render_template("admin/dashboard.html", stats=stats, recent=recent)


@app.route("/admin/funds")
@login_required
@admin_required
def admin_funds():
    funds = Fund.query.order_by(Fund.created_at.desc()).all()
    return render_template("admin/funds.html", funds=funds)


@app.route("/admin/funds/new", methods=["GET", "POST"])
@app.route("/admin/funds/<int:fund_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def admin_fund_form(fund_id=None):
    fund = Fund.query.get(fund_id) if fund_id else None
    if request.method == "POST":
        if not fund:
            fund = Fund()
            db.session.add(fund)
        fund.name = request.form["name"].strip()
        fund.tagline = request.form.get("tagline", "").strip()
        fund.description = request.form["description"].strip()
        fund.slot_value = Decimal(request.form["slot_value"])
        fund.min_slots = int(request.form["min_slots"])
        fund.max_slots = int(request.form["max_slots"])
        fund.expected_interest_rate = Decimal(request.form["expected_interest_rate"])
        fund.maturity_date = datetime.strptime(request.form["maturity_date"], "%Y-%m-%d").date()
        fund.early_exit_charge_percent = Decimal(request.form.get("early_exit_charge_percent") or 0)
        fund.phonepe_number = request.form["phonepe_number"].strip()
        fund.phonepe_upi_id = request.form["phonepe_upi_id"].strip()
        fund.risk_note = request.form.get("risk_note", "").strip()
        fund.is_active = bool(request.form.get("is_active"))
        db.session.commit()
        flash("Fund saved successfully.", "success")
        return redirect(url_for("admin_funds"))
    return render_template("admin/fund_form.html", fund=fund)


@app.route("/admin/investments")
@login_required
@admin_required
def admin_investments():
    investments = Investment.query.order_by(Investment.created_at.desc()).all()
    return render_template("admin/investments.html", investments=investments)


@app.route("/admin/investments/<int:investment_id>/review", methods=["POST"])
@login_required
@admin_required
def review_investment(investment_id):
    inv = Investment.query.get_or_404(investment_id)
    action = request.form.get("action")
    inv.admin_note = request.form.get("admin_note", "").strip()
    inv.reviewed_at = datetime.utcnow()
    if action == "approve":
        inv.status = "approved"
        inv.payment_status = "verified"
    elif action == "reject":
        inv.status = "rejected"
        inv.payment_status = "rejected"
    else:
        flash("Invalid review action.", "error")
        return redirect(url_for("admin_investments"))
    db.session.commit()
    flash("Investment review updated.", "success")
    return redirect(url_for("admin_investments"))


def seed():
    db.create_all()
    admin_email = os.getenv("ADMIN_EMAIL", "admin@yieldnest.local").lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name="Admin", email=admin_email, role="admin")
        admin.set_password(admin_password)
        db.session.add(admin)
    if not Fund.query.first():
        sample = Fund(
            name="Growth Slot Plan",
            tagline="Transparent slot-based maturity plan",
            description="A sample admin-managed plan. Edit or delete this in the admin panel before going live.",
            slot_value=Decimal("1000"),
            min_slots=1,
            max_slots=50,
            expected_interest_rate=Decimal("12"),
            maturity_date=date(date.today().year + 1, 12, 31),
            early_exit_charge_percent=Decimal("3"),
            phonepe_number="9999999999",
            phonepe_upi_id="yourbusiness@ybl",
            risk_note="Returns are expected values and subject to final plan terms, payment verification, and applicable law.",
        )
        db.session.add(sample)
    db.session.commit()


with app.app_context():
    seed()


if __name__ == "__main__":
    app.run(debug=True)
