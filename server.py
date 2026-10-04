#!/usr/bin/env python3
from flask import Flask, request, jsonify, render_template_string
from flask_sock import Sock
import random
import json
import time
import threading

app = Flask(__name__, static_url_path='', static_folder='static')
sock = Sock(app)

# Positions/state of each client
clients = {}

# Connected WebSocket clients
websocket_clients = set()

character_ttl = 4 * 60 * 60 # characters expire after 4 hours
cleanup_check_time = 60 # check every 1 minute

canvas_width, canvas_height = 800, 600
character_width, character_height = 16, 32
text_height = 10

min_x = 2
min_y = 2 + text_height
max_x = canvas_width - character_width - 2
max_y = canvas_height - character_height - 2


def get_character_rects(character):
    """
    Return the physical rectangles that make up the character.

    Each tuple is:
        (x, y, width, height)
    """

    x = character['x']
    y = character['y']

    return [
        # Head
        (x + 4, y,      8, 8),

        # Body
        (x + 4, y + 8,  8, 12),

        # Left arm
        (x,     y + 8,  4, 12),

        # Right arm
        (x + 12, y + 8, 4, 12),

        # Left leg
        (x + 4, y + 20, 4, 12),

        # Right leg
        (x + 8, y + 20, 4, 12),
    ]


def rects_overlap(a, b):
    """Return True if two rectangles overlap."""

    ax, ay, aw, ah = a
    bx, by, bw, bh = b

    return (
        ax < bx + bw and
        ax + aw > bx and
        ay < by + bh and
        ay + ah > by
    )


def check_collision(a, b):
    """
    Return True if any physical part of character A overlaps
    any physical part of character B.
    """

    a_rects = get_character_rects(a)
    b_rects = get_character_rects(b)

    for a_rect in a_rects:
        for b_rect in b_rects:
            if rects_overlap(a_rect, b_rect):
                return True

    return False


def get_character_center(character):
    """Return the center of a character."""

    return (
        character['x'] + character_width / 2,
        character['y'] + character_height / 2
    )


def update_collisions():
    """
    Calculate all character collisions.

    Collision detection happens exclusively on the backend.

    Each character gets a list of collision points. This allows a
    character to collide with multiple other characters at once.
    """

    # Reset collision state
    for client in clients.values():
        client['collision'] = False
        client['collision_points'] = []

    names = list(clients.keys())

    # Check every unique pair
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            name_a = names[i]
            name_b = names[j]

            a = clients[name_a]
            b = clients[name_b]

            if not check_collision(a, b):
                continue

            a['collision'] = True
            b['collision'] = True

            # Center of each character
            a_center_x, a_center_y = get_character_center(a)
            b_center_x, b_center_y = get_character_center(b)

            # Collision indicator is halfway between the
            # centers of the two colliding characters.
            collision_x = (a_center_x + b_center_x) / 2
            collision_y = (a_center_y + b_center_y) / 2

            # Add point to character A
            a['collision_points'].append({
                'x': collision_x,
                'y': collision_y,
                'with': name_b
            })

            # Add point to character B
            b['collision_points'].append({
                'x': collision_x,
                'y': collision_y,
                'with': name_a
            })


def get_positions_json():
    """
    Serialize the current positions for WebSocket clients.
    """

    return json.dumps({
        'type': 'positions',
        'positions': clients
    })


def broadcast_positions():
    """
    Send the current positions to every connected WebSocket client.

    Dead connections are removed.
    """

    message = get_positions_json()

    disconnected = set()

    for ws in websocket_clients:
        try:
            ws.send(message)
        except Exception:
            disconnected.add(ws)

    for ws in disconnected:
        websocket_clients.discard(ws)


def cleanup_expired_clients():
    while True:
        time.sleep(cleanup_check_time)

        now = time.time()
        expired = []

        for name, client in clients.items():
            if now - client['last_update'] >= character_ttl:
                expired.append(name)

        if not expired:
            continue

        for name in expired:
            del clients[name]

        update_collisions()
        broadcast_positions()


@app.route('/', methods=['GET'])
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Pico Workshop</title>
</head>

<body>

<canvas
    id="canvas"
    width="{{ canvas_width }}"
    height="{{ canvas_height }}"
    style="border:1px solid #000; width:100%">
</canvas>

<script>

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

const protocol =
    window.location.protocol === 'https:' ? 'wss:' : 'ws:';

const socket = new WebSocket(
    protocol + '//' + window.location.host + '/ws'
);


socket.onopen = function() {
    console.log('WebSocket connected');
};


socket.onclose = function() {
    console.log('WebSocket disconnected');
};


socket.onerror = function(error) {
    console.error('WebSocket error:', error);
};

