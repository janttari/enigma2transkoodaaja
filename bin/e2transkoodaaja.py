#!/usr/bin/env python3

import threading
import time
import os
import socket
import json
import requests
import sys
import copy
import subprocess
import signal
import shutil

HLSPATH = "/dev/shm/hls"
if HLSPATH[-1] != "/":
    HLSPATH += "/"
os.makedirs(HLSPATH, exist_ok=True)

PROJTMP = "/tmp/e2soittaja/"
if PROJTMP[-1] != "/":
    PROJTMP += "/"
os.makedirs(PROJTMP, exist_ok=True)

FFCOMMAND = "ffmpeg -loglevel quiet -re -i - %MAP -f hls -var_stream_map \"%VARSTREAMMAP\" -flags +cgop -g 25 -r 25 -c:v libx264 -b:v 8000k -c:a aac -b:a 96k -hls_flags delete_segments+append_list+omit_endlist -hls_time 1 -hls_list_size 10 -hls_segment_filename %CHANPATHfile_%v_%07d.ts %CHANPATHout_%v.m3u8"


def usage():
    print("käyttö:")
    print(sys.argv[0] + " channel1 create")
    print(sys.argv[0] + " channel1 e2play http://192.....")
    print(sys.argv[0] + " channel1 delete")
    quit()


