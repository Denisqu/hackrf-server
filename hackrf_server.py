import subprocess
import socket
import struct
import binascii
import time
import threading
import logging
from abc import ABC, abstractmethod

# Настройка логирования
logger = logging.getLogger('HackrfServer')
logger.setLevel(logging.DEBUG)

# Создание форматтера
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Создание обработчика для записи в файл
file_handler = logging.FileHandler('server.log', encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Создание обработчика для вывода в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Добавление обработчиков к логгеру
logger.addHandler(file_handler)
logger.addHandler(console_handler)

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
        logger.debug(f"Server initialized on {self.host}:{self.port}")

    def start(self):
        logger.info(f"Сервер слушает {self.host}:{self.port}")
        while True:
            logger.info("Ожидание подключения клиента...")
            try:
                self.client_socket, self.client_addr = self.server_socket.accept()
                logger.info(f"Подключение от {self.client_addr}")
                self.handle_client()
            except Exception as e:
                logger.error(f"Ошибка при ожидании подключения: {e}")

    def handle_client(self):
        try:
            while True:
                # Приём данных от клиента
                data = self.client_socket.recv(16)
                if not data:
                    logger.warning("Получены пустые данные от клиента.")
                    continue

                # Распаковка данных
                packed_size = 16
                packed_data = data
                try:
                    new_ranges = struct.unpack(f'>{packed_size // 8}d', packed_data)
                    logger.debug(f"Полученные данные: {new_ranges}")
                except struct.error as e:
                    logger.error(f"Ошибка распаковки данных: {e}")
                    continue

                # Проверка и перезапуск парсера, если диапазоны отличаются
                if new_ranges != self.parser.current_ranges:
                    logger.info(f"Диапазоны изменились с {self.parser.current_ranges} на {new_ranges}. Перезапуск парсера.")
                    self.parser.current_ranges = new_ranges
                    self.parser.restart_parser()
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.warning(f"Соединение с {self.client_addr} было закрыто: {e}")
        except Exception as e:
            logger.error(f"Ошибка при обработке клиента: {e}")
        finally:
            if self.client_socket:
                self.client_socket.close()
                logger.info(f"Соединение с {self.client_addr} закрыто.")

    def send_data(self, data):
        if self.client_socket:
            try:
                self.client_socket.sendall(data)
                logger.debug(f"Отправлены данные клиенту {self.client_addr}")
            except Exception as e:
                logger.error(f"Ошибка при отправке данных: {e}")

class HackrfSweepParser:
    def __init__(self, server):
        self.current_buffer = []
        self.server = server
        self.current_ranges = (0, 6000)
        self.process = None
        self.parser_thread = None
        logger.debug("HackrfSweepParser инициализирован.")

    def buffer_to_packed_points(self, buffer):
        result = []
        sorted_buffer = sorted(buffer, key=lambda x: float(x[1]))
        for line in sorted_buffer:
            _, hz_low, hz_high, hz_bin_width, dbs = line
            for i in range(0, 5):
                x = float((int(hz_low) + int(hz_low) + float(hz_bin_width) * (i + 1)) / 2)
                y = float(dbs[i])
                result.extend([x, y])
        logger.debug(f"Буфер преобразован в упакованные точки: {result}")
        return result

    def parse_hackrf_sweep(self):
        while True:

            if self.process:
                        self.process.terminate()
                        logger.info("Процесс hackrf_sweep завершен.")

            # Команда для запуска hackrf_sweep
            command = ["hackrf_sweep", "-f", f"{int(self.current_ranges[0])}:{int(self.current_ranges[1])}"]
            try:
                # Запуск процесса
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                logger.info("Запущен hackrf_sweep. Ожидание данных...")
                    # Обработка вывода в реальном времени
                for line in self.process.stdout:
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
                            dbs = [fields[6 + i] for i in range(len(fields) - 6)]
                            if int(hz_low) == int(self.current_ranges[0])*1e6 and len(self.current_buffer) > 0:
                                result = self.buffer_to_packed_points(self.current_buffer)
                                data_to_send = DataPacker.pack_data(result)
                                self.server.send_data(data_to_send)
                                self.current_buffer = []
                                logger.info("Данные отправлены клиенту после проверки диапазонов.")
                            self.current_buffer.append((date_time, hz_low, hz_high, hz_bin_width, dbs))
                logger.info("Прочитаны все sweep-строки.")
            except KeyboardInterrupt:
                logger.info("Остановка выполнения по Ctrl+C.")
            except Exception as e:
                logger.error(f"Произошла ошибка в парсере: {e}")
            finally:
                try:
                    if self.process:
                        self.process.terminate()
                        logger.info("Процесс hackrf_sweep завершен.")
                except Exception as e:
                    logger.error(f"Ошибка при завершении процесса hackrf_sweep: {e}")

    def restart_parser(self):
        # Остановка текущего процесса
        if self.process:
            self.process.terminate()
            logger.info("Текущий процесс hackrf_sweep завершен для перезапуска парсера.")

        # Перезапуск парсера в отдельном потоке
        if self.parser_thread and self.parser_thread.is_alive():
            self.parser_thread.join()
            logger.debug("Предыдущий поток парсера завершен.")

        time.sleep(1)
        self.parser_thread = threading.Thread(target=self.parse_hackrf_sweep, daemon=True)
        self.parser_thread.start()
        logger.info("Парсер hackrf_sweep перезапущен в новом потоке.")

if __name__ == "__main__":
    host = '127.0.0.1'
    port = 12345
    server = Server(host, port)
    parser = HackrfSweepParser(server)
    server.parser = parser  # Добавление ссылки на парсер в сервер

    # Start the server in a separate thread
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    logger.info("Сервер запущен в отдельном потоке.")

    # Start parsing hackrf_sweep data
    parser.restart_parser()
    server_thread.join()
