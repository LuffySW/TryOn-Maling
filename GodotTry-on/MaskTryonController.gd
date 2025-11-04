extends Control
# Virtual Try-On App Controller
# Displays raw webcam feed first, applies clothing only when user clicks

@onready var webcam_feed = $MainContainer/CameraPanel/CameraVBox/WebcamFeed
@onready var camera_status_label = $MainContainer/CameraPanel/CameraVBox/WebcamFeed/CameraStatusLabel
@onready var status_label = $MainContainer/CameraPanel/CameraVBox/StatusContainer/StatusLabel
@onready var info_label = $MainContainer/CameraPanel/CameraVBox/StatusContainer/InfoLabel
@onready var clothing_container = $MainContainer/ControlsContainer/ButtonContainer

# Settings UI
@onready var scale_slider: HSlider = $MainContainer/ControlsContainer/Settings/ScaleContainer/ScaleSlider
@onready var scale_value_label: Label = $MainContainer/ControlsContainer/Settings/ScaleContainer/ScaleValue
@onready var offx_slider: HSlider = $MainContainer/ControlsContainer/Settings/OffsetXContainer/OffsetXSlider
@onready var offx_value_label: Label = $MainContainer/ControlsContainer/Settings/OffsetXContainer/OffsetXValue
@onready var offy_slider: HSlider = $MainContainer/ControlsContainer/Settings/OffsetYContainer/OffsetYSlider
@onready var offy_value_label: Label = $MainContainer/ControlsContainer/Settings/OffsetYContainer/OffsetYValue

# Webcam Manager - akan di-load secara manual
var webcam_manager: Node

var webcam_frames_received: int = 0

# Dynamic list of masks; will be built at runtime from assets
var clothing_items: Array = []

var current_clothing: String = ""

const DEFAULT_SCALE := 1.1
const DEFAULT_OFFX := 0.0
const DEFAULT_OFFY := -0.35

func _ready():
	print("=== Virtual Try-On App Started ===")
	setup_webcam_manager()
	setup_ui()
	_setup_settings_ui()

func setup_ui():
	"""Setup UI - tampilkan pakaian buttons saja, tidak ada loading"""
	print("Setting up UI...")
	
	status_label.text = "🎥 Ready for Try-On"
	info_label.text = "Select clothing to try"
	
	# Bersihkan button container
	for child in clothing_container.get_children():
		child.queue_free()

	# Rebuild from local assets dynamically
	clothing_items = _scan_local_assets_masks()
	if clothing_items.is_empty():
		# Fallback minimal list
		clothing_items = [
			{"name": "none", "description": "None"}
		]
	# Always ensure 'none' exists and is first
	var has_none := false
	for it in clothing_items:
		if String(it.get("name", "")).to_lower() in ["none", "t-shirt", "tshirt"]:
			has_none = true
			break
	if not has_none:
		clothing_items.push_front({"name": "none", "description": "None"})

	for item in clothing_items:
		var btn := Button.new()
		btn.text = String(item.get("description", item.get("name", "Mask")))
		btn.custom_minimum_size = Vector2(150, 45)
		var on_click = func():
			_on_clothing_selected(item)
		btn.pressed.connect(on_click)
		clothing_container.add_child(btn)

func _normalize_key_from_filename(base: String) -> String:
	var key := base.strip_edges().to_lower()
	key = key.replace(" ", "-").replace("_", "-")
	key = key.replace("-removebg-preview", "").replace("-removebg", "")
	# Heuristics mapping
	if key.find("ski") != -1:
		return "ski-mask"
	if key.find("anonymous") != -1 or key.find("anon") != -1:
		return "anonymous-mask"
	if key.find("haggus") != -1:
		return "haggus-mask"
	return key

func _friendly_label_from_filename(base: String) -> String:
	var s := base
	s = s.replace("_", " ").replace("-", " ")
	var parts := s.split(" ")
	for i in range(parts.size()):
		if parts[i].length() > 0:
			parts[i] = parts[i].substr(0,1).to_upper() + parts[i].substr(1)
	return " ".join(parts)

func _scan_local_assets_masks() -> Array:
	var out: Array = []
	var abs_path := ProjectSettings.globalize_path("res://../svm_orb_mask/assets")
	var dir := DirAccess.open(abs_path)
	if dir == null:
		print("⚠️ Local assets folder not found: ", abs_path)
		return out
	dir.list_dir_begin()
	while true:
		var f := dir.get_next()
		if f == "":
			break
		if dir.current_is_dir():
			continue
		if f.to_lower().ends_with(".png"):
			var base := f.get_basename()
			var key := _normalize_key_from_filename(base)
			var label := _friendly_label_from_filename(base)
			out.append({"name": key, "description": label})
	dir.list_dir_end()
	return out

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

	# Receive dynamic masks list from server if available
	if webcam_manager.has_signal("masks_list_received"):
		webcam_manager.masks_list_received.connect(_on_masks_list_received)
		print("✅ masks_list_received signal connected")
	else:
		print("ℹ️ masks_list_received signal not found (older WebcamManager?)")
	
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

