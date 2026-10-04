extends AnimatedSprite2D

func walk(diff: Vector2) -> void:
	if diff == Vector2(0, 0):
		stop()
	else:
		play()
		
		var lr = "walk_right" if diff.x > 0 else "walk_left"
		var ud = "walk_down" if diff.y > 0 else "walk_up"
		if abs(abs(diff.y) - abs(diff.x)) <= 0.01:
			#avoid flicker
			if diff.y > 0:
				if animation != "walk_down": animation = lr
			else:
				if animation != "walk_up": animation = lr

		elif abs(diff.y) > abs(diff.x):
			animation = ud
		else:
			animation = lr
