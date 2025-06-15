import pytesseract
from pytesseract import Output
from PIL import Image
import cv2

img_path1 = 'sample2.jpg'
text = pytesseract.image_to_string(img_path1,lang='eng')
print(text)