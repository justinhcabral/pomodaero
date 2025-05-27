import random

def read_dht11():
    return round(random.uniform(22, 30), 1), round(random.uniform(45, 60),1)

def read_ph():
    return round(random.uniform(5.8, 7.2), 2)

def read_ec():
    return round(random.uniform(1.0, 2.5),2)
