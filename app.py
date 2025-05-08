from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import socket, time, datetime
from collections import defaultdict

app = Flask(__name__)
CORS(app)

orders = []
cleared_orders = []

@app.route('/test')
def test():
    return "Server is up!", 200

@app.route('/receive-order', methods=['POST'])
def receive_order():
    data = request.get_json()
    data['timestamp'] = time.time()
    data['recalled'] = False
    orders.append(data)
    return jsonify({"status": "received"}), 200

@app.route('/orders')
def get_orders():
    now = time.time()
    for o in orders:
        o['elapsed'] = int(now - o['timestamp'])
    return jsonify(orders)

@app.route('/clear/<int:i>', methods=['POST'])
def clear_order(i):
    if 0 <= i < len(orders):
        o = orders.pop(i)
        o['cleared_at'] = time.time()
        cleared_orders.insert(0, o)
        return '', 204
    return 'Not found', 404

@app.route('/undo-clear', methods=['POST'])
def undo_clear():
    if cleared_orders:
        o = cleared_orders.pop(0)
        o['recalled'] = True
        orders.append(o)
    return '', 204

@app.route('/recall-specific/<int:i>', methods=['POST'])
def recall_specific(i):
    if 0 <= i < len(cleared_orders):
        o = cleared_orders.pop(i)
        o['recalled'] = True
        orders.append(o)
        return '', 204
    return 'Not found', 404

@app.route('/overview-data')
def overview_data():
    food, drink = defaultdict(int), defaultdict(int)
    for o in orders:
        for it in o['order']:
            if any(dr in it['name'].lower() for dr in 
                   ['cola','coffee','fanta','tea','water','latte','cappuccino','beer','wine']):
                drink[it['name']] += it['quantity']
            else:
                food[it['name']] += it['quantity']
    return jsonify({"food": food, "drink": drink})

@app.route('/recall-data')
def recall_data():
    result = []
    for o in cleared_orders:
        duration = int(o['cleared_at'] - o['timestamp'])
        result.append({
            "orderNum": o['orderNum'],
            "items": o['order'],
            "comments": o['comments'],
            "duration": duration
        })
    return jsonify(result)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/quick-order/<int:table_num>')
def quick_order(table_num):
    return render_template('quick_order.html', table_num=table_num)

@app.route('/admin')
def admin():
    host = request.host_url.rstrip('/')
    host = host.replace(http://',''.replace(http://','')
    return render_template('admin.html', default_address=host)

@app.route('/qr-connect')
def qr_connect():
    return render_template('qr_connect.html')

@app.route('/viewer3d')
def model_viewer():
    return render_template('3d_model_viewer.html')

@app.route('/viewer-ar')
def ar_viewer():
    return render_template('ar_viewer.html')

@app.route('/licensing')
def licensing():
    return render_template('licensing.html')

@app.route('/bundles')
def bundles():
    return render_template('bundles.html')

@app.route('/dashboard')
def dashboard():
    now = datetime.datetime.now().strftime("%d/%m/%y %H:%M")
    return render_template('dashboard.html', now=now)

if __name__ == '__main__':
    local_ip = socket.gethostbyname(socket.gethostname())
    print(f"Flask server running at http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
