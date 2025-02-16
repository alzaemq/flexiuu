from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import stripe

app = Flask(__name__)
# Stripe Configuration
stripe.api_key = "sk_test_51QquA5P7xZsRQwo3pRvi3mxJR7lSDt0t1fajTJMSmELxuao4lQgg2L1S6wPivuJXJG6JTWgV5qywvhOaNtvKxTT700vYsjz7B4"
YOUR_DOMAIN = "http://127.0.0.1:5000"
# Create the extension
db = SQLAlchemy()
app.config['SECRET_KEY'] = 'your-very-secret-key'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shop.db"
db.init_app(app)
# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
admin = Admin(app)
with app.app_context():
    class User(db.Model, UserMixin):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String, nullable=False)
        password = db.Column(db.String, nullable=False)
        email = db.Column(db.String, nullable=False)
        role = db.Column(db.String, default="user")


    class Product(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String, nullable=False)
        price = db.Column(db.Float())
        quantity = db.Column(db.Integer)
        image_link = db.Column(db.String(1000))


    db.create_all()
admin.add_view(ModelView(Product, db.session))
admin.add_view(ModelView(User, db.session))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def start():
    all_products = Product.query.all()
    return render_template("index.html", products=all_products)


@app.route("/add_product", methods=["GET", "POST"])
@login_required
def add():
    if request.method == "POST":
        name = request.form.get("product_name")
        price = request.form.get("price")
        quantity = request.form.get("quantity")
        image = request.form.get("image")
        new_product = Product(name=name, price=price, quantity=quantity, image_link=image)
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('start'))
    return render_template("add_product.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists', 'danger')
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('start'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('start'))


@app.route("/view_product/<int:product_id>")
def view_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('start'))
    return render_template("detail.html", product=product)


# Search functionality
@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("query", "")
    if query:
        products = Product.query.filter(Product.name.ilike(f"%{query}%")).all()
    else:
        products = Product.query.all()
    return render_template("index.html", products=products, search_query=query)


# Cart functionality
@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    print(f"Attempting to add product ID {product_id} to cart")  # Debug statement
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found!', 'danger')
        print(f"Product with ID {product_id} not found in the database.")  # Debug statement
        return redirect(url_for('start'))

    quantity = int(request.form.get('quantity', 1))

    if quantity > product.quantity:
        flash('Selected quantity exceeds available stock!', 'danger')
        return redirect(url_for('view_product', product_id=product_id))

    if 'cart' not in session:
        session['cart'] = {}
    if str(product_id) in session['cart']:
        if session['cart'][str(product_id)] + quantity > product.quantity:
            flash('Selected quantity exceeds available stock!', 'danger')
            return redirect(url_for('view_product', product_id=product_id))
        session['cart'][str(product_id)] += quantity  # Increment quantity if already in cart
        print(f"Incremented quantity of product ID {product_id} in cart")  # Debug statement
    else:
        session['cart'][str(product_id)] = quantity  # Add product to cart
        print(f"Added product ID {product_id} to cart")  # Debug statement
    session.modified = True  # Ensure session is saved
    flash('Product added to cart!', 'success')
    return redirect(url_for('start'))


@app.route('/view_cart')
def view_cart():
    cart_items = []
    total = 0
    if 'cart' in session:
        for product_id, quantity in session['cart'].items():
            product = Product.query.get(int(product_id))
            if product:
                cart_items.append({'product': product, 'quantity': quantity})
                total += product.price * quantity
            else:
                print(f"Product with ID {product_id} not found in the database.")
    else:
        print("No cart in session.")
    return render_template('cart.html', cart_items=cart_items, total=total)


# Clear Cart Route
@app.route('/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    if 'cart' in session:
        session.pop('cart', None)
    flash('Cart cleared successfully!', 'success')
    return redirect(url_for('view_cart'))


# Buy Now Route
@app.route('/buy_now/<int:product_id>', methods=['POST'])
@login_required
def buy_now(product_id):
    product = Product.query.get(product_id)
    if not product:
        flash('Product not found!', 'danger')
        return redirect(url_for('start'))

    quantity = int(request.args.get('quantity', 1))

    if quantity > product.quantity:
        flash('Selected quantity exceeds available stock!', 'danger')
        return redirect(url_for('view_product', product_id=product_id))

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {'name': product.name},
                    'unit_amount': int(product.price * 100),
                },
                'quantity': quantity,
            },
        ],
        mode='payment',
        success_url=YOUR_DOMAIN + '/success',
        cancel_url=YOUR_DOMAIN + '/cancel',
    )
    return redirect(checkout_session.url, code=303)


# Checkout Route
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    cart_items = []
    if 'cart' in session:
        for product_id, quantity in session['cart'].items():
            product = Product.query.get(int(product_id))
            if product:
                cart_items.append({
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': product.name},
                        'unit_amount': int(product.price * 100),
                    },
                    'quantity': quantity,
                })
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=cart_items,
        mode='payment',
        success_url=YOUR_DOMAIN + '/success',
        cancel_url=YOUR_DOMAIN + '/cancel',
    )
    return redirect(checkout_session.url, code=303)


@app.route('/success')
def success():
    return render_template('success.html')


@app.route('/cancel')
def cancel():
    return render_template('cancel.html')


if __name__ == "__main__":
    app.run(debug=True)