extends CharacterBody2D

const SPEED = 40
var target = position
var collisions_with = {} #use a dict as a set

func init(char_name: String) -> void:
	name = char_name
	$Label.text = char_name
	visible = true

func set_target(t: Vector2) -> void:
	target = t
	$Sprite2D.position = target

func _physics_process(delta: float) -> void:
	var prev_position = position
	velocity = (target - position).normalized() * SPEED
	move_and_slide()
	
	for i in get_slide_collision_count():
		var c = get_slide_collision(i)
		var obj = c.get_collider()
		if obj is RigidBody2D:
			obj.apply_central_impulse(-c.get_normal() * 80)
		if obj is CharacterBody2D:
			print(obj.name)
			collisions_with[obj.name] = true

	if (target - position).length() < 1:
		position = target
	#print((target - position).length())
	var diff = (position - prev_position)/delta
	$AnimatedSprite2D.walk(diff)
