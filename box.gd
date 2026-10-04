extends RigidBody2D

# these are configured as "On Change" in the MultiplayerSynchronizer
@export var replicated_position : Vector2
@export var replicated_rotation : float
@export var replicated_linear_velocity : Vector2
@export var replicated_angular_velocity : float

func _integrate_forces(_state : PhysicsDirectBodyState2D) -> void:
	# Synchronizing the physics values directly causes problems since you can't
	# directly update physics values outside of _integrate_forces. This is
	# an attempt to resolve that problem while still being able to use
	# MultiplayerSynchronizer to replicate the values.

	# The object owner makes shadow copies of the physics values.
	# These shadow copies get synchronized by the MultiplyaerSynchronizer
	# The client copies the synchronized shadow values into the 
	# actual physics properties inside integrate_forces
	if is_multiplayer_authority():
		replicated_position = position
		replicated_rotation = rotation
		replicated_linear_velocity = linear_velocity
		replicated_angular_velocity = angular_velocity
	else:
		position = replicated_position
		rotation = replicated_rotation
		linear_velocity = replicated_linear_velocity
		angular_velocity = replicated_angular_velocity
