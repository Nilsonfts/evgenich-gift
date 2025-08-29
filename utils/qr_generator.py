# qr_generator.py
"""
Модуль для генерации QR-кодов.
Использует библиотеку qrcode, убедитесь, что она установлена:
pip install qrcode[pil]
"""
import qrcode
import io

def create_qr_code(link: str) -> io.BytesIO:
    """
    Создает QR-код для переданной ссылки и возвращает его как байтовый объект в памяти.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Сохраняем изображение в байтовый поток в памяти, а не в файл
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0) # "Перематываем" поток в начало, чтобы его можно было прочитать
    
    return img_byte_arr
