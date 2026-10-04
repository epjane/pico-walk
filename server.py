#!/usr/bin/env python3
from flask import Flask, Response, request, jsonify, render_template_string
from flask_socketio import SocketIO, emit
import random

app = Flask(__name__, static_url_path='', static_folder='static')
socketio = SocketIO(app)

# This dict will hold the positions of each client
clients = {}

#canvas_width, canvas_height = 1200, 1000
canvas_width, canvas_height = 800, 600
character_width, character_height = 16, 32
text_height = 10

min_x = 2
min_y = 2 + text_height
max_x = canvas_width - character_width - 2
max_y = canvas_height - character_height - 2

@app.route('/', methods=['GET'])
def index():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <script src="/socket.io.4.7.2.js"></script>
        </head>
        <body>
            <canvas id="canvas" width="'''+str(canvas_width)+'''" height="'''+str(canvas_height)+'''" style="border:1px solid #000; width: 100%"></canvas>
            <script>
const socket = io.connect('http://localhost:5000');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

const cyrb53 = (str, seed = 0) => {
    let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;
    for(let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1  = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2  = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);

    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};

//function sha256(str) {
//    return await window.crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
//}

function drawCharacter(x, y, name) {
    const hash = cyrb53(name); //name.split('').reduce((acc, char) => char.charCodeAt(0) + ((acc << 5) - acc), 0);

    const randomColorFromHash = (shift) => {
        const red = ((hash >> (shift + 16)) & 0xFF).toString(16).padStart(2, '0');
        const green = ((hash >> (shift + 8)) & 0xFF).toString(16).padStart(2, '0');
        const blue = ((hash >> (shift + 0)) & 0xFF).toString(16).padStart(2, '0');
        return `#${red}${green}${blue}`;
    };

    const headColor = randomColorFromHash(0);
    const bodyColor = randomColorFromHash(5);
    const armColor = randomColorFromHash(10);
    const legColor = randomColorFromHash(15);

    // Head
    ctx.fillStyle = headColor;
    ctx.fillRect(x+4, y, 8, 8);

    // Body
    ctx.fillStyle = bodyColor;
    ctx.fillRect(x+4, y+8, 8, 12);

    // Arms
    ctx.fillStyle = armColor;
    ctx.fillRect(x, y+8, 4, 12); // left
    ctx.fillRect(x+12, y+8, 4, 12); // right

    // Legs
    ctx.fillStyle = legColor;
    ctx.fillRect(x+4, y+20, 4, 12); // left
    ctx.fillRect(x+8, y+20, 4, 12); // right

    // Border
    ctx.strokeStyle = '#000';
    //ctx.strokeRect(x, y, 16, 32);
    ctx.strokeRect(x+4, y, 8, 32);
    ctx.strokeRect(x, y+8, 16, 12);

    //ctx.beginPath();
    //ctx.moveTo(x+4, y);
    //ctx.lineTo(x+4, y+8);
    //ctx.lineTo(x, y+8);
    //ctx.lineTo(x, y+8+12);
    //ctx.lineTo(x+4, y+8+12);
    //ctx.lineTo(x+4, y+8+12+12);
    //ctx.lineTo(x+4+8, y+8+12+12);
    //ctx.lineTo(x+4+8, y+8+12);
    //ctx.lineTo(x+4+8+4, y+8+12);
    //ctx.lineTo(x+4+8+4, y+8);
    //ctx.lineTo(x+4+8, y+8);
    //ctx.lineTo(x+4+8, y);
    //ctx.lineTo(x+4, y);
    //ctx.stroke();
    ctx.fillText(name, x, y-2);
}

var positions = {}

socket.on('update_positions', function(new_positions) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let name in new_positions) {
        const old_pos = positions[name];
        const new_pos = new_positions[name];
        if (!old_pos || new_pos.x !== old_pos.x || new_pos.y !== old_pos.y) {
          console.log(`${name} moved to (${new_pos.x}, ${new_pos.y})`)
        }
        drawCharacter(new_pos.x, new_pos.y, name);
    }
    positions = new_positions;
});
            </script>
        </body>
        </html>
    ''')

@app.route('/position', methods=['POST'])
def update_position():
    global clients

    data = request.json
    name = data.get('name')
    x_delta = data.get('x', 0) * 10
    y_delta = data.get('y', 0) * -10

    if name not in clients:
        clients[name] = {'x': random.randint(0, canvas_width), 'y': random.randint(0, canvas_height)}

    # Update client's position with bounds checking
    clients[name]['x'] = min(max(clients[name]['x'] + x_delta, min_x), max_x)
    clients[name]['y'] = min(max(clients[name]['y'] + y_delta, min_y), max_y)

    # Notify all connected clients to update positions
    socketio.emit('update_positions', clients)

    return jsonify(name=name, x=clients[name]['x'], y=clients[name]['y'])


@socketio.on('connect')
def send_initial_positions():
    emit('update_positions', clients, broadcast=False)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0')
