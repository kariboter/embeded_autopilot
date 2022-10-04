import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import requests
import json
reader = SimpleMFRC522()

def form_data(product_data, count):
    new_data = {}
    product_data['count'] = count
    new_data[product_data['id']] = product_data
    product_data.pop('id')
    return new_data


def change_data(value):
    value['images'][0] = value['images'][0]['image']
    value['company'] = dict(value['company'])
    return value


def get_data(uuid):
    url = f'http://192.168.88.241:8150/product/get/{uuid}'
    data = requests.get(url)
    if data.status_code == 200:
        data = data.json()
    return data


def update_database(data):
    url = 'http://192.168.88.241:8150/cart/update/Admin@gmail.com'
    header = {'Content-Type': 'application/json'}
    dataset = requests.put(url, data=json.dumps({"Cart": data}), headers=header)
    return dataset

while True:
    try:
            id, text = reader.read()
            daaata = get_data(f"{id}")
            data_url = form_data(change_data(daaata), 1)
            update_database(data_url)
    finally:
            GPIO.cleanup()
            id, text = 0, 0
