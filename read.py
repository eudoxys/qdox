import sys
import requests
import json

def get_json(*args,**kwargs):
    try:
        with requests.get(*args,**kwargs) as res:
            if res.status_code == 200:
                return json.loads(res.text)
            return dict(error="request failed",message=f"StatusCode:{res.status_code}")
    except:
        e_type, e_name, _ = sys.exc_info()
        return dict(error="request failed",message=f"{e_type.__name__}={e_name}")

# print(get_json("https://api.github.com/users/eudoxys"))

print("\n".join([f"{x} --> {repr(y)}" for x,y in get_json("https://api.github.com/users/dchassin").items()]))


