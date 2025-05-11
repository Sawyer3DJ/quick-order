from flask import Flask, request, jsonify, render_template, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import socket, time, datetime
from collections import defaultdict
import json

app = Flask(__name__)
CORS(app)

# ─── Database setup ─────────────────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI']   = 'sqlite:///menu.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Dish(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    name      = db.Column(db.String(128), nullable=False)
    category  = db.Column(db.String(32), nullable=False)     # "Food" or "Drink"
    sizes     = db.Column(db.Text, nullable=False)           # JSON: {"Regular":2.5,"Large":3.5}
    model_url = db.Column(db.String(256), nullable=True)     # optional 3D model link

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'sizes': json.loads(self.sizes),
            'model_url': self.model_url
        }

with app.app_context():
    db.create_all()

# ─── Home & Navigation ─────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/quick-order/<int:table_num>')
def quick_order(table_num):
    dishes = Dish.query.order_by(Dish.category, Dish.name).all()
    return render_template('quick_order.html',
                           table_num=table_num,
                           dishes=[d.to_dict() for d in dishes])

@app.route('/dashboard')
def dashboard():
    now = datetime.datetime.now().strftime("%d/%m/%y %H:%M")
    return render_template('dashboard.html', now=now)

# ─── Simple Test ────────────────────────────────────────────────────────────────
@app.route('/test')
def test():
    return "Server is up and reachable!", 200

# ─── Order API ─────────────────────────────────────────────────────────────────
orders = []
cleared_orders = []

@app.route('/receive-order', methods=['POST'])
def receive_order():
    data = request.get_json()
    data['timestamp'] = time.time()
    data['recalled']  = False
    orders.append(data)
    return jsonify({"status": "Order received"}), 200

@app.route('/orders')
def get_orders():
    now = time.time()
    sorted_orders = sorted(orders, key=lambda x: x['timestamp'])
    for o in sorted_orders:
        o['elapsed'] = int(now - o['timestamp'])
    return jsonify(sorted_orders)

@app.route('/clear/<int:index>', methods=['POST'])
def clear_order(index):
    try:
        o = orders.pop(index)
        o['cleared_at'] = time.time()
        cleared_orders.insert(0, o)
        return ('', 204)
    except:
        return ('Not found', 404)

@app.route('/undo-clear', methods=['POST'])
def undo_clear():
    if cleared_orders:
        o = cleared_orders.pop(0)
        o['recalled'] = True
        orders.append(o)
    return ('', 204)

# ─── Overview & Recall Data ────────────────────────────────────────────────────
@app.route('/overview-data')
def overview_data():
    food, drink = defaultdict(int), defaultdict(int)
    for o in orders:
        for itm in o['order']:
            if any(k in itm['name'].lower() for k in ("cola","coffee","fanta","tea","water","beer","wine")):
                drink[itm['name']] += itm['quantity']
            else:
                food[itm['name']] += itm['quantity']
    return jsonify({"food": food, "drink": drink})

@app.route('/recall-data')
def recall_data():
    arr = []
    for o in cleared_orders:
        duration = int(o['cleared_at'] - o['timestamp'])
        arr.append({
            "orderNum": o['orderNum'],
            "items":    o['order'],
            "comments": o['comments'],
            "duration": duration
        })
    return jsonify(arr)

# ─── Admin Tools ───────────────────────────────────────────────────────────────
@app.route('/admin')
def admin_tools():
    host = request.host_url.rstrip('/').replace('http://','').replace('https://','')
    return render_template('admin.html', default_address=host)

# ─── Menu Editor Endpoints ─────────────────────────────────────────────────────
@app.route('/admin/menu')
def menu_editor():
    # serves the React/vanilla-JS powered editor
    return render_template('admin_menu.html')

@app.route('/api/menu', methods=['GET'])
def api_menu_get():
    dishes = Dish.query.order_by(Dish.category, Dish.name).all()
    return jsonify([d.to_dict() for d in dishes])

@app.route('/api/menu', methods=['POST'])
def api_menu_create():
    data = request.get_json()
    d = Dish(name=data['name'],
             category=data['category'],
             sizes=json.dumps(data['sizes']),
             model_url=data.get('model_url'))
    db.session.add(d)
    db.session.commit()
    return jsonify(d.to_dict()), 201

@app.route('/api/menu/<int:dish_id>', methods=['PUT'])
def api_menu_update(dish_id):
    data = request.get_json()
    d = Dish.query.get_or_404(dish_id)
    d.name      = data['name']
    d.category  = data['category']
    d.sizes     = json.dumps(data['sizes'])
    d.model_url = data.get('model_url')
    db.session.commit()
    return jsonify(d.to_dict()), 200

@app.route('/api/menu/<int:dish_id>', methods=['DELETE'])
def api_menu_delete(dish_id):
    d = Dish.query.get_or_404(dish_id)
    db.session.delete(d)
    db.session.commit()
    return ('', 204)

# ─── Monetisation ───────────────────────────────────────────────────────
@app.route('/licensing')
def licensing():   return render_template('licensing.html')
@app.route('/bundles')
def bundles():     return render_template('bundles.html')

@app.route('/security')
def security():
    return render_template('security.html')

@app.route('/distribution')
def distribution():
    return render_template('distribution.html')

@app.route('/marketing')
def marketing():
    return render_template('marketing.html')

@app.route('/monetisation')
def monetisation():
    return render_template('monetisation.html')

# ─── 3D & AR Viewers ───────────────────────────────────────────────────────────
@app.route('/viewer3d')
def model_viewer(): return render_template('3d_model_viewer.html')
@app.route('/viewer-ar')
def ar_viewer():    return render_template('ar_viewer.html')

# ---- Login CSRF stuff ------

from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash

app.secret_key = 'replace_this_with_a_real_secret_key'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Dummy admin user (could later use DB)
users = {'admin': generate_password_hash('password')}

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit   = SubmitField('Login')

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = form.username.data
        if user in users and check_password_hash(users[user], form.password.data):
            login_user(User(user))
            return render_template('admin_menu.html')  # redirect later if needed
        else:
            return render_template('login.html', form=form, error="Invalid credentials")
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return render_template('login.html', form=LoginForm(), error="Logged out")

# Protect the menu editor
@app.route('/admin/menu')
@login_required
def menu_editor():
    return render_template('admin_menu.html')

# ─── Launch ────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f"Flask server running at: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
