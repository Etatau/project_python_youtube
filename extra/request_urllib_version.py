from urllib.request import Request, urlopen
import json

yt_link = "https://youtu.be/EYID3plKb8I?si=rp5g5MZr3lhQrMdp"

api_key = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"
_url = "https://www.youtube.com/youtubei/v1/player?key="+api_key

data = """{
            "videoId": "%ID",
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.04.38",
                    "androidSdkVersion": 31
                }
            }
        }""".replace("%ID", yt_link.split("=")[1] if "youtube" in yt_link else yt_link.split("/")[3].split("?")[0]).encode('utf-8')

# content-type header is important as it tells the api that the data is json format or else it will throw HTTP Error 400
headers = {'User-Agent': 'com.google.android.youtube/19.04.38 (Linux; U; Android 12; GB) gzip', 'Content-Type': 'application/json'}

k = Request(_url, data=data, headers=headers, method="POST")
res = b''.join(urlopen(k))
text = json.loads(res)
print(text)
