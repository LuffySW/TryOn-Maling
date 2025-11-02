extends Node
class_name WebcamClient

# Sinyal untuk komunikasi dengan UI
signal frame_received(texture: ImageTexture)
signal connection_status_changed(connected: bool)
signal error_occurred(message: String)

var udp_socket: PacketPeerUDP
var connected: bool = false
var server_host: String = "127.0.0.1"
var server_port: int = 9999

# Packet reassembly
var frame_buffer: Dictionary = {}

# Timing untuk heartbeat
var ping_interval: float = 2.0
var last_ping_time: float = 0.0

func _init():
	pass

func connect_to_server() -> bool:
	"""Koneksi ke UDP webcam server"""
	if connected:
		print("✅ Sudah terhubung ke server")
		return true
	
	print("🔗 Mencoba koneksi ke webcam server UDP di %s:%d..." % [server_host, server_port])
	
	udp_socket = PacketPeerUDP.new()
	
	# Set destination address untuk client
	udp_socket.set_dest_address(server_host, server_port)
	
	connected = true
	last_ping_time = 0.0
	
	# Set up processing
	set_process(true)
	
	# Kirim ping pertama untuk register
	_send_ping()
	
	emit_signal("connection_status_changed", true)
	print("✅ Berhasil terhubung ke webcam server UDP")
	return true

func disconnect_from_server():
	"""Putuskan koneksi dari server"""
	if not connected:
		return
	
	print("🔌 Memutuskan koneksi dari webcam server...")
	connected = false
	
	if udp_socket:
		udp_socket.close()
		udp_socket = null
	
	frame_buffer.clear()
	set_process(false)
	
	emit_signal("connection_status_changed", false)
	print("✅ Koneksi terputus")

func _process(delta):
	"""Main process loop"""
	if not connected or not udp_socket:
		return
	
	# Kirim ping untuk register sebagai client
	last_ping_time += delta
	if last_ping_time >= ping_interval:
		_send_ping()
		last_ping_time = 0.0
	
	# Terima paket UDP
	while udp_socket.get_available_packet_count() > 0:
		var packet = udp_socket.get_packet()
		if packet.size() >= 12:
			_process_udp_packet(packet)
		elif packet.size() > 0:
			print("⚠️ Packet terlalu kecil: %d bytes" % packet.size())

func _send_ping():
	"""Kirim ping ke server untuk register"""
	if udp_socket:
		var ping_data = "ping".to_utf8_buffer()
		udp_socket.set_dest_address(server_host, server_port)
		var err = udp_socket.put_packet(ping_data)
		if err != OK:
			print("⚠️ Gagal kirim ping: %s" % error_string(err))

func _process_udp_packet(packet: PackedByteArray):
	"""Parse UDP packet dengan format: [seq][total][index][data]"""
	if packet.size() < 12:
		print("❌ Header packet tidak lengkap")
		return
	
	# Parse header (big-endian)
	var sequence_number = packet.decode_u32(0)
	var total_packets = packet.decode_u32(4)
	var packet_index = packet.decode_u32(8)
	var frame_data = packet.slice(12)
	
	print("📦 Received: seq=%d, packet %d/%d, size=%d bytes" % [sequence_number, packet_index + 1, total_packets, frame_data.size()])
	
	# Initialize buffer untuk sequence ini
	if sequence_number not in frame_buffer:
		frame_buffer[sequence_number] = {
			"packets": {},
			"total": total_packets
		}
	
	# Store packet
	frame_buffer[sequence_number]["packets"][packet_index] = frame_data
	
	# Check apakah frame lengkap
	var buffer_entry = frame_buffer[sequence_number]
	if buffer_entry["packets"].size() == buffer_entry["total"]:
		# Reconstruct frame
		var complete_frame = PackedByteArray()
		for i in range(buffer_entry["total"]):
			if i in buffer_entry["packets"]:
				complete_frame.append_array(buffer_entry["packets"][i])
			else:
				print("❌ Missing packet %d for sequence %d" % [i, sequence_number])
				frame_buffer.erase(sequence_number)
				return
		
		# Process complete frame
		_process_frame_data(complete_frame)
		
		# Cleanup old buffers
		if frame_buffer.size() > 5:
			var oldest_seq = sequence_number - 5
			if oldest_seq >= 0 and oldest_seq in frame_buffer:
				frame_buffer.erase(oldest_seq)

func _process_frame_data(jpeg_data: PackedByteArray):
	"""Decode JPEG data dan emit frame_received signal"""
	if jpeg_data.size() == 0:
		print("❌ Empty frame data")
		return
	
	var image = Image.new()
	var load_result = image.load_jpg_from_buffer(jpeg_data)
	
	if load_result != OK:
		emit_signal("error_occurred", "Gagal decode JPEG: %s" % error_string(load_result))
		return
	
	# Buat texture dari image
	var texture = ImageTexture.create_from_image(image)
	
	# Emit signal dengan texture
	emit_signal("frame_received", texture)
	print("✅ Frame processed: %dx%d" % [image.get_width(), image.get_height()])

func is_webcam_connected() -> bool:
	"""Cek apakah masih terhubung"""
	return connected

func _notification(what):
	if what == NOTIFICATION_PREDELETE:
		disconnect_from_server()
