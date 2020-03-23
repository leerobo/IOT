#!/usr/bin python3
from prometheus_client import start_http_server, Gauge
import random
import time

def process_request(t):
    """A dummy function that takes some time."""
    g.set(4.2)   # Set to a given value

if __name__ == '__main__':
    g = Gauge('W1_Gauge', 'Water-Temp')
    # Start up the server to expose the metrics.
    start_http_server(8010)
    # Generate some requests.
    while True:
        process_request(random.random())
        
