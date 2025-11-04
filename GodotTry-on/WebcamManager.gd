extends Node

signal frame_received(texture: ImageTexture)
signal connection_changed(connected: bool) 
signal error_message(message: String)
signal masks_list_received(masks: Array)

var udp_socket: PacketPeerUDP
var webcam_connected: bool = false
var server_host: String = "127.0.0.1"
var server_port: int = 9999

# Packet reassembly buffers
# Key: sequence_number, Value: {packets: {packet_index: packet_data}, total: int}
var frame_buffer: Dictionary = {}
var last_sequence: int = -1

# Timing untuk heartbeat (ping)
var ping_interval: float = 2.0  # Kirim ping setiap 2 detik
var last_ping_time: float = 0.0

func _ready():
	connect_to_webcam_server()

func connect_to_webcam_server():
	udp_socket = PacketPeerUDP.new()
	
	# Bind to local port 0 (OS will assign an available port) untuk listening
	var bind_result = udp_socket.bind(0, "127.0.0.1")
	if bind_result != OK:
		print("❌ Failed to bind UDP socket: %s" % error_string(bind_result))
		error_message.emit("Failed to bind UDP socket")
		return
	
	# Set destination address untuk mengirim ping ke server
	udp_socket.set_dest_address(server_host, server_port)
	
	print("✅ UDP socket created and bound, connecting to server at %s:%d..." % [server_host, server_port])
	set_process(true)
	last_ping_time = 0.0
	webcam_connected = true
	connection_changed.emit(true)
	
	# Kirim ping pertama untuk register
	_send_ping()

func _process(delta):
	if not udp_socket:
		return
	
	# Kirim ping/heartbeat setiap 2 detik untuk register di server
	last_ping_time += delta
	if last_ping_time >= ping_interval:
		_send_ping()
		last_ping_time = 0.0
	
	# Terima paket UDP
	while udp_socket.get_available_packet_count() > 0:
		var packet = udp_socket.get_packet()
		if packet.size() > 0:
			if _maybe_control_message(packet):
				continue
			_process_udp_packet(packet)

func _send_ping():
	"""Kirim ping ke server untuk register sebagai client."""
	if udp_socket:
		var ping_data = "ping".to_utf8_buffer()
		udp_socket.set_dest_address(server_host, server_port)
		if udp_socket.put_packet(ping_data) != OK:
			print("⚠️ Failed to send ping")

func send_clothing_selection(clothing_name: String):
	"""Kirim pilihan pakaian ke server untuk di-apply pada overlay."""
	if not udp_socket:
		print("❌ UDP socket not ready")
		return
	
	var msg = ("clothing:" + clothing_name).to_utf8_buffer()
	udp_socket.set_dest_address(server_host, server_port)
	if udp_socket.put_packet(msg) != OK:
		print("⚠️ Failed to send clothing selection")
	else:
		print("👕 Sent clothing selection to server: %s" % clothing_name)

func request_masks_list():
	"""Minta daftar masker dari server; server akan balas JSON {"masks": [..]}"""
	if not udp_socket:
		print("❌ UDP socket not ready (request_masks_list)")
		return
	var data: PackedByteArray = "list_masks".to_utf8_buffer()
	udp_socket.set_dest_address(server_host, server_port)
	if udp_socket.put_packet(data) != OK:
		print("⚠️ Failed to send list_masks request")

func send_settings(scale: float, offset_x: float, offset_y: float) -> void:
	"""Kirim pengaturan overlay masker ke server."""
	if not udp_socket:
		print("❌ UDP socket not ready (settings)")
		return
	var msg_str := "settings:scale=%.3f;offset_x=%.3f;offset_y=%.3f" % [scale, offset_x, offset_y]
	var data: PackedByteArray = msg_str.to_utf8_buffer()
	udp_socket.set_dest_address(server_host, server_port)
	if udp_socket.put_packet(data) != OK:
		print("⚠️ Failed to send settings")
	else:
		# Throttle log volume by not printing every frame; this is a one-liner info
		pass

