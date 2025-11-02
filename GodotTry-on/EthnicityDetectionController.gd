extends Control
# Virtual Try-On App Controller
# Displays raw webcam feed first, applies clothing only when user clicks

@onready var webcam_feed = $MainContainer/CameraPanel/CameraVBox/WebcamFeed
@onready var camera_status_label = $MainContainer/CameraPanel/CameraVBox/WebcamFeed/CameraStatusLabel
@onready var status_label = $MainContainer/CameraPanel/CameraVBox/StatusContainer/StatusLabel
@onready var info_label = $MainContainer/CameraPanel/CameraVBox/StatusContainer/InfoLabel
@onready var clothing_container = $MainContainer/ControlsContainer/ButtonContainer

# Webcam Manager - akan di-load secara manual
var webcam_manager: Node

var webcam_frames_received: int = 0

# Data pakaian yang tersedia untuk try-on
var clothing_items = [
	{"name": "T-Shirt", "description": "Kaos Polos"},
	{"name": "Kemeja", "description": "Kemeja Formal"},
	{"name": "Jaket", "description": "Jaket Casual"}
]

var current_clothing: String = ""

func _ready():
	print("=== Virtual Try-On App Started ===")
	setup_webcam_manager()
	setup_ui()

func setup_ui():
	"""Setup UI - tampilkan pakaian buttons saja, tidak ada loading"""
	print("Setting up UI...")
	
	status_label.text = "🎥 Ready for Try-On"
	info_label.text = "Select clothing to try"
	
	# Bersihkan button container
	for child in clothing_container.get_children():
		child.queue_free()
	
	# Buat button untuk setiap pakaian
	for item in clothing_items:
		var button = Button.new()
		button.text = item["description"]
		button.custom_minimum_size = Vector2(150, 45)
		button.pressed.connect(func(): _on_clothing_selected(item["name"]))
		clothing_container.add_child(button)

func setup_webcam_manager():
	"""Setup WebcamManager untuk real webcam"""
	print("=== Setting up WebcamManager ===")
	
	# Verifikasi node tersedia
	if not webcam_feed:
		print("ERROR: webcam_feed node not found!")
		return
	
	if not camera_status_label:
		print("ERROR: camera_status_label node not found!")
		return
	
	# Setup placeholder image dulu
	setup_webcam_placeholder()
	
	# Load WebcamManager script
	var webcam_script = load("res://WebcamManager.gd")
	if webcam_script == null:
		print("Error: Could not load WebcamManager.gd")
		camera_status_label.text = "Error: WebcamManager tidak ditemukan"
		camera_status_label.modulate = Color(1, 0, 0, 0.8)
		return
	
	print("Creating WebcamManager instance...")
	webcam_manager = webcam_script.new()
	
	# Connect signals SEBELUM add_child (sebelum _ready() dipanggil)
	print("Connecting signals...")
	if webcam_manager.has_signal("frame_received"):
		webcam_manager.frame_received.connect(_on_webcam_frame_received)
		print("✅ frame_received signal connected")
	else:
		print("❌ frame_received signal not found")
	
	if webcam_manager.has_signal("connection_changed"):
		webcam_manager.connection_changed.connect(_on_webcam_connection_changed)
		print("✅ connection_changed signal connected")
	else:
		print("❌ connection_changed signal not found")
	
	if webcam_manager.has_signal("error_message"):
		webcam_manager.error_message.connect(_on_webcam_error)
		print("✅ error_message signal connected")
	else:
		print("❌ error_message signal not found")
	
	# Sekarang add ke scene (akan trigger _ready() dan emit signals)
	add_child(webcam_manager)
	
	# Update status
	camera_status_label.text = "🔗 Connecting..."
	camera_status_label.modulate = Color(1, 1, 0, 0.8)

