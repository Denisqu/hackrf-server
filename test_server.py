import socket
import struct
import math
import binascii
import time
from abc import ABC, abstractmethod

class WaveGenerator(ABC):
    @abstractmethod
    def generate(self, size):
        pass

class SineWaveGenerator(WaveGenerator):
    def __init__(self, frequency=1.0, amplitude=1.0):
        self.frequency = frequency
        self.amplitude = amplitude

    def generate(self, size):
        sine_wave = []
        for i in range(size):
            x = i / (size - 1) * 2 * math.pi  # Normalize i to the range [0, 2*pi]
            y = self.amplitude * math.sin(self.frequency * x)
            sine_wave.extend([y, x])
        return sine_wave

class LineGenerator(WaveGenerator):
    def __init__(self, multiplier):
        self.multiplier = multiplier

    def generate(self, size):
        result = []
        for i in range(size):
            x = i
            y = i + self.multiplier / 10
            result.extend([x, y])
        return result

class DataPacker:
    @staticmethod
    def pack_data(data):
        packed_data = struct.pack(f'>{len(data)}d', *data)
        packed_size = struct.pack('>i', len(packed_data))
        return packed_size + packed_data

class Server:
    def __init__(self, host, port, wave_generator):
        self.host = host
        self.port = port
        self.wave_generator = wave_generator
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

    def start(self):
        print(f"Server listening on {self.host}:{self.port}")
        while True:
            print("Waiting for a connection...")
            client_socket, addr = self.server_socket.accept()
            print(f"Connection from {addr}")
            self.handle_client(client_socket, addr)

    def handle_client(self, client_socket, addr):
        i = 0
        try:
            while True:
                i += 1
                array_size = 100  # Example size, you can change this
                wave_data = self.wave_generator.generate(array_size)
                data_to_send = DataPacker.pack_data(wave_data)
                client_socket.sendall(data_to_send)
                hex_data = binascii.hexlify(data_to_send).decode('utf-8')
                print(f"Sent data to {addr} in hex format: {hex_data}")
                time.sleep(1)
        except (ConnectionResetError, BrokenPipeError):
            print(f"Connection from {addr} was closed.")
        finally:
            client_socket.close()

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345
    wave_generator = LineGenerator(multiplier=1)  # You can switch to SineWaveGenerator if needed
    server = Server(host, port, wave_generator)
    server.start()
