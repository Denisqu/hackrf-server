# import subprocess
# import csv
# import socket
# import struct
# import math
# import binascii
# import time
# from abc import ABC, abstractmethod


# class HackrfSweepParser:
#     def __init__(self, serverImpl):
#         self.current_buffer = []
#         self.server = serverImpl

#     def buffer_to_packed_points(self, buffer):
#         xs = []
#         ys = []
#         for line in buffer:
#             _, hz_low, hz_high, hz_bin_width, dbs = line
#             for i in range(0, 5):
#                 xs.append((int(hz_low) + float(hz_bin_width) * (i + 1)) / 2)
#                 ys.append(float(dbs[i]))
#         return xs, ys

#     def parse_hackrf_sweep(self):
#         # Команда для запуска hackrf_sweep
#         command = ["hackrf_sweep"]

#         try:
#             # Запуск процесса
#             process = subprocess.Popen(
#                 command,
#                 stdout=subprocess.PIPE,
#                 stderr=subprocess.PIPE,
#                 text=True
#             )

#             print("Запущено hackrf_sweep. Ожидание данных...")

#             # Обработка вывода в реальном времени
#             previous_date_time = None
#             for line in process.stdout:
#                 # Удаляем лишние пробелы и проверяем, содержит ли строка данные
#                 line = line.strip()
#                 if "," in line:
#                     # Разделяем строку на части
#                     fields = line.split(", ")
#                     if len(fields) > 6:  # Проверяем наличие необходимого количества полей
#                         date_time = fields[0] + fields[1]
#                         hz_low = fields[2]
#                         hz_high = fields[3]
#                         hz_bin_width = fields[4]
#                         dbs = [fields[6 + i] for i in range(5)]
#                         self.current_buffer.append((date_time, hz_low, hz_high, hz_bin_width, dbs))
#                         if previous_date_time != date_time:
#                             # todo: send buffer_to_packed_points(current_buffer) to client
#                             self.current_buffer = []
#                         previous_date_time = date_time

#             print("Данные успешно сохранены в hackrf_sweep_output.csv.")

#         except KeyboardInterrupt:
#             print("Остановка выполнения по Ctrl+C.")
#         except Exception as e:
#             print(f"Произошла ошибка: {e}")
#         finally:
#             try:
#                 process.terminate()
#             except Exception:
#                 pass

# class DataPacker:
#     @staticmethod
#     def pack_data(data):
#         packed_data = struct.pack(f'>{len(data)}d', *data)
#         packed_size = struct.pack('>i', len(packed_data))
#         return packed_size + packed_data

# class Server:
#     def __init__(self, host, port, wave_generator):
#         self.host = host
#         self.port = port
#         self.wave_generator = wave_generator
#         self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.server_socket.bind((self.host, self.port))
#         self.server_socket.listen(1)

#     def start(self):
#         print(f"Server listening on {self.host}:{self.port}")
#         while True:
#             print("Waiting for a connection...")
#             client_socket, addr = self.server_socket.accept()
#             print(f"Connection from {addr}")
#             self.handle_client(client_socket, addr)

#     def handle_client(self, client_socket, addr):
#         i = 0
#         try:
#             while True:
#                 i += 1
#                 array_size = 100  # Example size, you can change this
#                 wave_data = self.wave_generator.generate(array_size)
#                 data_to_send = DataPacker.pack_data(wave_data)
#                 client_socket.sendall(data_to_send)
#                 hex_data = binascii.hexlify(data_to_send).decode('utf-8')
#                 print(f"Sent data to {addr} in hex format: {hex_data}")
#                 time.sleep(1)
#         except (ConnectionResetError, BrokenPipeError):
#             print(f"Connection from {addr} was closed.")
#         finally:
#             client_socket.close()


# if __name__ == "__main__":
#     host = '127.0.0.1'
#     port = 12345
#     wave_generator = LineGenerator(multiplier=1)  # You can switch to SineWaveGenerator if needed
#     server = Server(host, port, wave_generator)
#     server.start()
#     parse_hackrf_sweep()


import subprocess
import socket
import struct
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
        self.client_socket = None
        self.client_addr = None

    def start(self):
        print(f"Server listening on {self.host}:{self.port}")
        while True:
            print("Waiting for a connection...")
            self.client_socket, self.client_addr = self.server_socket.accept()
            print(f"Connection from {self.client_addr}")
            self.handle_client()

    def handle_client(self):
        i = 0
        try:
            while True:
                time.sleep(0.25)
        except (ConnectionResetError, BrokenPipeError):
            print(f"Connection from {self.client_addr} was closed.")
        finally:
            self.client_socket.close()

    def send_data(self, data):
        if self.client_socket:
            self.client_socket.sendall(data)

class HackrfSweepParser:
    def __init__(self, server):
        self.current_buffer = []
        self.server = server

    def buffer_to_packed_points(self, buffer):
        result = []
        for line in buffer:
            _, hz_low, hz_high, hz_bin_width, dbs = line
            for i in range(0, 5):
                result.append(float((int(hz_low) + float(hz_bin_width) * (i + 1)) / 2)) #x
                result.append(float(dbs[i])) #y
        return result

    def parse_hackrf_sweep(self):
        # Команда для запуска hackrf_sweep
        command = ["hackrf_sweep"]

        try:
            # Запуск процесса
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            print("Запущено hackrf_sweep. Ожидание данных...")

            # Обработка вывода в реальном времени
            previous_date_time = None
            for line in process.stdout:
                # Удаляем лишние пробелы и проверяем, содержит ли строка данные
                line = line.strip()
                if "," in line:
                    # Разделяем строку на части
                    fields = line.split(", ")
                    if len(fields) > 6:  # Проверяем наличие необходимого количества полей
                        date_time = fields[0] + fields[1]
                        hz_low = fields[2]
                        hz_high = fields[3]
                        hz_bin_width = fields[4]
                        dbs = [fields[6 + i] for i in range(5)]
                        self.current_buffer.append((date_time, hz_low, hz_high, hz_bin_width, dbs))
                        if previous_date_time != date_time:
                            result = self.buffer_to_packed_points(self.current_buffer)
                            data_to_send = DataPacker.pack_data(result)
                            self.server.send_data(data_to_send)
                            self.current_buffer = []
                        previous_date_time = date_time

            print("Данные успешно сохранены в hackrf_sweep_output.csv.")

        except KeyboardInterrupt:
            print("Остановка выполнения по Ctrl+C.")
        except Exception as e:
            print(f"Произошла ошибка: {e}")
        finally:
            try:
                process.terminate()
            except Exception:
                pass

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345
    wave_generator = LineGenerator(multiplier=1)  # You can switch to SineWaveGenerator if needed
    server = Server(host, port, wave_generator)
    parser = HackrfSweepParser(server)

    # Start the server in a separate thread
    import threading
    server_thread = threading.Thread(target=server.start)
    server_thread.start()

    # Start parsing hackrf_sweep data
    parser.parse_hackrf_sweep()