class Fork:
    def __init__(self, channame, command, uri=None):
        self.channame = channame
        self.uri = uri
        self.PATTABLE = {}
        self.CURTRACKS = {}  # parhaillaan striimattavat raidat. kun lähetyksessä tämä muuttuu, striimaava ffmpeg uudelleenkäynnistetään
        self.LASTSEEN = {}
        self.PID = None
        self.PUSI = None
        self.Adaption = None
        self.pacno = 0
        self.th_ffkirjoittaja = None
        self.prosff = None
        self.ffaja = True
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.th_e2lukija=None
        #print(PROJTMP+channame+".sock")
        if os.path.exists(PROJTMP+channame+".sock"):  # tämän niminen kanava on jo!
            #print("KAnaVA on jo")
            self.sock.connect(PROJTMP+channame+".sock")
            self.sock.settimeout(1)  # lähetä komento kanavalle
            komento = json.dumps({"command": command, "uri": uri}).encode()
            self.sock.send(komento)
            quit()
        else:  # luo kanava
            if command == "create":
                os.makedirs(HLSPATH+channame, exist_ok=True)
                print("Striimi löytyy osoitteesta: http://localhost"+HLSPATH+channame+"/master.m3u8")
                try:
                    pid = os.fork()
                    if pid > 0:
                        #print("PID", pid)
                        with open(PROJTMP+channame+".pid", "w") as f:
                            f.write(str(pid))
                        os._exit(0)
                except:
                    print("ERR luodessa fork")
                self.teetaustapros()
            else:
                usage()

    def teetaustapros(self):
        th_receiveSock = (threading.Thread(target=self.receiveSock))
        th_receiveSock.start()
        self.th_ffkirjoittaja = threading.Thread(target=self.ffkirjoittaja)
        self.th_ffkirjoittaja.start()

    def receiveSock(self):
        #print("receiver")
        self.sock.bind(PROJTMP+channame+".sock")
        self.sock.listen(1)
        while True:
            #print("lukee")
            connection, client_address = self.sock.accept()
            while True:
                data = connection.recv(100)
                if data:
                    jdata = json.loads(data)
                    if jdata["command"] == "delete":
                        with open(PROJTMP+channame+".pid") as f:
                            pid=int(f.read())
                            shutil.rmtree(HLSPATH+channame)
                            os.remove(PROJTMP+channame+".pid")
                            os.remove(PROJTMP+channame+".sock")
                            os.kill(pid, signal.SIGTERM) #or signal.SIGKILL 

                    elif jdata["command"] == "e2play":
                        #self.ffaja = False
                        self.e2lukijarun = False
                        self.e2uri = jdata["uri"]
                        if self.th_e2lukija is not None:
                            self.th_e2lukija.join()
                        self.th_e2lukija=threading.Thread(target=self.e2lukija)
                        self.th_e2lukija.start()
                else:
                    break

    def ffkirjoittaja(self):  # säie kirjoittaa ffmpegin stdiniin dataa
        while True:
            while len(self.CURTRACKS) == 0:
                time.sleep(0.5)
            mappays = ""
            varstreammap = "v:0"
            MASTERPL = "#EXTM3U\n#EXT-X-VERSION:3\n"
            atrcount = 0
            for i in self.CURTRACKS:
                mappays += " -map i:"+str(i)
                print("MAP", self.CURTRACKS[i][0])
                if self.CURTRACKS[i][0] != 2 and self.CURTRACKS[i][0] != 27:  # audiot..
                    varstreammap += " a:"+str(atrcount)
                    lang = self.CURTRACKS[i][1]
                    if atrcount == 0:
                        asel = "YES"
                    else:
                        asel = "NO"
                    trnum = str(atrcount+1)
                    MASTERPL += '#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="aac",LANGUAGE="'+lang + \
                        '",DEFAULT=YES,AUTOSELECT='+asel+',URI="out_'+trnum+'.m3u8"\n'
                    atrcount += 1
            MASTERPL += '#EXT-X-STREAM-INF:BANDWIDTH=2962000,NAME="Main",CODECS="avc1.66.30",RESOLUTION=1280x720,AUDIO="aac"\n'
            MASTERPL += "out_0.m3u8"
            chanpath = HLSPATH+self.channame+"/"
            os.makedirs(chanpath, exist_ok=True)
            with open(chanpath+"master.m3u8", "w") as mf:
                mf.write(MASTERPL)
            mappays = mappays[1:]
            ffcmd = FFCOMMAND.replace("%MAP", mappays)
            ffcmd = ffcmd.replace("%CHANPATH", chanpath)
            ffcmd = ffcmd.split(" ")
            
            for f in range(len(ffcmd)):
                if ffcmd[f] == '"%VARSTREAMMAP"':
                    ffcmd[f] = varstreammap
            print(ffcmd)
            # quit()
            self.prosff = subprocess.Popen(ffcmd, stdin=subprocess.PIPE)
            self.ffaja = True
            while self.ffaja:
                time.sleep(0.3)
            self.prosff.kill()
            time.sleep(0.5)
            self.prosff=None

    def ff_write_packet(self):  # kirjoita yksittäinen ts-paketti ffmpegille
        if self.prosff is not None:  # jos ffprosessi on käynnissä
            try:
                self.prosff.stdin.write(self.spacket)
            except:
                pass

    def e2lukija(self):  # lukee enigma2:lta ts-paketteja
        self.e2lukijarun = True
        self.spacket = None
        r = requests.get(self.e2uri, stream=True)  # HTTP
        r.raw  # HTTP
        for self.spacket in r.iter_content(chunk_size=188):
            if self.e2lukijarun:
                if self.spacket:
                    # pitäisi olla aina 0x47 jos synkronointi pysynyt ok
                    if self.spacket[0] != 0x47:
                        print("sync fail")
                        sys.exit(1)
                    else:
                        self.PUSI = (self.spacket[1] & 0b01000000) >> 6
                        self.TransportPriority = (self.spacket[1] >> 1) & 1
                        self.PID = int.from_bytes(
                            self.spacket[1:3], byteorder='big') & 0b0001111111111111
                        self.Adaption = ((self.spacket[3]) & 0b00110000) >> 4
                        if self.PUSI != 0:
                            self.parsePMT()
                        if self.PID == 0:
                            self.parsePAT()
                        self.pacno += 1
                    self.ff_write_packet()
            else:
                r.close()
                break

    def parsePAT(self):
        start = 4
        stream_id = self.spacket[start]
        section_syntax_indicator = (self.spacket[start+1] & 0b10000000) >> 7
        section_syntax_indicator = self.spacket[start+1] & 0b10000000 >> 7
        section_length = int.from_bytes(
            self.spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
        table_id_extension = int.from_bytes(
            self.spacket[start+4:start+6], byteorder='big')
        version_number = (self.spacket[start+6] & 0b00111110) >> 1
        current_next_indicator = (self.spacket[start+6] & 0b00000001)
        last_section_number = self.spacket[start+7]
        program_info_length = int.from_bytes(
            self.spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
        proginfo = self.spacket[start+14:start+14+program_info_length]
        pointer = 17
        while pointer < section_length+4:
            program_num = int.from_bytes(
                self.spacket[pointer:pointer+2], byteorder='big')
            program_map_pid = int.from_bytes(
                self.spacket[pointer+2:pointer+4], byteorder='big') & 0b0001111111111111
            self.PATTABLE[program_map_pid] = program_num
            self.LASTSEEN[program_map_pid] = time.time()
            pointer += 4

    def parsePMT(self):
        start = 4
        stream_id = self.spacket[start]
        tableid = self.spacket[start]
        section_syntax_indicator = (self.spacket[start+1] & 0b10000000) >> 7
        private_indicator = (self.spacket[start+1] & 0b01000000) >> 6
        program_info_length = int.from_bytes(
            self.spacket[start+11:start+13], byteorder='big') & 0b0000111111111111
        section_length = int.from_bytes(
            self.spacket[start+2:start+4], byteorder='big') & 0b0000111111111111
        table_id_extension = int.from_bytes(
            self.spacket[start+4:start+6], byteorder='big')
        version_number = (self.spacket[start+6] & 0b00111110) >> 1
        current_next_indicator = (self.spacket[start+6] & 0b00000001)
        section_number = self.spacket[start+7]
        last_section_number = self.spacket[start+7]
        proginfo = self.spacket[start+14:start+14+program_info_length]

        if self.PID in self.PATTABLE:  # Tämä on PMT-paketti!
            #print("***",self.PID)
            tracks_start_point = program_info_length+17
            pointer = tracks_start_point
            nytTracks = {}
            while pointer < section_length+program_info_length-17:
                # ISO/IEC 13818-1 : 2000 (E): Table 2-29 – Stream type assignments 2VIDEO 3AUDIO
                streamType = self.spacket[pointer]
                elementary_PID = int.from_bytes(
                    self.spacket[pointer+1:pointer+3], byteorder='big') & 0b0001111111111111
                ES_info_length = int.from_bytes(
                    self.spacket[pointer+3:pointer+5], byteorder='big') & 0b0000111111111111
                lng="und"
                if streamType==3 or streamType== 0x11:
                    for i in range(pointer,pointer+ES_info_length):
                        if self.spacket[i] == 10 and self.spacket[i+1]==4:
                            try:
                                lng=self.spacket[i+2:i+5].decode()
                            except:
                                pass
                if streamType==6:
                    for i in range(pointer,pointer+ES_info_length):
                        if self.spacket[i]==89 or self.spacket[i]==86: # and spacket[i+1]==4:
                            try:
                                lng=self.spacket[i+2:i+5].decode()
                            except:
                                pass
                #print("TYPE", hex(streamType), hex(elementary_PID),lng)
                #ISO/IEC 13818-1 : 2000 Table 2-39 – Program and program element descriptors
                if streamType == 2 or streamType== 27 or streamType == 3 or streamType== 0x11:  # video tai audio
                    nytTracks[elementary_PID] = [streamType,lng]
                    #!TODO tässä käy läpi ES_info_length:n määrä loopilla!! pitäisi mm kielikoodi löytyä!
                pointer += ES_info_length+5
            
            if  nytTracks != self.CURTRACKS:  # raidat muuttuneet!
                time.sleep(2)
                if self.ffaja and len(self.CURTRACKS)>0:  # ffkirjoittaja on olemassa joten tapetaan se ensin
                    self.ffaja = False
                    self.PATTABLE = {}
                    self.CURTRACKS = {}
                    self.LASTSEEN = {}
                self.CURTRACKS = copy.deepcopy(nytTracks)

if __name__ == "__main__":
    #print(len(sys.argv))
    channame = sys.argv[1]  # tulee argumenttina
    playtype = sys.argv[2]
    if len(sys.argv) > 3:
        uri = sys.argv[3]
    else:
        uri=None
    f = Fork(channame, playtype, uri)
