from typing import Union
from fastapi import FastAPI, Response, Request, HTTPException
from PINcontrol import PinControl
import prometheus_client 
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prom=prometheus_client.Gauge(name='hotbox',documentation='Bollnas',labelnames=['label_name'])

# Add prometheus asgi middleware to route /metrics requests
#metrics_app = prometheus_client.make_asgi_app()
#app.mount("/metrics", metrics_app)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/sensors")
def read_sensors():
    pins=PinControl()
    rst,status=pins.w1Refresh()
    print('Sensors:',pins.Wire1List)
    return pins.Wire1List

@app.get("/metrics")
def promethuesPoll():
    pins=PinControl()
    rst,status=pins.w1Refresh()
    for sid in pins.Wire1List:
       print('>>> ',sid,':',pins.Wire1List[sid]['value'])
       try: 
         gauge_child = prom.labels(sid)
         gauge_child.set_to_current_time()
         gauge_child.set(pins.Wire1List[sid]['value'])         
       except Exception as ex:
         print(ex)  
         pass    
    content=prometheus_client.generate_latest()
    return Response(content=content,media_type='text/plain')

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}