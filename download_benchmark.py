import argparse
import sys
from contextlib import closing
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from time import perf_counter
from urllib.parse import urlsplit

REQUEST_COUNT = 10
READ_SIZE = 64 * 1024
TIMEOUT_SECONDS = 30
BYTES_PER_MIB = 1024**2


def measure_download(connection: HTTPConnection, target: str) -> tuple[float, int]:
    downloaded_bytes = 0
    started_at = perf_counter()

    with closing(connection):
        connection.request("GET", target)
        with connection.getresponse() as response:
            if not 200 <= response.status < 300:
                raise HTTPException(f"HTTP {response.status}")

            while chunk := response.read(READ_SIZE):
                downloaded_bytes += len(chunk)

            if response.length:
                raise HTTPException("соединение закрылось до конца ответа")

            elapsed = perf_counter() - started_at

    return elapsed, downloaded_bytes


def main() -> int:
    parser = argparse.ArgumentParser(description="Измеряет скорость скачивания за 10 HTTP-запросов.")
    parser.add_argument("url", help="адрес ресурса с http:// или https://")
    args = parser.parse_args()

    try:
        url = urlsplit(args.url)
        host = url.hostname
        port = url.port
    except ValueError as error:
        parser.error(f"некорректный URL ({error})")

    if url.scheme not in ("http", "https") or not host:
        parser.error("укажите полный URL с http:// или https://")
    if url.username is not None:
        parser.error("укажите URL без логина и пароля")

    target = url.path or "/"
    if url.query:
        target += f"?{url.query}"

    connection_type = HTTPSConnection if url.scheme == "https" else HTTPConnection
    total_time = 0.0
    total_bytes = 0

    for request_number in range(1, REQUEST_COUNT + 1):
        try:
            connection = connection_type(host, port, timeout=TIMEOUT_SECONDS)
            elapsed, downloaded_bytes = measure_download(connection, target)
        except (OSError, HTTPException, ValueError) as error:
            print(f"Запрос {request_number} из {REQUEST_COUNT}: {error}", file=sys.stderr)
            return 1

        total_time += elapsed
        total_bytes += downloaded_bytes

    print(f"Среднее время запроса: {total_time / REQUEST_COUNT:.3f} с")
    print(f"Скачано: {total_bytes} байт")
    print(f"Скорость скачивания: {total_bytes / total_time / BYTES_PER_MIB:.2f} МиБ/с")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
