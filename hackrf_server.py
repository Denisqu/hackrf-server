import subprocess
import csv

def parse_hackrf_sweep():
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
        with open("hackrf_sweep_output.csv", "w", newline="") as csvfile:
            csv_writer = csv.writer(csvfile)
            header_written = False

            for line in process.stdout:
                # Удаляем лишние пробелы и проверяем, содержит ли строка данные
                line = line.strip()
                if "," in line:
                    # Разделяем строку на части
                    fields = line.split(", ")
                    if len(fields) > 6:  # Проверяем наличие необходимого количества полей
                        # Записываем заголовок в CSV (однократно)
                        if not header_written:
                            headers = ["date", "time", "hz_low", "hz_high", "hz_bin_width", "num_samples"] + [
                                f"dB_{i}" for i in range(1, len(fields) - 6 + 1)
                            ]
                            csv_writer.writerow(headers)
                            header_written = True
                        
                        # Записываем строку в CSV
                        csv_writer.writerow(fields)
                        print(f"Записаны данные: {fields}")
        
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
    parse_hackrf_sweep()
