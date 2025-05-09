from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import socket, time, datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

# In-memory storage
orders = []
cleared_orders = []

def get_local_ip():
    """Discover the local LAN IP without sending any packets."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

# ——— Home & Navigation ———

@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/quick-order/<int:table_num>')
def quick_order(table_num):
    return render_template('quick_order.html', table_num=table_num)

@app.route('/dashboard')
def dashboard():
    now = datetime.datetime.now().strftime("%d/%m/%y %H:%M")
    return render_template('dashboard.html', now=now)

# ——— Simple Test ———

@app.route('/test')
def test():
    return "Server is up and reachable!", 200

# ——— Order API ———

@app.route('/receive-order', methods=['POST'])
def receive_order():
    data = request.get_json()
    data['timestamp'] = time.time()
    data['recalled'] = False
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
        o = orders[index]
        o['cleared_at'] = time.time()
        cleared_orders.insert(0, o)
        del orders[index]
        return '', 204
    except:
        return 'Not found', 404

@app.route('/undo-clear', methods=['POST'])
def undo_clear():
    if cleared_orders:
        o = cleared_orders.pop(0)
        o['recalled'] = True
        orders.append(o)
    return '', 204

# ——— Overview & Recall Data for Modals ———

@app.route('/overview-data')
def overview_data():
    food = defaultdict(int)
    drink = defaultdict(int)
    for o in orders:
        for itm in o['order']:
            name = itm['name'].lower()
            if any(k in name for k in ("cola","coffee","fanta","water","beer","wine","latte","cappuccino")):
                drink[itm['name']] += itm['quantity']
            else:
                food[itm['name']] += itm['quantity']
    return jsonify({"food": dict(food), "drink": dict(drink)})

@app.route('/recall-data')
def recall_data():
    arr = []
    for o in cleared_orders:
        duration = int(o['cleared_at'] - o['timestamp'])
        arr.append({
            "orderNum": o['orderNum'],
            "items": o['order'],
            "comments": o['comments'],
            "duration": duration
        })
    return jsonify(arr)

# ——— Admin Tools ———

@app.route('/admin')
def admin_tools():
    local_ip = get_local_ip()
    port     = request.environ.get('SERVER_PORT', '5000')
    default  = f"{local_ip}:{port}"
    return render_template('admin.html', default_address=default)

# ——— Licensing & Bundles ———

@app.route('/licensing')
def licensing():
    return render_template('licensing.html')

@app.route('/bundles')
def bundles():
    return render_template('bundles.html')

# ——— 3D & AR Viewers ———

@app.route('/3d_model_viewer')
def model_viewer():
    return render_template('3d_model_viewer.html')

@app.route('/ar_viewer')
def ar_viewer():
    return render_template('ar_viewer.html')

# ——— Launch ———

if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"Flask server running at: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
