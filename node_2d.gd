extends Node2D

var WIDTH = ProjectSettings.get_setting("display/window/size/viewport_width")
var HEIGHT = ProjectSettings.get_setting("display/window/size/viewport_height")
var SIZE = Vector2(WIDTH, HEIGHT)
var SPRITE_SIZE = Vector2(20, 35)

var random = RandomNumberGenerator.new()
var characters = {}
var character_pos = {}
var collisions = {} #collisions since last api call for each character

func create_game_server() -> void:
	var peer = WebSocketMultiplayerPeer.new()
	var res = peer.create_server(16230)
	if res == OK:
		print("created server")
	else:
		print("error creating server: ", res)

	multiplayer.multiplayer_peer = peer
	
	multiplayer.peer_connected.connect(
		func(peer_id: int) -> void:
			print("client connected with peer_id ", peer_id)
			#hello.rpc_id(peer_id, 999)
	)

	multiplayer.peer_disconnected.connect(
		func(peer_id: int) -> void:
			print("client disconnected with peer_id ", peer_id)
	)

func join_game_server() -> void:
	var url = "ws://localhost:16230" #fallback url for development
	
	#find actual url when running in browser
	if OS.has_feature('web'):
		url = JavaScriptBridge.eval('document.location.href').replace('http', 'ws')
		print('detected web, using url: ', url)
	else:
		#only need to wait in debug mode
		print('client waiting to connect...')
		await wait(2)

		# Listen for incoming messages from JavaScript
		#var map_data = JavaScriptBridge.eval('''
			#let params = new URL(document.location).searchParams;
			#let mapData = params.get("map-data");  // Retrieve the map-data query parameter
			#if (mapData) {
				#// Decode the map data to handle special characters properly
				#decodeURIComponent(mapData);
			#} else {
				#"No map data in URL";
			#}
		#''')
		# Check if map data was successfully retrieved
		#print("Map Data from JS: %s" % map_data)

	var peer = WebSocketMultiplayerPeer.new()
	var res = peer.create_client("ws://localhost:16230")
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

@rpc
func hello(data) -> void:
	print('hello ', data, ' ', multiplayer.get_unique_id())
	get_node("AnimatedSprite2D").play()

func get_pos(char_name: String) -> Vector2:
	#print('@@@ ', char_name, ' ', characters, ' ', char_name in characters)
	if char_name in characters:
		return character_pos[char_name]
	else:
		return Vector2(random.randi_range(0, WIDTH), random.randi_range(0, HEIGHT))

func server_update_or_create_character(char_name: String, pos: Vector2) -> void:
	if char_name in characters:
		print("cleared")
		characters[char_name].collisions_with = {}
	update_or_create_character.rpc(char_name, pos)

@rpc("call_local")
func update_or_create_character(char_name: String, pos: Vector2) -> void:
	print('peer ', multiplayer.get_unique_id(), ' updating character: ', char_name)
	#print(multiplayer.is_server(), ' ', characters)
	if not char_name in characters:
		characters[char_name] = $CharacterBody2D.duplicate()
		characters[char_name].init(char_name)
		self.add_child(characters[char_name])
		characters[char_name].position = pos
	characters[char_name].set_target(pos)
	character_pos[char_name] = characters[char_name].position


func wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout

#var boxes = []
func create_boxes() -> void:
	for i in 80:
		var box = $RigidBody2D.duplicate()
		box.visible = true
		box.position = Vector2(WIDTH/2, HEIGHT/2)
		add_child(box)
		#boxes.append(box)

func _ready() -> void:
	var args = Array(OS.get_cmdline_args())
	if args.has("--server"):
		$Label.text = "server"
		print("starting server...")
		create_game_server()
		create_http_server()
	else:
		$Label.text = "client"
		join_game_server()
	#create_boxes()

func _process(_delta: float) -> void:
	for char_name in characters:
		character_pos[char_name] = characters[char_name].position
		collisions[char_name] = characters[char_name].collisions_with.keys()
	#if multiplayer.is_server():
		#server_update_boxes()

func send_hello(data: int) -> void:
	print('sending hello', data)
	hello.rpc(data)

func create_http_server() -> void:
	# simple get request
	# you can do other options like 'post' and 'delete' and so on
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
			self.call_deferred("server_update_or_create_character", data.name, pos)
			var collisions_with = []
			if data.name in collisions:
				collisions_with = collisions[data.name]
				collisions.erase(data.name)
			response.json(200, {"x": pos.x, "y": pos.y, "collisions_with": collisions_with})
			return true
	})

	## handles routes with parameters
	#var paramroute := HttpRouter.new('/:test', {
		#'get': func(request: HttpRequest, response: HttpResponse):
			#response.send(200, 'hello world %s' % request.parameters['test'])
			#return true
	#})

	## static file server example
	var fileroute := HttpFileRouter.new('/', 'export-web')

	## conditional route
	## only return response from this route if they are an admin or whatever other custom logic you want
	#var conditionalroute := HttpRouter.new('/', {
		#'get': func(request: HttpRequest, response: HttpResponse):
			#response.send(200, 'hello world')
			#return true,
		#'condition': func(request: HttpRequest):
			#return false #isAdmin(request)
	#})

	var server = HttpServer.new()
	server.port = 16231

	server.register_router(simpleroute)
	server.register_router(fileroute)
	#server.register_router(paramroute)
	# ... and so on

	add_child(server)

	server.start()
