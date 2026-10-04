extends Node2D

const GAME_PORT = 16230
const HTTP_PORT = 16231

var WIDTH = ProjectSettings.get_setting("display/window/size/viewport_width")
var HEIGHT = ProjectSettings.get_setting("display/window/size/viewport_height")
var SIZE = Vector2(WIDTH, HEIGHT)
var SPRITE_SIZE = Vector2(20, 45) #TODO grab this from Player's CollisionShape2D
const NUM_BOXES = 40

var random = RandomNumberGenerator.new()
var characters = {}
var character_pos = {}
var collisions = {} #collisions since last api call for each character

func create_game_server() -> void:
	var peer = WebSocketMultiplayerPeer.new()
	var res = peer.create_server(GAME_PORT)
	if res == OK:
		print("created server")
	else:
		print("error creating server: ", res)

	multiplayer.multiplayer_peer = peer
	
	multiplayer.peer_connected.connect(
		func(peer_id: int) -> void:
			print("client connected with peer_id ", peer_id)
	)

	multiplayer.peer_disconnected.connect(
		func(peer_id: int) -> void:
			print("client disconnected with peer_id ", peer_id)
	)

func join_game_server() -> void:
	var url = "ws://localhost:" + str(GAME_PORT) #fallback url for development

	#find actual url when running in browser
	if OS.has_feature('web'):
		#you better not serve this over ftp or this will break
		#although ftp doesn't support websockets anyway
		url = JavaScriptBridge.eval('document.location.href')
		url = url.replace('http://', 'ws://')
		url = url.replace('https://', 'wss://')
		print('detected web, using url: ', url)
	else:
		print('client waiting to connect...')
		#have the client wait for a few seconds for the server to start, useful during development.
		#this is not needed in web mode because the server serves the html and js files that
		#comprise the client, so the client can't start unless the server is already running anyway
		await wait(2)

	var peer = WebSocketMultiplayerPeer.new()
	var res = peer.create_client(url)
	if res == OK:
		print("created client")
	else:
		print("error creating client: ", res)

	multiplayer.multiplayer_peer = peer
	
	multiplayer.connected_to_server.connect(
		func() -> void:
			print("connected to server")
	)
	
	multiplayer.connection_failed.connect(
		func() -> void:
			print("connection failed")
	)

func get_pos(char_name: String) -> Vector2:
	if char_name in characters:
		return character_pos[char_name]
	else:
		return Vector2(random.randi_range(0, WIDTH), random.randi_range(0, HEIGHT))

func server_update_or_create_character(char_name: String, pos: Vector2) -> void:
	if char_name in characters:
		character_pos[char_name] = characters[char_name].position
		characters[char_name].collisions_with = {}
	else:
		characters[char_name] = preload("res://player.tscn").instantiate()
		characters[char_name].init(char_name, pos)
		$Players.add_child(characters[char_name])
	characters[char_name].set_target(pos)

func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout

func create_boxes() -> void:
	for i in NUM_BOXES:
		var box = preload("res://box.tscn").instantiate()
		box.position = Vector2(WIDTH/2, HEIGHT/2)
		box.name = 'box' + str(i)
		$Boxes.add_child(box)

func _ready() -> void:
	var args = Array(OS.get_cmdline_args())
	if args.has("--server"):
		$Label.text = "server"
		print("starting server...")
		create_game_server()
		create_http_server()
		create_boxes()
	else:
		$Label.text = "client"
		join_game_server()

func _process(_delta: float) -> void:
	for char_name in characters:
		character_pos[char_name] = characters[char_name].position
		collisions[char_name] = characters[char_name].collisions_with.keys()

func create_http_server() -> void:
	var simpleroute := HttpRouter.new('/position', {
		'post': func(request: HttpRequest, response: HttpResponse):
			print("request: ", request)
			var data = request.get_body_parsed()
			print("data: ", data)
			if data == null:
				response.json(400, {"error": "missing data"})
				return true
			var pos = get_pos(data.name)
			pos += Vector2(data.dx, data.dy)
			pos = pos.clamp(SPRITE_SIZE, SIZE - SPRITE_SIZE)
			#self.call_deferred("create_boxes")
			var collisions_with = []
			if data.name in collisions:
				collisions_with = collisions[data.name]
				collisions.erase(data.name)
			self.call_deferred("server_update_or_create_character", data.name, pos)
			response.json(200, {"x": pos.x, "y": pos.y, "collisions_with": collisions_with})
			return true
	})

	# serve the html export of the game
	var fileroute := HttpFileRouter.new('/', 'export-web')

	var server = HttpServer.new()
	server.port = HTTP_PORT

	server.register_router(simpleroute)
	server.register_router(fileroute)

	add_child(server)
	server.start()
