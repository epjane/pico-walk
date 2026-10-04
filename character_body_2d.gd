extends CharacterBody2D

const SPEED = 40
var collisions_with = {} #use a dict as a set

func init(char_name: String, pos: Vector2) -> void:
	name = char_name
	position = pos
	$Label.text = char_name

func set_target(target: Vector2) -> void:
	$Sprite2D.position = target

func _physics_process(delta: float) -> void:
	var target = $Sprite2D.position
	var prev_position = position
	velocity = (target - position).normalized() * SPEED
	move_and_slide()
	
	for i in get_slide_collision_count():
		var c = get_slide_collision(i)
		var obj = c.get_collider()
		if obj is RigidBody2D:
			obj.apply_central_impulse(-c.get_normal() * 80)
		#if obj is CharacterBody2D: #uncomment this to only track collisions with other players
		collisions_with[obj.name] = true

	if (target - position).length() < 1:
		position = target
	var diff = (position - prev_position)/delta
	$AnimatedSprite2D.walk(diff)