const cyrb53 = (str, seed = 0) => {
    let h1 = 0xdeadbeef ^ seed, h2 = 0x41c6ce57 ^ seed;

    for(let i = 0, ch; i < str.length; i++) {
        ch = str.charCodeAt(i);
        h1 = Math.imul(h1 ^ ch, 2654435761);
        h2 = Math.imul(h2 ^ ch, 1597334677);
    }

    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);

    return 4294967296 * (2097151 & h2) + (h1 >>> 0);
};


function drawCharacter(x, y, name) {
    const hash = cyrb53(name);

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
    ctx.fillRect(x + 4, y, 8, 8);

    // Body
    ctx.fillStyle = bodyColor;
    ctx.fillRect(x + 4, y + 8, 8, 12);

    // Arms
    ctx.fillStyle = armColor;
    ctx.fillRect(x, y + 8, 4, 12);
    ctx.fillRect(x + 12, y + 8, 4, 12);

    // Legs
    ctx.fillStyle = legColor;
    ctx.fillRect(x + 4, y + 20, 4, 12);
    ctx.fillRect(x + 8, y + 20, 4, 12);

    // Border
    ctx.strokeStyle = '#000';
    ctx.strokeRect(x + 4, y, 8, 32);
    ctx.strokeRect(x, y + 8, 16, 12);

    // Name
    ctx.fillStyle = '#000';
    ctx.fillText(name, x, y - 2);
}


function drawCollisionPoint(x, y) {
    ctx.beginPath();

    ctx.arc(x, y, 5, 0, Math.PI * 2);

    ctx.fillStyle = 'red';
    ctx.fill();

    ctx.strokeStyle = '#000';
    ctx.stroke();
}


let positions = {};


socket.onmessage = function(event) {

    const message = JSON.parse(event.data);


    if (message.type !== 'positions') {
        return;
    }


    const newPositions = message.positions;


    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw characters
    for (const name in newPositions) {
        const oldPos = positions[name];
        const newPos = newPositions[name];


        if (
            !oldPos ||
            newPos.x !== oldPos.x ||
            newPos.y !== oldPos.y
        ) {
            console.log(
                `${name} moved to ` +
                `(${newPos.x}, ${newPos.y}), ` +
                `collision: ${newPos.collision}`
            );
        }

        drawCharacter(newPos.x, newPos.y, name);
    }


    //Draw collision points supplied by the backend.
    const drawnPoints = new Set();

    for (const name in newPositions) {
        const character = newPositions[name];

        if (!character.collision) {
            continue;
        }

        for (const point of character.collision_points) {

            // Both characters receive the same collision point,
            // so prevent drawing it twice.
            const key = `${point.x},${point.y}`;

            if (drawnPoints.has(key)) {
                continue;
            }

            drawnPoints.add(key);

            drawCollisionPoint(point.x, point.y);
        }
    }

    positions = newPositions;
};

</script>

</body>
</html>
''',
        canvas_width=canvas_width,
        canvas_height=canvas_height
    )


@app.route('/position', methods=['POST'])
def update_position():
    data = request.json

    name = data.get('name')
    dx = data.get('dx', 0) * 10
    dy = data.get('dy', 0) * -10

    if name not in clients:
        clients[name] = {
            'x': random.randint(min_x, max_x),
            'y': random.randint(min_y, max_y),
            'collision': False,
            'collision_points': [],
            'last_update': time.time()
        }

    clients[name]['last_update'] = time.time()

    # Update client's position with bounds checking
    clients[name]['x'] = min(
        max(clients[name]['x'] + dx, min_x),
        max_x
    )

    clients[name]['y'] = min(
        max(clients[name]['y'] + dy, min_y),
        max_y
    )


    # Calculate collisions
    update_collisions()


    # Tell all WebSocket clients about the new state
    broadcast_positions()


    # Return the moved character's collision state
    return jsonify(
        # name=name,
        x=clients[name]['x'],
        y=clients[name]['y'],
        # collision=clients[name]['collision'],
        # collision_points=clients[name]['collision_points'],
        collisions_with=[p['with'] for p in clients[name]['collision_points']]
    )


@sock.route('/ws')
def websocket(ws):

    websocket_clients.add(ws)

    try:

        # Immediately send the current state
        ws.send(get_positions_json())


        # Keep the connection alive.
        #
        # We don't actually need messages from the browser;
        # movement happens through /position.
        while True:

            message = ws.receive()

            if message is None:
                break

    except Exception:
        pass

    finally:
        websocket_clients.discard(ws)


if __name__ == '__main__':
    cleanup_thread = threading.Thread(
        target=cleanup_expired_clients,
        daemon=True
    )
    cleanup_thread.start()

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=False
    )
