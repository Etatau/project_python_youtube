"""
MIT License

Copyright (c) 2024 Etatau

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import requests as req
from urllib.request import Request, urlopen
import asyncio


class Stream:
    def __init__(self, _url: str, file_size: int):
        self.url = _url
        self.file_size = file_size

        self.byte_stream_arr: list = list()

        self._extract_stream()

    """
    coroutine function for HTML request
    """
    async def _execute_request(self, _url):
        base_headers = {"User-Agent": "Mozilla/5.0", "accept-language": "en-US,en"}
        request = Request(_url, headers=base_headers, method="GET")
        return urlopen(request)

    """
    generates a list of tuple which contains the start and end range
    """
    def _range_generator(self, batch_size: int) -> list[tuple[int, int]]:
        div_range = list()
        for i in range(0, self.file_size, batch_size):
            div_range.append((i+1 if i != 0 else i, i+batch_size if self.file_size > (i+batch_size) else self.file_size))
        return div_range

    """
    main function to create tasks for each range
    async is used to speed up the request process
    
    youtube apparently limits the data transfer to less 10MB unless it has pre-existing
    parameter called ratebypass in url. Rather than checking for probabilistic case like that 
    its better to divide in chunks and rip from the stream since we can then use 
    individual chunk for streaming while other chunks are being downloaded
    """
    async def _req_gen(self):
        div_range = self._range_generator(100000)
        for _ in div_range:
            self.byte_stream_arr.append(asyncio.create_task(self._execute_request(self.url + f"&range={_[0]}-{_[1]}")))
        [await _ for _ in self.byte_stream_arr]

    """
    result() function is used to get the html response object that has been returned from the task
    read() function then reads from that object and stores the data in the list
    """
    def _extract_stream(self):
        asyncio.run(self._req_gen())

        for _ in range(len(self.byte_stream_arr)):
            self.byte_stream_arr[_] = self.byte_stream_arr[_].result().read()

    """
    appends all the byte string in the list and returns as a single byte string
    """
    def get_stream(self):
        return b''.join(self.byte_stream_arr)


"""
youtube provides an api to communicate with youtube platform

android is used as user agent since it doesnt have ciphered url
unlike any web agent which usually has a ciphered url.
the user agent in header is very important as without it the request will fail. 
the android version and youtube client version has to match with the one given in data

the signature can be found in the itag in "signatureCipher"
the ciphered signature can be solved through the base.js file but
its a hassle.

the method is for those who like pain:

find a=a.split("") which contains the step for the cipher
the cipher only uses 3 methods - splice string, swap characters between 2 random index and reverse the string
these function definitions are stored in dictionary
with basic knowledge of javascript you can pretty easily figure out what each function does
after you figure out the function just pass the string through it and it will return the deciphered signature
concat that signature at end of link with sig={deciphered signature}

the youtube API apparently only accepts POST method.
the data format is the minimum that is required for a valid request
video ID is (eg - https://www.youtube.com/watch?v=VrcB9PJ22F0) this part -> VrcB9PJ22F0 the part after v= 
client name is ANDROID because we are impersonating as it
client version is the latest version of youtube you would find on google playstore
android sdk version relates to the api version of android eg- 31 relates to android 12
refer to this website (https://developer.android.com/tools/releases/platforms) to get api version and the android version they relate to

the replace() function puts implementation for 2 types of links i.e. the shared link and the normal url link. 
shared link has to be handled differently since the format differs

to use the api you require a key which is not that hard to get
just go to google cloud console and then select youtube api then you get an api key there

rest is just extracting information from the json file

download simply writes all the bytes into a file. before that there is name check for illegal 
characters which can cause problems while naming a new file. It is a vague check for illegal
characters since I am not interested in writing a whole separate check for it.

you can change the itag value depending on what you want to download.
"""
class Youtube:
    def __init__(self, _url: str):
        self.embed_url: str = None
        self.content_length: int = None
        self.vid_title: str = None

        api_key = "AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w"  # recommended to use your own key
        api_endpoint = "https://www.youtube.com/youtubei/v1/player?key="+api_key

        data = """{
            "videoId": "%ID",
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.04.38",
                    "androidSdkVersion": 31
                }
            }
        }""".replace("%ID", _url.split("=")[1] if "youtube" in _url else _url.split("/")[3].split("?")[0])
        headers = {"User-Agent": "com.google.android.youtube/19.04.38 (Linux; U; Android 12; GB) gzip", "Connection": "close"}

        k = req.post(api_endpoint, headers=headers, data=data, timeout=5)
        self.json = k.json()
        self.__extract_details()

        extract = Stream(self.embed_url, self.content_length)
        self.stream = extract.get_stream()

    def __extract_details(self):
        self.vid_title = self.json['videoDetails']['title']
        for i in self.json['streamingData']['adaptiveFormats']:
            if i['itag'] == 140:
                self.embed_url = i['url']
                self.content_length = int(i['contentLength'])

    def __name_change(self):
        name = input("Invalid file name detected. Enter a new filename: ")
        return self.__filename_check(name)

    def __filename_check(self, name):
        illegal_char = r'?*/\"%:|<>.,;='
        number = '123456789'
        alphabet = '_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        if ' ' in name:
            name = name.replace(' ', '_')
        if name[0] in number:
            name = self.__name_change()
        for _ in name:
            if _ in illegal_char:
                print("Illegal Character", _)
                name = self.__name_change()
                break
            elif _ not in alphabet:
                print("Illegal Character", _)
                name = self.__name_change()
                break
        if ' ' in name:
            name = name.replace(' ', '_')
        return name

    def download(self, filepath: str = "", filename: str = None, extension: str = "m4a"):
        if filename is None:
            filename = self.__filename_check(self.vid_title)
        with open(filepath+filename+'.'+extension, "wb") as f:
            f.write(self.stream)
            print("Completed Download")


"""
this is an example and can only download audio file
"""
yt = Youtube("https://www.youtube.com/watch?v=VrcB9PJ22F0")
yt.download(filename="regression")
