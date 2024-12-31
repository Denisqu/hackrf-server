import socket
import struct
import math

def generate_sine_wave(size, frequency=1.0, amplitude=1.0):
    sine_wave = []
    for i in range(size):
        x = i / (size - 1) * 2 * math.pi  # Normalize i to the range [0, 2*pi]
        y = amplitude * math.sin(frequency * x)
        sine_wave.extend([x, y])
    return sine_wave

def generate_line(size):
    result = []
    for i in range(size):
        x = i*2
        y = i
        result.extend([x, y])
    return result

def main():
    host = '127.0.0.1'  # Localhost
    port = 12345        # Port to listen on

    # Create a TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the address
    server_socket.bind((host, port))

    # Listen for incoming connections
    server_socket.listen(1)
    print(f"Server listening on {host}:{port}")

    while True:
        # Wait for a connection
        print("Waiting for a connection...")
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")

        try:
            # Generate a sine wave
            array_size = 100  # Example size, you can change this
            sine_wave = generate_line(array_size)#generate_sine_wave(array_size)

            # Pack the array size as int32 (little-endian)
            packed_size = struct.pack('<i', len(sine_wave))

            # Pack the sine wave array as little-endian
            packed_sine_wave = struct.pack(f'<{len(sine_wave)}d', *sine_wave)

            # Send the packed size followed by the packed sine wave array
            client_socket.sendall(packed_size + packed_sine_wave)
            print(f"Sent sine wave of size {len(sine_wave)} to {addr}")

        finally:
            # Clean up the connection
            client_socket.close()

if __name__ == "__main__":
    main()
