"""
@file main.py
@brief Программа для работы с различными типами кодов: QR, DataMatrix, Code128, Code39 и PDF417.
@details Программа позволяет генерировать и декодировать коды. Также поддерживается транслитерация текста, работа с разными форматами файлов (PNG, JPG) и настройка параметров кодов.

@brief Импорты стандартных библиотек и модулей.
@details Содержит библиотеки для работы с кодами, обработки изображений, транслитерации и работы с файловой системой.
"""
import argparse
import os
from abc import ABC, abstractmethod
from typing import Optional
from transliterate import translit

import qrcode
import barcode
from barcode.writer import ImageWriter
from pylibdmtx.pylibdmtx import encode as dmtx_encode, decode as dmtx_decode
from pyzbar.pyzbar import decode as zbar_decode
from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg
from pdf417 import encode as pdf417_encode, render_image
import zxing
import numpy as np
import io

def transliterate_text(text: str) -> str:
    """
    @brief Функция для транслитерации текста.
    @param text Текст для транслитерации.
    @return Транслитерированный текст (если присутствуют символы, отличные от ASCII) или исходный текст.
    """
    return translit(text, 'ru', reversed=True) if any(ord(c) > 128 for c in text) else text

class CodeGenerator():
    """
    @brief Базовый класс для всех генераторов кодов.
    @details Определяет интерфейс для генерации и декодирования кодов.
    """
    @abstractmethod
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация кода.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        @param kwargs Дополнительные параметры, такие как уровень коррекции ошибок.
        @note Метод обязателен для реализации в наследниках.
        """
        pass
    @abstractmethod
    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование кода.
        @param file_path Путь к файлу, содержащему закодированные данные.
        @return Строка с декодированными данными или None, если данные не были распознаны.
        """
        pass


class QRCodeGenerator(CodeGenerator):
    """
    @brief Класс для работы с QR-кодами.
    @details Реализует методы генерации и декодирования QR-кодов с использованием библиотеки qrcode.
    """
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация QR-кода.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        @param kwargs Дополнительные параметры, включая error_correction (уровень коррекции ошибок).
        """
        data = transliterate_text(data)
        qr = qrcode.QRCode(
            error_correction=kwargs.get('error_correction', qrcode.constants.ERROR_CORRECT_M)
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        if file_format.lower() == "jpg":
            img = img.convert("RGB")
            img.save(file_path, "JPEG")
        else:
            img.save(file_path, "PNG")

    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование QR-кода.
        @param file_path Путь к файлу.
        @return Строка с декодированными данными или None.
        """
        image = Image.open(file_path)
        results = zbar_decode(image)
        return results[0].data.decode() if results else None

class DataMatrixGenerator(CodeGenerator):
    """
    @brief Класс для работы с DataMatrix-кодами.
    @details Использует библиотеку pylibdmtx для кодирования и декодирования.
    """
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация DataMatrix-кода.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        """
        data = transliterate_text(data)
        encoded = dmtx_encode(data.encode('utf-8'))
        img = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
        if file_format.lower() == "jpg":
            img = img.convert("RGB")
            img.save(file_path, "JPEG")
        else:
            img.save(file_path, "PNG")

    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование DataMatrix-кода.
        @param file_path Путь к файлу.
        @return Строка с декодированными данными или None.
        """
        image = Image.open(file_path)
        decoded = dmtx_decode(image)
        return decoded[0].data.decode('utf-8') if decoded else None

class Code128Generator(CodeGenerator):
    """
    @brief Класс для работы с линейным штрих-кодом Code128.
    @details Реализует генерацию и декодирование с использованием библиотеки python-barcode.
    """
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация Code128.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        """
        data = transliterate_text(data)
        barcode_class = barcode.get_barcode_class('code128')
        bar_code = barcode_class(data, writer=ImageWriter())
        bar_code.save(file_path[:-4])
        os.rename(file_path[:-4] + '.png', file_path)
        if file_format.lower() == "jpg":
            img = Image.open(file_path)
            img = img.convert("RGB")
            img.save(file_path, "JPEG")

    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование Code128.
        @param file_path Путь к файлу.
        @return Строка с декодированными данными или None.
        """
        image = Image.open(file_path)
        results = zbar_decode(image)
        return results[0].data.decode() if results else None

class Code39Generator(CodeGenerator):
    """
    @brief Класс для работы с линейным штрих-кодом Code39.
    @details Реализует генерацию и декодирование.
    """
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация Code39.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        """
        data = transliterate_text(data)
        barcode_class = barcode.get_barcode_class('code39')
        bar_code = barcode_class(data, writer=ImageWriter())
        bar_code.save(file_path[:-4])
        os.rename(file_path[:-4] + '.png', file_path)
        if file_format.lower() == "jpg":
            img = Image.open(file_path)
            img = img.convert("RGB")
            img.save(file_path, "JPEG")

    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование Code39.
        @param file_path Путь к файлу.
        @return Строка с декодированными данными или None.
        """
        image = Image.open(file_path)
        results = zbar_decode(image)
        return results[0].data.decode() if results else None