func _process_udp_packet(packet: PackedByteArray):	
	"""
	Parse UDP packet dengan format (BIG-ENDIAN dari Python):
	[4 bytes: sequence_number][4 bytes: total_packets][4 bytes: packet_index][remaining: frame_data]
	"""
	if packet.size() < 12:
		# Bukan paket frame; sudah dicoba sebagai kontrol di _maybe_control_message
		return
	
	# Decode big-endian integers (dari Python struct.pack("!III", ...))
	# Godot decode_u32 uses little-endian, jadi kita harus reverse bytes atau pakai manual parsing
	var sequence_number = (packet[0] << 24) | (packet[1] << 16) | (packet[2] << 8) | packet[3]
	var total_packets = (packet[4] << 24) | (packet[5] << 16) | (packet[6] << 8) | packet[7]
	var packet_index = (packet[8] << 24) | (packet[9] << 16) | (packet[10] << 8) | packet[11]

	# Validasi header agar tidak salah mengira pesan kontrol sebagai frame
	if total_packets <= 0 or total_packets > 10000 or packet_index < 0 or packet_index >= total_packets:
		# Kemungkinan ini pesan kontrol teks; coba parse
		if _maybe_control_message(packet):
			return
		# Jika bukan kontrol, buang
		return
	
	# Extract frame data (semua bytes setelah header)
	var frame_data = packet.slice(12)
	
	print("📦 Packet: seq=%d, %d/%d, %d bytes" % [sequence_number, packet_index + 1, total_packets, frame_data.size()])
	
	# Initialize buffer untuk sequence ini jika belum ada
	if sequence_number not in frame_buffer:
		frame_buffer[sequence_number] = {
			"packets": {},
			"total": total_packets
		}
		print("📊 New sequence buffer created: seq=%d, expecting %d packets" % [sequence_number, total_packets])
	
	# Store packet
	frame_buffer[sequence_number]["packets"][packet_index] = frame_data
	var packets_received = frame_buffer[sequence_number]["packets"].size()
	print("   Stored packet %d, have %d/%d" % [packet_index, packets_received, total_packets])
	
	# Check apakah semua packet sudah diterima
	var buffer_entry = frame_buffer[sequence_number]
	if buffer_entry["packets"].size() == buffer_entry["total"]:
		print("✅ Frame complete! Reassembling %d packets..." % buffer_entry["total"])
		
		# Reconstruct frame
		var complete_frame = PackedByteArray()
		for i in range(buffer_entry["total"]):
			if i in buffer_entry["packets"]:
				complete_frame.append_array(buffer_entry["packets"][i])
			else:
				print("❌ Missing packet %d for sequence %d" % [i, sequence_number])
				frame_buffer.erase(sequence_number)
				return
		
		print("📦 Frame reassembled: %d bytes total" % complete_frame.size())
		
		# Process complete frame
		_process_frame(complete_frame)
		
		# Cleanup old buffers (keep last 5 sequences untuk safety)
		if frame_buffer.size() > 5:
			var oldest_seq = sequence_number - 5
			if oldest_seq >= 0 and oldest_seq in frame_buffer:
				frame_buffer.erase(oldest_seq)

func _maybe_control_message(packet: PackedByteArray) -> bool:
	"""Coba decode paket sebagai pesan kontrol JSON dari server. Return true jika sudah ditangani."""
	# Optimisasi: jika byte pertama adalah '{' maka kemungkinan besar JSON
	if packet.size() == 0:
		return false
	var first := packet[0]
	if first != int('{'.to_utf8_buffer()[0]):
		# Bisa jadi teks lain; tetap coba decode kecil (< 512 bytes)
		if packet.size() > 512:
			return false
	var text := ""
	var ok := true
	# Coba decode utf-8
	# In Godot 4, PackedByteArray has get_string_from_utf8 via String(...)? Use built-in conversion
	# Use a try-like guard: if decoding fails, we consider it not control.
	text = packet.get_string_from_utf8()
	if text == "":
		# Could be binary frame packet
		return false
	text = text.strip_edges()
	if text.begins_with("{") and text.ends_with("}"):
		# Parse simple JSON for masks list
		var json := JSON.new()
		var res := json.parse(text)
		if res == OK:
			var obj = json.data
			if typeof(obj) == TYPE_DICTIONARY and obj.has("masks"):
				var masks = obj["masks"]
				if typeof(masks) == TYPE_ARRAY:
					masks_list_received.emit(masks)
					return true
	return false

func _process_frame(jpeg_data: PackedByteArray):
	"""Decode JPEG data dan emit frame_received signal."""
	print("🎬 Processing frame: %d bytes" % jpeg_data.size())
	
	if jpeg_data.size() == 0:
		print("❌ Empty frame data")
		return
	
	var image = Image.new()
	var load_error = image.load_jpg_from_buffer(jpeg_data)
	
	if load_error == OK:
		var texture = ImageTexture.create_from_image(image)
		print("✅ JPEG decoded successfully: %dx%d" % [image.get_width(), image.get_height()])
		print("🔔 Emitting frame_received signal...")
		frame_received.emit(texture)
		print("✅ Signal emitted!")
	else:
		print("❌ JPEG load error: %s" % error_string(load_error))
		error_message.emit("Failed to decode JPEG: %s" % error_string(load_error))

func disconnect_from_server():
	if udp_socket:
		udp_socket.close()
		udp_socket = null
	webcam_connected = false
	connection_changed.emit(false)
	set_process(false)
	frame_buffer.clear()
	print("✅ Disconnected from server")

func _emit_error(message: String):
	error_message.emit(message)

func get_connection_status() -> bool:
	return webcam_connected

func _notification(what):
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		disconnect_from_server()
