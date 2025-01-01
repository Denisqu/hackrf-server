import subprocess
import socket
import struct
import binascii
import time
from abc import ABC, abstractmethod

class DataPacker:
    @staticmethod
    def pack_data(data):
        packed_data = struct.pack(f'>{len(data)}d', *data)
        packed_size = struct.pack('>i', len(packed_data))
        return packed_size + packed_data

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
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
                # Приём данных от клиента
                data = self.client_socket.recv(1024)
                if not data:
                    continue

                # Распаковка данных
                #packed_size = struct.unpack('>i', data[:4])[0]
                packed_size = 16
                packed_data = data
                numbers = struct.unpack(f'>{packed_size // 8}d', packed_data)

                # Отображение данных в командной строке
                print(f"Received data: {numbers}")
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
                        if int(hz_low) == 0 and len(self.current_buffer) > 0:
                            result = self.buffer_to_packed_points(self.current_buffer)
                            data_to_send = DataPacker.pack_data(result)
                            self.server.send_data(data_to_send)
                            self.current_buffer = []
                        self.current_buffer.append((date_time, hz_low, hz_high, hz_bin_width, dbs))
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
    server = Server(host, port)
    parser = HackrfSweepParser(server)

    # Start the server in a separate thread
    import threading
    server_thread = threading.Thread(target=server.start)
    server_thread.start()

    # Start parsing hackrf_sweep data
    parser.parse_hackrf_sweep()
