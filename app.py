from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///car_booking.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    model_year = db.Column(db.String(10))
    price_per_day = db.Column(db.Float, nullable=False)
    seats = db.Column(db.Integer, default=5)
    fuel = db.Column(db.String(30), default="Petrol")
    description = db.Column(db.Text)
    image = db.Column(db.String(300))

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    pickup = db.Column(db.String(200), nullable=False)
    drop_location = db.Column(db.String(200), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    car = Car.query.first()
    return render_template("index.html", car=car)

@app.route("/book", methods=["GET", "POST"])
def book():
    car = Car.query.first()
    if not car:
        flash("Car details are not configured yet.")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            from datetime import date
            start = datetime.strptime(request.form["start_date"], "%Y-%m-%d").date()
            end = datetime.strptime(request.form["end_date"], "%Y-%m-%d").date()
            if end < start:
                flash("End date must be after or equal to start date.")
                return redirect(url_for("book"))

            days = (end - start).days + 1
            overlap = Booking.query.filter(
                Booking.status != "Rejected",
                Booking.start_date <= end,
                Booking.end_date >= start
            ).first()
            if overlap:
                flash("Selected dates are already booked. Please choose another date.")
                return redirect(url_for("book"))

            total = days * car.price_per_day
            booking = Booking(
                customer_name=request.form["customer_name"].strip(),
                phone=request.form["phone"].strip(),
                pickup=request.form["pickup"].strip(),
                drop_location=request.form["drop_location"].strip(),
                start_date=start,
                end_date=end,
                total_amount=total
            )
            db.session.add(booking)
            db.session.commit()
            return render_template("success.html", booking=booking, days=days, car=car)
        except (ValueError, KeyError):
            flash("Please enter valid booking details.")
    return render_template("book.html", car=car)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "admin" and request.form["password"] == "admin123":
            session["admin"] = True
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin")
@admin_required
def dashboard():
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    car = Car.query.first()
    return render_template("dashboard.html", bookings=bookings, car=car)

@app.route("/admin/booking/<int:booking_id>/<status>")
@admin_required
def booking_status(booking_id, status):
    booking = db.get_or_404(Booking, booking_id)
    if status not in ["Confirmed", "Rejected", "Pending"]:
        flash("Invalid status.")
    else:
        booking.status = status
        db.session.commit()
    return redirect(url_for("dashboard"))

@app.route("/admin/car", methods=["POST"])
@admin_required
def update_car():
    car = Car.query.first()
    if not car:
        car = Car()
        db.session.add(car)
    car.name = request.form["name"]
    car.model_year = request.form["model_year"]
    car.price_per_day = float(request.form["price_per_day"])
    car.seats = int(request.form["seats"])
    car.fuel = request.form["fuel"]
    car.description = request.form["description"]
    car.image = request.form["image"]
    db.session.commit()
    flash("Car details updated.")
    return redirect(url_for("dashboard"))

with app.app_context():
    db.create_all()
    if not Car.query.first():
        db.session.add(Car(
            name="Maruti Suzuki Dzire",
            model_year="2022",
            price_per_day=2500,
            seats=5,
            fuel="Petrol/CNG",
            description="Comfortable 5-seater car available for local and outstation booking.",
            image="https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?auto=format&fit=crop&w=1200&q=80"
        ))
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