func _setup_settings_ui():
	# Set default values and connect change handlers
	scale_slider.value = DEFAULT_SCALE
	offx_slider.value = DEFAULT_OFFX
	offy_slider.value = DEFAULT_OFFY
	_update_setting_labels()

	var on_scale_changed = func(_v):
		_update_setting_labels()
		_send_settings_to_server()
	scale_slider.value_changed.connect(on_scale_changed)

	var on_offx_changed = func(_v):
		_update_setting_labels()
		_send_settings_to_server()
	offx_slider.value_changed.connect(on_offx_changed)

	var on_offy_changed = func(_v):
		_update_setting_labels()
		_send_settings_to_server()
	offy_slider.value_changed.connect(on_offy_changed)
	# Try send once at init
	_send_settings_to_server()

func _update_setting_labels():
	scale_value_label.text = "%.2f" % scale_slider.value
	offx_value_label.text = "%.2f" % offx_slider.value
	offy_value_label.text = "%.2f" % offy_slider.value

func _send_settings_to_server():
	if not is_instance_valid(webcam_manager):
		return
	var scale := float(scale_slider.value)
	var ox := float(offx_slider.value)
	var oy := float(offy_slider.value)
	if webcam_manager.has_method("send_settings"):
		webcam_manager.send_settings(scale, ox, oy)
	else:
		print("⚠️ WebcamManager missing send_settings method")

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
		# Send current settings on first frame
		_send_settings_to_server()
	elif webcam_frames_received % 30 == 0:
		camera_status_label.text = "📹 Live"

func _on_webcam_connection_changed(connected: bool):
	"""Callback ketika status koneksi webcam berubah"""
	if connected:
		camera_status_label.text = "✅ Server Terhubung"
		camera_status_label.modulate = Color(0, 1, 0, 0.9)
		print("✅ Webcam server connected")
		_send_settings_to_server()
		# Request masks list from server (will rebuild UI on receipt)
		if webcam_manager and webcam_manager.has_method("request_masks_list"):
			webcam_manager.request_masks_list()
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
			var on_reconnect_timeout = func():
				if is_inside_tree() and webcam_manager and not webcam_manager.get_connection_status():
					camera_status_label.text = "🔄 Reconnecting..."
					camera_status_label.modulate = Color(1, 1, 0, 0.9)
					webcam_manager.connect_to_webcam_server()
				reconnect_timer.queue_free()
			reconnect_timer.timeout.connect(on_reconnect_timeout)
			add_child(reconnect_timer)
			reconnect_timer.start()

func _on_webcam_error(message: String):
	"""Callback ketika terjadi error webcam"""
	camera_status_label.text = "❌ Error: " + message
	camera_status_label.modulate = Color(1, 0, 0, 0.9)
	camera_status_label.visible = true
	print("❌ Webcam Error: " + message)

func _on_masks_list_received(masks: Array) -> void:
	"""Handle server-provided list of masks and rebuild buttons."""
	print("📥 Received masks list from server: ", masks)
	var items: Array = []
	# Ensure 'none' option at top
	items.append({"name": "none", "description": "None"})
	for m in masks:
		if typeof(m) == TYPE_STRING:
			var key: String = m
			# Skip duplicates/none
			var lower := key.to_lower()
			if lower in ["none", "t-shirt", "tshirt"]:
				continue
			var label := _friendly_label_from_filename(key)
			items.append({"name": key, "description": label})
	# Replace and rebuild UI
	clothing_items = items
	_rebuild_buttons()

func _rebuild_buttons():
	# Clear
	for child in clothing_container.get_children():
		child.queue_free()
	# Rebuild
	for item in clothing_items:
		var btn := Button.new()
		btn.text = String(item.get("description", item.get("name", "Mask")))
		btn.custom_minimum_size = Vector2(150, 45)
		var on_click = func():
			_on_clothing_selected(item)
		btn.pressed.connect(on_click)
		clothing_container.add_child(btn)

func _on_clothing_selected(item: Dictionary):
	"""Handle pemilihan masker berdasarkan nama asset (key)"""
	var mask_key: String = String(item.get("name", "none"))
	var mask_label: String = String(item.get("description", mask_key))
	print("🎭 Selected mask: " + mask_key)
	current_clothing = mask_key
	info_label.text = "Applying: " + mask_label
	status_label.text = "🎭 " + mask_label

	# Kirim pilihan mask (menggunakan API lama 'clothing:' untuk kompatibilitas)
	if webcam_manager and webcam_manager.has_method("send_clothing_selection"):
		webcam_manager.send_clothing_selection(mask_key)
		print("📤 Sent mask selection to server: " + mask_key)
	else:
		print("⚠️ Cannot send mask selection (webcam_manager not ready)")

func _on_reset_settings_pressed():
	scale_slider.value = DEFAULT_SCALE
	offx_slider.value = DEFAULT_OFFX
	offy_slider.value = DEFAULT_OFFY
	_update_setting_labels()
	_send_settings_to_server()

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


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://MainMenu.tscn")