func setup_webcam_placeholder():
	"""Buat placeholder image untuk webcam"""
	var placeholder_image = Image.create(480, 360, false, Image.FORMAT_RGBA8)
	placeholder_image.fill(Color(0.2, 0.2, 0.3, 1.0))
	
	# Buat border
	for x in range(480):
		for y in range(8):
			placeholder_image.set_pixel(x, y, Color(0.4, 0.4, 0.5, 1.0))
			placeholder_image.set_pixel(x, 359-y, Color(0.4, 0.4, 0.5, 1.0))
	
	for y in range(360):
		for x in range(8):
			placeholder_image.set_pixel(x, y, Color(0.4, 0.4, 0.5, 1.0))
			placeholder_image.set_pixel(479-x, y, Color(0.4, 0.4, 0.5, 1.0))
	
	var placeholder_texture = ImageTexture.new()
	placeholder_texture.set_image(placeholder_image)
	webcam_feed.texture = placeholder_texture

func _on_webcam_frame_received(texture: ImageTexture):
	"""Callback ketika frame webcam diterima"""
	print("👀 Frame received callback triggered!")
	
	if not webcam_feed:
		print("ERROR: webcam_feed node is null!")
		return
	
	print("📺 Updating webcam_feed texture...")
	webcam_feed.texture = texture
	webcam_frames_received += 1
	print("📊 Frame count: %d" % webcam_frames_received)
	
	# Update status untuk menunjukkan webcam aktif
	if webcam_frames_received == 1:
		print("✅ First frame received - updating UI!")
		camera_status_label.text = "📹 Live"
		camera_status_label.modulate = Color(0, 1, 0, 0.9)
		print("✅ Status label updated to LIVE")
	elif webcam_frames_received % 30 == 0:
		camera_status_label.text = "📹 Live"

func _on_webcam_connection_changed(connected: bool):
	"""Callback ketika status koneksi webcam berubah"""
	if connected:
		camera_status_label.text = "✅ Server Terhubung"
		camera_status_label.modulate = Color(0, 1, 0, 0.9)
		print("✅ Webcam server connected")
	else:
		camera_status_label.text = "❌ Server Terputus"
		camera_status_label.modulate = Color(1, 0, 0, 0.9)
		camera_status_label.visible = true
		print("❌ Webcam server disconnected")
		
		# Coba reconnect
		if webcam_manager and not webcam_manager.get_connection_status():
			var reconnect_timer = Timer.new()
			reconnect_timer.wait_time = 3.0
			reconnect_timer.one_shot = true
			reconnect_timer.timeout.connect(func():
				if is_inside_tree() and webcam_manager and not webcam_manager.get_connection_status():
					camera_status_label.text = "🔄 Reconnecting..."
					camera_status_label.modulate = Color(1, 1, 0, 0.9)
					webcam_manager.connect_to_webcam_server()
				reconnect_timer.queue_free()
			)
			add_child(reconnect_timer)
			reconnect_timer.start()

func _on_webcam_error(message: String):
	"""Callback ketika terjadi error webcam"""
	camera_status_label.text = "❌ Error: " + message
	camera_status_label.modulate = Color(1, 0, 0, 0.9)
	camera_status_label.visible = true
	print("❌ Webcam Error: " + message)

func _on_clothing_selected(clothing_name: String):
	"""Handle pemilihan pakaian"""
	print("👕 Selected clothing: " + clothing_name)
	current_clothing = clothing_name
	info_label.text = "Applying: " + clothing_name
	
	# Visual feedback
	status_label.text = "👕 " + clothing_name
	
	# Kirim pilihan pakaian ke server
	if webcam_manager and webcam_manager.has_method("send_clothing_selection"):
		webcam_manager.send_clothing_selection(clothing_name)
		print("📤 Sent clothing selection to server")
	else:
		print("⚠️ Cannot send clothing selection (webcam_manager not ready)")

func cleanup_resources():
	"""Bersihkan resources sebelum keluar"""
	print("=== Cleaning up resources ===")
	
	if webcam_manager:
		print("Disconnecting webcam manager...")
		if webcam_manager.has_method("disconnect_from_server"):
			webcam_manager.disconnect_from_server()
		if is_inside_tree():
			webcam_manager.queue_free()
		webcam_manager = null
	
	print("✅ Cleanup complete")

func _notification(what):
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		cleanup_resources()