class PDF417Generator(CodeGenerator):
    """
    @brief Класс для работы с PDF417.
    @details Использует библиотеку pdf417 для генерации, декодирование через pyzbar.
    """
    def generate(self, data: str, file_path: str, file_format: str, **kwargs):
        """
        @fn generate
        @brief Генерация PDF417.
        @param data Данные для кодирования.
        @param file_path Путь для сохранения файла.
        @param file_format Формат файла (png/jpg).
        """
        data = transliterate_text(data)
        codes = pdf417_encode(data, error_level=kwargs.get('error_level', 2))
        img = render_image(codes)
        if file_format.lower() == "jpg":
            img = img.convert("RGB")
            img.save(file_path, "JPEG")
        else:
            img.save(file_path, "PNG")

    def decode(self, file_path: str) -> Optional[str]:
        """
        @fn decode
        @brief Декодирование PDF417.
        @param file_path Путь к файлу.
        @return Строка с декодированными данными или None.
        """
        try:
            # Создаем объект ZXing
            reader = zxing.BarCodeReader()

            # Декодируем изображение
            barcode = reader.decode(file_path)

            if barcode:
                return barcode.parsed  # Возвращаем декодированные данные
            else:
                print("Не удалось распознать код на изображении.")
                return None
        except Exception as e:
            print(f"Ошибка при декодировании PDF417 с использованием zxing: {e}")
            return None

def display_menu():
    """
    @fn display_menu
    @brief Отображение меню для выбора типа кода.
    @return Тип кода (например, qr, datamatrix, code128, code39, pdf417).
    """
    while True:
        print("Выберите тип кода:")
        print("1 - Линейный код")
        print("2 - Двумерный код")
        code_type = input("Ваш выбор: ").strip()

        if code_type == "1":
            print("Выберите линейный код:")
            print("1 - Code128")
            print("2 - Code39")
            linear_type = input("Ваш выбор: ").strip()
            return "code128" if linear_type == "1" else "code39"

        elif code_type == "2":
            print("Выберите двумерный код:")
            print("1 - QR-код")
            print("2 - DataMatrix")
            print("3 - PDF417")
            dim_type = input("Ваш выбор: ").strip()
            if dim_type == "1":
                return "qr"
            elif dim_type == "2":
                return "datamatrix"
            elif dim_type == "3":
                return "pdf417"

        print("Неверный выбор. Попробуйте снова.")

def main():
    """
    @fn main
    @brief Основная функция программы.
    @details Позволяет выбирать режимы работы (кодирование/декодирование), задавать параметры и обрабатывать ошибки.
    """
    while True:
        code_type = display_menu()

        print("Выберите режим:")
        print("1 - Кодирование")
        print("2 - Декодирование")
        mode = input("Ваш выбор: ").strip()

        if mode not in ["1", "2"]:
            print("Неверный выбор. Попробуйте снова.")
            continue

        file_format = input("Выберите формат для сохранения (png/jpg): ").strip().lower()

        if code_type == "qr":
            generator = QRCodeGenerator()
        elif code_type == "datamatrix":
            generator = DataMatrixGenerator()
        elif code_type == "code128":
            generator = Code128Generator()
        elif code_type == "code39":
            generator = Code39Generator()
        elif code_type == "pdf417":
            generator = PDF417Generator()
        else:
            print("Неподдерживаемый тип кода")
            continue

        if mode == "1":
            data = input("Введите текстовую информацию для кодирования: ").strip()
            file_path = input("Введите путь для сохранения файла (например, output): ").strip()

            if not file_path.endswith(".png") and not file_path.endswith(".jpg"):
                file_path = file_path + (".jpg" if file_format == "jpg" else ".png")

            error_correction = input("Введите уровень помехоустойчивости (по умолчанию): ").strip()
            try:
                generator.generate(data, file_path, file_format, error_correction=error_correction)
                print(f"Код сохранен в {file_path}")
            except Exception as e:
                print(f"Ошибка: {e}")

        elif mode == "2":
            file_path = input("Введите путь к файлу для декодирования: ").strip()
            if not os.path.exists(file_path):
                print("Файл не найден. Проверьте путь и попробуйте снова.")
                continue
            try:
                result = generator.decode(file_path)
                if result:
                    print(f"Декодированные данные: {result}")
                else:
                    print("Не удалось декодировать данные.")
            except Exception as e:
                print(f"Ошибка: {e}")

        else:
            print("Неверный выбор. Попробуйте снова.")

if __name__ == "__main__":
    main()
